from fastapi import Depends, HTTPException
from sqlmodel import Session

from app.database import get_session
from app.models.collections import Collection
from app.models.documents import Document
from app.models.entities import Entity


def get_valid_collection(
    collection_id: str,
    session: Session = Depends(get_session),
) -> Collection:
    collection = session.get(Collection, collection_id)
    if not collection or collection.is_deleted:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


def get_entity_or_404(
    entity_id: str,
    collection: Collection = Depends(get_valid_collection),
    session: Session = Depends(get_session),
) -> Entity:
    from app.services.entities_service import get_entity_service
    entity = get_entity_service(session, entity_id, collection.id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


def get_document_or_404(
    doc_id: str,
    collection: Collection = Depends(get_valid_collection),
    session: Session = Depends(get_session),
) -> Document:
    from app.services.documents_service import get_document_service
    doc = get_document_service(session, collection.id, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
