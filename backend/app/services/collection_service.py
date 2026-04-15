import logging

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.collections import Collection
from app.models.documents import Document
from app.models.entities import Entity
from app.core.common import soft_delete
from app.core.rag_engine import delete_collection_vectors
from app.services.entity_text_draft_service import discard_pending_drafts

logger = logging.getLogger(__name__)


def create_collection_service(
    session: Session, name: str, description: str = ""
) -> Collection:
    existing = session.exec(
        select(Collection).where(
            Collection.name == name,
            Collection.is_deleted == False,
        )
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Collection name already exists")

    collection = Collection(name=name, description=description)
    session.add(collection)
    session.commit()
    session.refresh(collection)
    logger.info("Collection '%s' created with id %s", name, collection.id)
    return collection


def list_collections_service(session: Session) -> list[Collection]:
    stmt = select(Collection).where(Collection.is_deleted == False)
    return session.exec(stmt).all()


def get_collection_service(session: Session, collection_id: str) -> Collection | None:
    collection = session.get(Collection, collection_id)
    if not collection or collection.is_deleted:
        return None
    return collection


def _cascade_soft_delete_children(session: Session, collection_id: str) -> None:
    for model in (Document, Entity):
        stmt = select(model).where(
            model.collection_id == collection_id,
            model.is_deleted == False,
        )
        for record in session.exec(stmt).all():
            soft_delete(session, record)

    count = discard_pending_drafts(session, collection_id=collection_id)
    logger.info("Discarded %d pending draft(s) for collection %s", count, collection_id)


def delete_collection_service(session: Session, collection_id: str):
    collection = session.get(Collection, collection_id)
    if not collection or collection.is_deleted:
        return False

    _cascade_soft_delete_children(session, collection_id)
    soft_delete(session, collection)

    session.commit()
    logger.info("Collection %s and its children soft-deleted", collection_id)

    try:
        delete_collection_vectors(collection_id)
    except Exception as e:
        logger.error("Failed to delete vectors for collection %s: %s", collection_id, e)

    return True
