import logging

from sqlmodel import Session, select

from app.models.collections import Collection
from app.models.documents import Document
from app.models.entities import Entity
from app.core.common import soft_delete
from app.core.rag_engine import delete_collection_vectors
from app.services import content_management_service

logger = logging.getLogger(__name__)


def cascade_delete_entity(session: Session, entity: Entity) -> None:
    deleted_contents = content_management_service.cascade_delete_by_entity(
        session, entity.id, entity.collection_id
    )
    logger.info(
        "Soft-deleted %d EntityContent(s) for entity %s", deleted_contents, entity.id
    )

    soft_delete(session, entity)
    logger.info(
        "Entity %s soft-deleted from collection %s", entity.id, entity.collection_id
    )


def cascade_delete_collection(session: Session, collection: Collection) -> None:
    """Soft-delete docs, entities (with their drafts), and Qdrant vectors."""
    docs = session.exec(
        select(Document).where(
            Document.collection_id == collection.id,
            Document.is_deleted == False,
        )
    ).all()
    for doc in docs:
        soft_delete(session, doc)
    logger.info(
        "Soft-deleted %d document(s) for collection %s", len(docs), collection.id
    )

    entities = session.exec(
        select(Entity).where(
            Entity.collection_id == collection.id,
            Entity.is_deleted == False,
        )
    ).all()
    for entity in entities:
        cascade_delete_entity(session, entity)
    logger.info(
        "Soft-deleted %d entity(ies) for collection %s", len(entities), collection.id
    )

    orphan_contents = content_management_service.cascade_delete_by_collection(
        session, collection.id
    )
    if orphan_contents > 0:
        logger.info(
            "Soft-deleted %d orphan EntityContent(s) for collection %s",
            orphan_contents,
            collection.id,
        )

    soft_delete(session, collection)
    logger.info("Collection %s soft-deleted", collection.id)

    try:
        delete_collection_vectors(collection.id)
    except Exception as e:
        logger.error("Failed to delete vectors for collection %s: %s", collection.id, e)
