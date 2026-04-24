import logging
from datetime import datetime, timezone
from typing import Literal, Optional

from sqlalchemy import func
from sqlmodel import Session, select

from app.core.common import soft_delete
from app.models.entities import Entity
from app.models.entity_content import EntityContent
from app.models.enums import ContentCategory, ContentStatus

logger = logging.getLogger(__name__)


def list_contents(
    session: Session,
    entity_id: str,
    collection_id: str,
    category: Optional[ContentCategory] = None,
    page: int = 1,
    page_size: int = 20,
    order: Literal["asc", "desc"] = "desc",
) -> tuple[list[EntityContent], int]:
    conditions = [
        EntityContent.entity_id == entity_id,
        EntityContent.collection_id == collection_id,
        EntityContent.status != ContentStatus.discarded,
        EntityContent.is_deleted == False,
    ]
    if category is not None:
        conditions.append(EntityContent.category == category)

    total = session.exec(
        select(func.count()).select_from(
            select(EntityContent).where(*conditions).subquery()
        )
    ).one()

    sort_col = EntityContent.created_at.asc() if order == "asc" else EntityContent.created_at.desc()
    skip = (page - 1) * page_size
    items = list(
        session.exec(
            select(EntityContent)
            .where(*conditions)
            .order_by(sort_col)
            .offset(skip)
            .limit(page_size)
        ).all()
    )
    return items, total


def edit_content(
    session: Session,
    content_id: str,
    entity_id: str,
    collection_id: str,
    new_text: str,
) -> EntityContent | None:
    content = _get_active_content(session, content_id, entity_id, collection_id)
    if not content:
        return None
    if content.status == ContentStatus.discarded:
        raise ValueError("discarded")
    now = datetime.now(timezone.utc)
    content.content = new_text
    content.updated_at = now
    session.add(content)
    session.commit()
    session.refresh(content)
    return content


def confirm_content(
    session: Session,
    content_id: str,
    entity: Entity,
) -> EntityContent | None:
    content = _get_pending_content(session, content_id, entity.id, entity.collection_id)
    if not content:
        return None

    now = datetime.now(timezone.utc)
    content.status = ContentStatus.confirmed
    content.confirmed_at = now
    content.updated_at = now
    session.add(content)

    discarded = _discard_sibling_contents(
        session,
        entity_id=entity.id,
        collection_id=entity.collection_id,
        category=content.category,
        exclude_id=content_id,
        statuses=[ContentStatus.pending, ContentStatus.confirmed],
    )
    logger.info(
        "Auto-discarded %d sibling content(s) for entity %s category %s",
        discarded,
        entity.id,
        content.category,
    )

    session.commit()
    session.refresh(content)
    logger.info("EntityContent %s confirmed for entity %s", content_id, entity.id)
    return content


def discard_content(
    session: Session,
    content_id: str,
    entity_id: str,
    collection_id: str,
) -> EntityContent | None:
    content = _get_pending_content(session, content_id, entity_id, collection_id)
    if not content:
        return None
    content.status = ContentStatus.discarded
    session.add(content)
    session.commit()
    session.refresh(content)
    logger.info("EntityContent %s discarded", content_id)
    return content


def soft_delete_content(
    session: Session,
    content_id: str,
    entity_id: str,
    collection_id: str,
) -> bool:
    content = _get_active_content(session, content_id, entity_id, collection_id)
    if not content:
        return False
    soft_delete(session, content)
    session.commit()
    logger.info("EntityContent %s soft-deleted", content_id)
    return True


def cascade_delete_by_entity(
    session: Session,
    entity_id: str,
    collection_id: str,
) -> int:
    contents = session.exec(
        select(EntityContent).where(
            EntityContent.entity_id == entity_id,
            EntityContent.collection_id == collection_id,
            EntityContent.is_deleted == False,
        )
    ).all()
    for c in contents:
        soft_delete(session, c)
    logger.info(
        "Soft-deleted %d EntityContent(s) [entity_id=%s]", len(contents), entity_id
    )
    return len(contents)


def cascade_delete_by_collection(
    session: Session,
    collection_id: str,
) -> int:
    contents = session.exec(
        select(EntityContent).where(
            EntityContent.collection_id == collection_id,
            EntityContent.is_deleted == False,
        )
    ).all()
    for c in contents:
        soft_delete(session, c)
    logger.info(
        "Soft-deleted %d EntityContent(s) [collection_id=%s]",
        len(contents),
        collection_id,
    )
    return len(contents)


# ── Private helpers ───────────────────────────────────────────────────────────


def _get_active_content(
    session: Session,
    content_id: str,
    entity_id: str,
    collection_id: str,
) -> EntityContent | None:
    return session.exec(
        select(EntityContent).where(
            EntityContent.id == content_id,
            EntityContent.entity_id == entity_id,
            EntityContent.collection_id == collection_id,
            EntityContent.is_deleted == False,
        )
    ).first()


def _get_pending_content(
    session: Session,
    content_id: str,
    entity_id: str,
    collection_id: str,
) -> EntityContent | None:
    content = _get_active_content(session, content_id, entity_id, collection_id)
    return content if content and content.status == ContentStatus.pending else None


def _discard_sibling_contents(
    session: Session,
    entity_id: str,
    collection_id: str,
    category: ContentCategory,
    exclude_id: str,
    statuses: list[ContentStatus],
) -> int:
    siblings = session.exec(
        select(EntityContent).where(
            EntityContent.entity_id == entity_id,
            EntityContent.collection_id == collection_id,
            EntityContent.category == category,
            EntityContent.id != exclude_id,
            EntityContent.status.in_(statuses),
            EntityContent.is_deleted == False,
        )
    ).all()
    for s in siblings:
        s.status = ContentStatus.discarded
        session.add(s)
    return len(siblings)
