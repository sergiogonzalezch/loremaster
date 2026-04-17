import logging

from sqlmodel import Session, select

from app.models.collections import Collection
from app.models.documents import Document
from app.models.entities import Entity
from app.core.common import soft_delete
from app.core.rag_engine import delete_collection_vectors
from app.services.entity_text_draft_service import soft_delete_all_drafts

logger = logging.getLogger(__name__)


def cascade_delete_entity(session: Session, entity: Entity) -> None:
    """Soft-delete all drafts for the entity, then soft-delete the entity itself."""
    deleted = soft_delete_all_drafts(
        session, entity_id=entity.id, collection_id=entity.collection_id
    )
    logger.info("Soft-deleted %d draft(s) for entity %s", deleted, entity.id)
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
    logger.info("Soft-deleted %d document(s) for collection %s", len(docs), collection.id)

    entities = session.exec(
        select(Entity).where(
            Entity.collection_id == collection.id,
            Entity.is_deleted == False,
        )
    ).all()
    for entity in entities:
        cascade_delete_entity(session, entity)
    logger.info("Soft-deleted %d entity(ies) for collection %s", len(entities), collection.id)

    remaining = soft_delete_all_drafts(session, collection_id=collection.id)
    if remaining > 0:
        logger.info("Soft-deleted %d orphan draft(s) for collection %s", remaining, collection.id)

    soft_delete(session, collection)
    logger.info("Collection %s soft-deleted", collection.id)

    try:
        delete_collection_vectors(collection.id)
    except Exception as e:
        logger.error("Failed to delete vectors for collection %s: %s", collection.id, e)