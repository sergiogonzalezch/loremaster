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
from app.core.rag_generate import generate_rag_response
from app.core.common import get_active_by_id

logger = logging.getLogger(__name__)

MAX_PENDING_DRAFTS = 5


async def generate_draft_service(
    session: Session,
    entity_id: str,
    collection_id: str,
    request: GenerateEntityTextDraftRequest,
) -> EntityTextDraft:
    entity = get_active_by_id(session, Entity, entity_id, collection_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    pending_count = session.exec(
        select(func.count())
        .select_from(EntityTextDraft)
        .where(
            EntityTextDraft.entity_id == entity_id,
            EntityTextDraft.collection_id == collection_id,
            EntityTextDraft.status == DraftStatus.pending,
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

    try:
        answer, sources_count = generate_rag_response(
            collection_id=collection_id,
            query=request.query,
            extra_context=extra_context,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    draft = EntityTextDraft(
        entity_id=entity_id,
        collection_id=collection_id,
        query=request.query,
        content=answer,
        sources_count=sources_count,
    )
    session.add(draft)
    session.commit()
    session.refresh(draft)
    logger.info("Draft %s created for entity %s", draft.id, entity_id)
    return draft


def list_drafts_service(
    session: Session,
    entity_id: str,
    collection_id: str,
) -> list[EntityTextDraft]:
    entity = get_active_by_id(session, Entity, entity_id, collection_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    stmt = (
        select(EntityTextDraft)
        .where(
            EntityTextDraft.entity_id == entity_id,
            EntityTextDraft.collection_id == collection_id,
            EntityTextDraft.status != DraftStatus.discarded,
        )
        .order_by(EntityTextDraft.created_at.desc())
    )
    return session.exec(stmt).all()


def update_draft_content_service(
    session: Session,
    draft_id: str,
    entity_id: str,
    collection_id: str,
    content: str,
) -> EntityTextDraft | None:
    draft = _get_active_draft(session, draft_id, entity_id, collection_id)
    if not draft:
        return None
    draft.content = content
    session.add(draft)
    session.commit()
    session.refresh(draft)
    return draft


def confirm_draft_service(
    session: Session,
    draft_id: str,
    entity_id: str,
    collection_id: str,
) -> Entity | None:
    draft = _get_active_draft(session, draft_id, entity_id, collection_id)
    if not draft:
        return None

    entity = get_active_by_id(session, Entity, entity_id, collection_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    draft.status = DraftStatus.confirmed
    draft.confirmed_at = datetime.now(timezone.utc)
    session.add(draft)

    pending_stmt = select(EntityTextDraft).where(
        EntityTextDraft.entity_id == entity_id,
        EntityTextDraft.collection_id == collection_id,
        EntityTextDraft.id != draft_id,
        EntityTextDraft.status == DraftStatus.pending,
    )
    pending_drafts = session.exec(pending_stmt).all()
    for pending in pending_drafts:
        pending.status = DraftStatus.discarded
        session.add(pending)
    logger.info(
        "Auto-discarded %d pending draft(s) for entity %s",
        len(pending_drafts),
        entity_id,
    )

    entity.description = draft.content
    entity.updated_at = datetime.now(timezone.utc)
    session.add(entity)

    session.commit()
    session.refresh(entity)
    logger.info(
        "Draft %s confirmed → entity %s description updated", draft_id, entity_id
    )
    return entity


def discard_draft_service(
    session: Session,
    draft_id: str,
    entity_id: str,
    collection_id: str,
) -> EntityTextDraft | None:
    draft = _get_active_draft(session, draft_id, entity_id, collection_id)
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
    stmt = select(EntityTextDraft).where(EntityTextDraft.status == DraftStatus.pending)
    if entity_id is not None:
        stmt = stmt.where(EntityTextDraft.entity_id == entity_id)
    if collection_id is not None:
        stmt = stmt.where(EntityTextDraft.collection_id == collection_id)

    drafts = session.exec(stmt).all()
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


def _get_active_draft(
    session: Session,
    draft_id: str,
    entity_id: str,
    collection_id: str,
) -> EntityTextDraft | None:
    stmt = select(EntityTextDraft).where(
        EntityTextDraft.id == draft_id,
        EntityTextDraft.entity_id == entity_id,
        EntityTextDraft.collection_id == collection_id,
        EntityTextDraft.status == DraftStatus.pending,
    )
    return session.exec(stmt).first()
