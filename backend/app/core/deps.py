from fastapi import Depends, HTTPException
from sqlmodel import Session

from app.core.common import get_active_by_id
from app.database import get_session
from app.models.collections import Collection
from app.models.documents import Document
from app.models.entities import Entity


def get_collection_or_404(
    collection_id: str,
    session: Session = Depends(get_session),
) -> Collection:
    collection = session.get(Collection, collection_id)
    if not collection or collection.is_deleted:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


def get_entity_or_404(
    entity_id: str,
    collection: Collection = Depends(get_collection_or_404),
    session: Session = Depends(get_session),
) -> Entity:
    entity = get_active_by_id(session, Entity, entity_id, collection.id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


def get_document_or_404(
    doc_id: str,
    collection: Collection = Depends(get_collection_or_404),
    session: Session = Depends(get_session),
) -> Document:
    doc = get_active_by_id(session, Document, doc_id, collection.id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc