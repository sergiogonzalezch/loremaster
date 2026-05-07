from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session

from app.core.common import get_active_by_id
from app.core.auth_deps import get_current_user, security, verify_token
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
        raise HTTPException(status_code=404, detail="Colección no encontrada.")
    return collection


def get_collection_or_404_owned(
    collection_id: str,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Collection:
    collection = session.get(Collection, collection_id)
    if not collection or collection.is_deleted:
        raise HTTPException(status_code=404, detail="Colección no encontrada.")
    if collection.owner_id != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    return collection


def get_collection_or_404_public_or_owned(
    collection_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
) -> Collection:
    collection = session.get(Collection, collection_id)
    if not collection or collection.is_deleted:
        raise HTTPException(status_code=404, detail="Colección no encontrada.")
    if collection.is_public:
        return collection
    if credentials:
        payload = verify_token(credentials.credentials)
        if collection.owner_id == payload.get("sub"):
            return collection
    raise HTTPException(status_code=403, detail="Acceso denegado.")


def get_entity_or_404(
    entity_id: str,
    collection: Collection = Depends(get_collection_or_404),
    session: Session = Depends(get_session),
) -> Entity:
    entity = get_active_by_id(session, Entity, entity_id, collection.id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entidad no encontrada.")
    return entity


def get_document_or_404(
    doc_id: str,
    collection: Collection = Depends(get_collection_or_404),
    session: Session = Depends(get_session),
) -> Document:
    doc = get_active_by_id(session, Document, doc_id, collection.id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")
    return doc
