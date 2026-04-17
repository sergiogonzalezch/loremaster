import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.models.entity_text_draft import (
    DraftStatus,
    EntityTextDraft,
    GenerateEntityTextDraftRequest,
)
from app.models.entities import Entity
from app.core.common import soft_delete
from app.core.rag_generate import generate_rag_response

logger = logging.getLogger(__name__)

MAX_PENDING_DRAFTS = 5


def generate_draft_service(
    session: Session,
    entity: Entity,
    request: GenerateEntityTextDraftRequest,
) -> EntityTextDraft:
    pending_count = session.exec(
        select(func.count())
        .select_from(EntityTextDraft)
        .where(
            EntityTextDraft.entity_id == entity.id,
            EntityTextDraft.collection_id == entity.collection_id,
            EntityTextDraft.status == DraftStatus.pending,
            EntityTextDraft.is_deleted == False,
        )
    ).one()
    if pending_count >= MAX_PENDING_DRAFTS:
        raise HTTPException(
            status_code=409,
            detail=f"Entity has {pending_count} pending drafts (max {MAX_PENDING_DRAFTS}). "
            "Confirm or discard existing drafts first.",
        )

    extra_context = ""
    if entity.description:
        extra_context = (
            f"Información actual de '{entity.name}' ({entity.type}):\n"
            f"{entity.description}\n\n"
        )

    answer, sources_count = generate_rag_response(
        collection_id=entity.collection_id,
        query=request.query,
        extra_context=extra_context,
    )

    draft = EntityTextDraft(
        entity_id=entity.id,
        collection_id=entity.collection_id,
        query=request.query,
        content=answer,
        sources_count=sources_count,
    )
    session.add(draft)
    session.commit()
    session.refresh(draft)
    logger.info("Draft %s created for entity %s", draft.id, entity.id)
    return draft


def list_drafts_service(
    session: Session,
    entity_id: str,
    collection_id: str,
) -> list[EntityTextDraft]:
    stmt = (
        select(EntityTextDraft)
        .where(
            EntityTextDraft.entity_id == entity_id,
            EntityTextDraft.collection_id == collection_id,
            EntityTextDraft.status != DraftStatus.discarded,
            EntityTextDraft.is_deleted == False,
        )
        .order_by(EntityTextDraft.created_at.desc())
    )
    return session.exec(stmt).all()


def edit_draft_service(
    session: Session,
    draft_id: str,
    entity_id: str,
    collection_id: str,
    content: str,
) -> EntityTextDraft | None:
    draft = _get_editable_draft(session, draft_id, entity_id, collection_id)
    if not draft:
        return None

    now = datetime.now(timezone.utc)
    draft.content = content
    draft.updated_at = now
    session.add(draft)

    if draft.status == DraftStatus.confirmed:
        entity = session.exec(
            select(Entity).where(
                Entity.id == entity_id,
                Entity.collection_id == collection_id,
                Entity.is_deleted == False,
            )
        ).first()
        if entity:
            entity.description = content
            entity.updated_at = now
            session.add(entity)
            logger.info(
                "Updated entity %s description from confirmed draft edit", entity_id
            )

    session.commit()
    session.refresh(draft)
    return draft


def confirm_draft_service(
    session: Session,
    draft_id: str,
    entity: Entity,
) -> Entity | None:
    draft = _get_pending_draft(session, draft_id, entity.id, entity.collection_id)
    if not draft:
        return None

    now = datetime.now(timezone.utc)
    draft.status = DraftStatus.confirmed
    draft.confirmed_at = now
    draft.updated_at = now
    session.add(draft)

    discarded = _discard_sibling_drafts(
        session,
        entity.id,
        entity.collection_id,
        draft_id,
        statuses=[DraftStatus.pending, DraftStatus.confirmed],
    )
    logger.info(
        "Auto-discarded %d sibling draft(s) for entity %s", discarded, entity.id
    )

    entity.description = draft.content
    entity.updated_at = now
    session.add(entity)

    session.commit()
    session.refresh(entity)
    logger.info(
        "Draft %s confirmed → entity %s description updated", draft_id, entity.id
    )
    return entity


def discard_draft_service(
    session: Session,
    draft_id: str,
    entity_id: str,
    collection_id: str,
) -> EntityTextDraft | None:
    draft = _get_pending_draft(session, draft_id, entity_id, collection_id)
    if not draft:
        return None
    draft.status = DraftStatus.discarded
    session.add(draft)
    session.commit()
    session.refresh(draft)
    logger.info("Draft %s discarded", draft_id)
    return draft


def discard_pending_drafts(
    session: Session,
    entity_id: str | None = None,
    collection_id: str | None = None,
) -> int:
    drafts = session.exec(
        _active_drafts_stmt(entity_id, collection_id).where(
            EntityTextDraft.status == DraftStatus.pending
        )
    ).all()
    for draft in drafts:
        draft.status = DraftStatus.discarded
        session.add(draft)
    logger.info(
        "Discarded %d pending draft(s) [entity_id=%s, collection_id=%s]",
        len(drafts),
        entity_id,
        collection_id,
    )
    return len(drafts)


def soft_delete_draft_service(
    session: Session,
    draft_id: str,
    entity_id: str,
    collection_id: str,
) -> bool:
    draft = _get_active_draft(session, draft_id, entity_id, collection_id)
    if not draft:
        return False
    soft_delete(session, draft)
    session.commit()
    logger.info("Draft %s soft-deleted", draft_id)
    return True


def soft_delete_all_drafts(
    session: Session,
    entity_id: str | None = None,
    collection_id: str | None = None,
) -> int:
    drafts = session.exec(_active_drafts_stmt(entity_id, collection_id)).all()
    for draft in drafts:
        soft_delete(session, draft)
    logger.info(
        "Soft-deleted %d draft(s) [entity_id=%s, collection_id=%s]",
        len(drafts),
        entity_id,
        collection_id,
    )
    return len(drafts)


def _get_active_draft(
    session: Session,
    draft_id: str,
    entity_id: str,
    collection_id: str,
) -> EntityTextDraft | None:
    return session.exec(
        select(EntityTextDraft).where(
            EntityTextDraft.id == draft_id,
            EntityTextDraft.entity_id == entity_id,
            EntityTextDraft.collection_id == collection_id,
            EntityTextDraft.is_deleted == False,
        )
    ).first()


def _get_pending_draft(
    session: Session,
    draft_id: str,
    entity_id: str,
    collection_id: str,
) -> EntityTextDraft | None:
    draft = _get_active_draft(session, draft_id, entity_id, collection_id)
    return draft if draft and draft.status == DraftStatus.pending else None


def _get_editable_draft(
    session: Session,
    draft_id: str,
    entity_id: str,
    collection_id: str,
) -> EntityTextDraft | None:
    draft = _get_active_draft(session, draft_id, entity_id, collection_id)
    if not draft:
        return None
    if draft.status in (DraftStatus.pending, DraftStatus.confirmed):
        return draft
    return None


def _active_drafts_stmt(entity_id: str | None, collection_id: str | None):
    if entity_id is None and collection_id is None:
        raise ValueError("requires at least entity_id or collection_id")
    stmt = select(EntityTextDraft).where(EntityTextDraft.is_deleted == False)
    if entity_id is not None:
        stmt = stmt.where(EntityTextDraft.entity_id == entity_id)
    if collection_id is not None:
        stmt = stmt.where(EntityTextDraft.collection_id == collection_id)
    return stmt


def _discard_sibling_drafts(
    session: Session,
    entity_id: str,
    collection_id: str,
    exclude_id: str,
    statuses: list[DraftStatus],
) -> int:
    drafts = session.exec(
        select(EntityTextDraft).where(
            EntityTextDraft.entity_id == entity_id,
            EntityTextDraft.collection_id == collection_id,
            EntityTextDraft.id != exclude_id,
            EntityTextDraft.status.in_(statuses),
            EntityTextDraft.is_deleted == False,
        )
    ).all()
    for d in drafts:
        d.status = DraftStatus.discarded
        session.add(d)
    return len(drafts)
