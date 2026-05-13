"""Servicios de lógica de negocio para colecciones."""

import logging
from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.api.params import DateRangeParams, PaginationParams
from app.core.database.utils import db_commit, paginate_with_sort
from app.core.exceptions import DuplicateCollectionNameError
from app.models.db.collection import Collection
from app.models.db.document import Document
from app.models.db.entity import Entity
from app.models.schemas.collection import UpdateCollectionRequest
from app.services.deletion_service import cascade_delete_collection

logger = logging.getLogger(__name__)


def _fetch_counts(
    session: Session,
    collection_ids: list[str],
) -> tuple[dict[str, int], dict[str, int]]:
    if not collection_ids:
        return {}, {}
    doc_rows = session.exec(
        select(Document.collection_id, func.count(Document.id))
        .where(
            Document.collection_id.in_(collection_ids),
            Document.is_deleted.is_(False),
        )
        .group_by(Document.collection_id),
    ).all()
    entity_rows = session.exec(
        select(Entity.collection_id, func.count(Entity.id))
        .where(
            Entity.collection_id.in_(collection_ids),
            Entity.is_deleted.is_(False),
        )
        .group_by(Entity.collection_id),
    ).all()
    return (
        dict(doc_rows),
        dict(entity_rows),
    )


def get_collection_with_counts_service(
    session: Session,
    collection: Collection,
) -> dict:
    """Enriquece una colección con recuentos de documentos y entidades.

    Args:
        session: Sesión de base de datos activa.
        collection: Instancia de la colección a enriquecer.

    Returns:
        Diccionario con los datos de la colección más document_count y entity_count.

    """
    doc_counts, entity_counts = _fetch_counts(session, [collection.id])
    return {
        **collection.model_dump(),
        "document_count": doc_counts.get(collection.id, 0),
        "entity_count": entity_counts.get(collection.id, 0),
    }


def create_collection_service(
    session: Session,
    owner_id: str,
    name: str,
    description: str = "",
) -> Collection:
    """Crea una nueva colección para un usuario.

    Valida que no exista otra colección con el mismo nombre para el propietario.

    Args:
        session: Sesión de base de datos activa.
        owner_id: UUID del usuario propietario.
        name: Nombre de la colección.
        description: Descripción opcional.

    Returns:
        Instancia de la colección creada.

    Raises:
        DuplicateCollectionNameError: Si ya existe una colección con ese nombre.

    """
    name = name.strip()
    description = description.strip()
    existing = session.exec(
        select(Collection).where(
            Collection.name == name,
            Collection.owner_id == owner_id,
            Collection.is_deleted.is_(False),
        ),
    ).first()
    if existing:
        raise DuplicateCollectionNameError(name)

    collection = Collection(name=name, description=description, owner_id=owner_id)
    session.add(collection)
    try:
        session.commit()
    except IntegrityError as e:
        session.rollback()
        raise DuplicateCollectionNameError(name) from e
    session.refresh(collection)
    logger.info(
        "Collection '%s' created with id %s (owner: %s)",
        name,
        collection.id,
        owner_id,
    )
    return collection


def list_collections_service(
    session: Session,
    owner_id: str,
    pagination: PaginationParams,
    dates: DateRangeParams,
    name: str | None = None,
) -> tuple[list[dict], int]:
    """Lista las colecciones de un usuario con paginación y filtros.

    Args:
        session: Sesión de base de datos activa.
        owner_id: UUID del propietario.
        pagination: Parámetros de paginación y orden.
        dates: Rango de fechas de creación.
        name: Filtrar por nombre (búsqueda parcial, case-insensitive).

    Returns:
        Tupla de (lista de colecciones enriquecidas con counts, total de resultados).

    """
    conditions = [Collection.is_deleted.is_(False), Collection.owner_id == owner_id]
    if name:
        conditions.append(Collection.name.ilike(f"%{name}%"))
    if dates.created_after:
        conditions.append(Collection.created_at >= dates.created_after)
    if dates.created_before:
        conditions.append(Collection.created_at <= dates.created_before)

    items, total = paginate_with_sort(
        session,
        Collection,
        conditions,
        page=pagination.page,
        page_size=pagination.page_size,
        order_col=Collection.created_at,
        order=pagination.order,
    )
    collection_ids = [c.id for c in items]
    doc_counts, entity_counts = _fetch_counts(session, collection_ids)
    enriched = [
        {
            **c.model_dump(),
            "document_count": doc_counts.get(c.id, 0),
            "entity_count": entity_counts.get(c.id, 0),
        }
        for c in items
    ]
    return enriched, total


def update_collection_service(
    session: Session,
    collection: Collection,
    request: UpdateCollectionRequest,
    user_id: str | None = None,
) -> Collection:
    """Actualiza el nombre y/o descripción de una colección.

    Args:
        session: Sesión de base de datos activa.
        collection: Instancia de la colección a actualizar.
        request: Esquema con los campos a modificar.
        user_id: UUID del usuario que realiza la actualización (opcional).

    Returns:
        Instancia de la colección actualizada.

    Raises:
        DuplicateCollectionNameError: Si el nuevo nombre ya está en uso.

    """
    new_name = request.name.strip() if request.name is not None else collection.name
    if new_name != collection.name:
        existing = session.exec(
            select(Collection).where(
                Collection.name == new_name,
                Collection.owner_id == collection.owner_id,
                Collection.is_deleted.is_(False),
                Collection.id != collection.id,
            ),
        ).first()
        if existing:
            raise DuplicateCollectionNameError(new_name)

    if request.name is not None:
        collection.name = request.name.strip()
    if request.description is not None:
        collection.description = request.description.strip()

    collection.updated_at = datetime.now(timezone.utc)
    if user_id:
        collection.updated_by = user_id
    session.add(collection)
    try:
        session.commit()
    except IntegrityError as e:
        session.rollback()
        raise DuplicateCollectionNameError(new_name) from e
    session.refresh(collection)
    logger.info("Collection '%s' updated (id %s)", collection.name, collection.id)
    return collection


def delete_collection_service(session: Session, collection: Collection) -> bool:
    """Elimina una colección en cascada (documentos, entidades, vectores).

    Args:
        session: Sesión de base de datos activa.
        collection: Instancia de la colección a eliminar.

    Returns:
        True si los vectores de Qdrant fueron eliminados exitosamente;
        False si quedaron vectores huérfanos.

    """
    vectors_cleaned = cascade_delete_collection(session, collection)
    db_commit(session, f"delete_collection({collection.id})")
    logger.info("Collection '%s' (%s) deleted", collection.name, collection.id)
    return vectors_cleaned
