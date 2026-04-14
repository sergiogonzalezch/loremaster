from datetime import datetime, timezone

from sqlmodel import Session, select

from app.database import engine
from app.models.collections import Collection
from app.services import rag_engine


def create_collection_service(name: str, description: str = "") -> Collection:
    with Session(engine) as session:
        collection = Collection(name=name, description=description)
        session.add(collection)
        session.commit()
        session.refresh(collection)
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
        rag_engine.delete_collection_vectors(collection_id)
        collection.is_deleted = True
        collection.deleted_at = datetime.now(timezone.utc)
        session.add(collection)
        session.commit()
        return True
