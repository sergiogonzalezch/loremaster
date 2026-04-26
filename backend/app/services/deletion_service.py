import logging
import time

from sqlmodel import Session, select

from app.models.collections import Collection
from app.models.documents import Document
from app.models.entities import Entity
from app.core.common import soft_delete
from app.engine.rag import delete_collection_vectors
from app.services import content_management_service

logger = logging.getLogger(__name__)

_QDRANT_RETRY_ATTEMPTS = 3
_QDRANT_RETRY_DELAY = 0.5


def _delete_vectors_with_retry(collection_id: str) -> bool:
    for attempt in range(1, _QDRANT_RETRY_ATTEMPTS + 1):
        try:
            delete_collection_vectors(collection_id)
            return True
        except Exception as e:
            if attempt < _QDRANT_RETRY_ATTEMPTS:
                logger.warning(
                    "Qdrant cleanup attempt %d/%d failed for collection %s: %s",
                    attempt,
                    _QDRANT_RETRY_ATTEMPTS,
                    collection_id,
                    e,
                )
                time.sleep(_QDRANT_RETRY_DELAY)
            else:
                logger.error(
                    "Orphan vectors remain in Qdrant for collection %s after %d attempts"
                    " — manual cleanup needed. collection_id=%s",
                    collection_id,
                    _QDRANT_RETRY_ATTEMPTS,
                    collection_id,
                    exc_info=True,
                )
    return False


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


def cascade_delete_collection(session: Session, collection: Collection) -> bool:
    """Soft-delete docs, entities (with their drafts), and Qdrant vectors.

    Returns True if Qdrant vectors were also cleaned up, False if they remain
    (orphan vectors — requires manual cleanup or retry when Qdrant is available).
    """
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

    return _delete_vectors_with_retry(collection.id)
