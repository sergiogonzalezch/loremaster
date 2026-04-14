import logging
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.database import engine
from app.models.collections import Collection
from app.models.documents import Document
from app.models.entities import Entity
from app.services.rag_engine import delete_collection_vectors

logger = logging.getLogger(__name__)


def create_collection_service(name: str, description: str = "") -> Collection:
    with Session(engine) as session:
        collection = Collection(name=name, description=description)
        session.add(collection)
        session.commit()
        session.refresh(collection)
        logger.info("Collection '%s' created with id %s", name, collection.id)
        return collection


def list_collections_service() -> list[Collection]:
    with Session(engine) as session:
        stmt = select(Collection).where(Collection.is_deleted == False)
        return session.exec(stmt).all()


def get_collection_service(collection_id: str) -> Collection | None:
    with Session(engine) as session:
        collection = session.get(Collection, collection_id)
        if not collection or collection.is_deleted:
            return None
        return collection


def collection_exists(collection_id: str) -> bool:
    return get_collection_service(collection_id) is not None


def delete_collection_service(collection_id: str):
    with Session(engine) as session:
        collection = session.get(Collection, collection_id)
        if not collection or collection.is_deleted:
            return None
        collection.is_deleted = True
        collection.deleted_at = datetime.now(timezone.utc)
        session.add(collection)
        session.commit()
        logger.info("Collection %s soft-deleted", collection_id)

        docs_stmt = select(Document).where(
            Document.collection_id == collection_id,
            Document.is_deleted == False,
        )
        for doc in session.exec(docs_stmt).all():
            doc.is_deleted = True
            doc.deleted_at = datetime.now(timezone.utc)
            session.add(doc)

        entities_stmt = select(Entity).where(
            Entity.collection_id == collection_id,
            Entity.is_deleted == False,
        )
        for entity in session.exec(entities_stmt).all():
            entity.is_deleted = True
            entity.deleted_at = datetime.now(timezone.utc)
            session.add(entity)

        session.commit()

        try:
            delete_collection_vectors(collection_id)
        except Exception as e:
            logger.warning(
                "Failed to delete vectors for collection %s: %s", collection_id, e
            )
        return True
