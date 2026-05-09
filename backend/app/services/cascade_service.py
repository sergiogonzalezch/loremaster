import logging

from sqlmodel import Session, select

from app.core.database.utils import soft_delete
from app.models.db.entity_content import EntityContent

logger = logging.getLogger(__name__)


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
