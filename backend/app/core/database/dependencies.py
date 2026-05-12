from fastapi import Depends, HTTPException
from sqlmodel import Session

from app.core.auth.dependencies import get_current_user
from app.core.database.utils import get_active_by_id
from app.database import get_session
from app.models.db.collection import Collection
from app.models.db.document import Document
from app.models.db.entity import Entity
from app.models.db.user import User


def get_collection_or_404(
    collection_id: str,
    session: Session = Depends(get_session),
) -> Collection:
    """Obtiene una colección por ID. Lanza 404 si no existe o está eliminada."""
    collection = session.get(Collection, collection_id)
    if not collection or collection.is_deleted:
        raise HTTPException(status_code=404, detail="Colección no encontrada.")
    return collection


def get_collection_or_404_owned(
    collection_id: str,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Collection:
    """Obtiene una colección verificando que pertenezca al usuario actual.

    Lanza 404 si no existe, 403 si no es dueña.
    """
    collection = session.get(Collection, collection_id)
    if not collection or collection.is_deleted:
        raise HTTPException(status_code=404, detail="Colección no encontrada.")
    if collection.owner_id != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    return collection


def get_entity_or_404(
    entity_id: str,
    collection: Collection = Depends(get_collection_or_404),
    session: Session = Depends(get_session),
) -> Entity:
    """Obtiene una entidad por ID dentro de una colección. Lanza 404 si no existe."""
    entity = get_active_by_id(session, Entity, entity_id, collection.id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entidad no encontrada.")
    return entity


def get_entity_or_404_owned(
    entity_id: str,
    collection: Collection = Depends(get_collection_or_404_owned),
    session: Session = Depends(get_session),
) -> Entity:
    """Obtiene una entidad verificando que la colección sea del usuario actual.

    Lanza 404 si no existe, 403 si la colección no pertenece al usuario.
    """
    entity = get_active_by_id(session, Entity, entity_id, collection.id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entidad no encontrada.")
    return entity


def get_document_or_404(
    doc_id: str,
    collection: Collection = Depends(get_collection_or_404),
    session: Session = Depends(get_session),
) -> Document:
    """Obtiene un documento por ID dentro de una colección. Lanza 404 si no existe."""
    doc = get_active_by_id(session, Document, doc_id, collection.id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")
    return doc


def get_document_or_404_owned(
    doc_id: str,
    collection: Collection = Depends(get_collection_or_404_owned),
    session: Session = Depends(get_session),
) -> Document:
    """Obtiene un documento verificando que la colección sea del usuario actual.

    Lanza 404 si no existe o si la colección no pertenece al usuario.
    """
    doc = get_active_by_id(session, Document, doc_id, collection.id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")
    return doc


def get_current_db_user(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> User:
    """Obtiene el usuario actual desde la base de datos. Lanza 404 si no existe."""
    user = session.get(User, current_user["sub"])
    if not user or user.is_deleted:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return user
