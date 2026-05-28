"""Servicios de lógica de negocio para entidades."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.api.params import DateRangeParams, PaginationParams
from app.core.database.utils import bulk_delete_items, db_commit, paginate_with_sort
from app.core.exceptions import DuplicateNameError
from app.models.db.entity import Entity, EntityType
from app.models.schemas.entity import CreateEntityRequest, UpdateEntityRequest
from app.services.deletion_service import cascade_delete_entity

logger = logging.getLogger(__name__)


@dataclass
class EntityFilters:
    """Filtros opcionales para listar entidades de una colección."""

    name: str | None = None
    entity_type: EntityType | None = None


def _find_by_name(session: Session, collection_id: str, name: str) -> Entity | None:
    """Reserva nombres incluso si la entidad fue soft-deleted."""
    return session.exec(
        select(Entity).where(
            Entity.collection_id == collection_id,
            Entity.name == name,
        ),
    ).first()


def create_entity_service(
    session: Session,
    request: CreateEntityRequest,
    collection_id: str,
) -> Entity:
    """Crea una nueva entidad dentro de una colección.

    Args:
        session: Sesión de base de datos activa.
        request: Datos de la entidad a crear.
        collection_id: Identificador de la colección.

    Returns:
        Instancia de la entidad creada.

    Raises:
        DuplicateNameError: Si ya existe una entidad con ese nombre.

    """
    name = request.name.strip()
    description = request.description.strip()
    if _find_by_name(session, collection_id, name):
        raise DuplicateNameError(name, f"Ya existe una entidad llamada '{name}' en esta colección.")
    entity = Entity(
        collection_id=collection_id,
        type=request.type,
        name=name,
        description=description,
    )
    session.add(entity)
    try:
        session.commit()
    except IntegrityError as e:
        session.rollback()
        raise DuplicateNameError(name, f"Ya existe una entidad llamada '{name}' en esta colección.") from e
    session.refresh(entity)
    logger.info("Entity '%s' created in collection %s", name, collection_id)
    return entity


def list_entities_service(
    session: Session,
    collection_id: str,
    pagination: PaginationParams,
    dates: DateRangeParams,
    filters: EntityFilters | None = None,
) -> tuple[list[Entity], int]:
    """Lista las entidades de una colección con paginación y filtros.

    Args:
        session: Sesión de base de datos activa.
        collection_id: Identificador de la colección.
        pagination: Parámetros de paginación y orden.
        dates: Rango de fechas de creación.
        filters: Filtros opcionales de dominio (name, entity_type).

    Returns:
        Tupla de (lista de entidades, total de resultados).

    """
    f = filters or EntityFilters()
    conditions = [
        Entity.collection_id == collection_id,
        Entity.is_deleted.is_(False),
    ]
    if f.name:
        conditions.append(Entity.name.ilike(f"%{f.name}%"))
    if f.entity_type:
        conditions.append(Entity.type == f.entity_type)
    if dates.created_after:
        conditions.append(Entity.created_at >= dates.created_after)
    if dates.created_before:
        conditions.append(Entity.created_at <= dates.created_before)

    return paginate_with_sort(
        session,
        Entity,
        conditions,
        page=pagination.page,
        page_size=pagination.page_size,
        order_col=Entity.created_at,
        order=pagination.order,
    )


def update_entity_service(
    session: Session,
    entity: Entity,
    request: UpdateEntityRequest,
    user_id: str | None = None,
) -> Entity:
    """Actualiza los campos de una entidad existente.

    Args:
        session: Sesión de base de datos activa.
        entity: Instancia de la entidad a actualizar.
        request: Esquema con los campos a modificar.
        user_id: UUID del usuario que realiza la actualización (opcional).

    Returns:
        Instancia de la entidad actualizada.

    Raises:
        DuplicateNameError: Si el nuevo nombre ya está en uso.

    """
    new_name = request.name.strip() if request.name is not None else entity.name
    if new_name != entity.name and _find_by_name(
        session,
        entity.collection_id,
        new_name,
    ):
        raise DuplicateNameError(new_name, f"Ya existe una entidad llamada '{new_name}' en esta colección.")
    if request.type is not None:
        entity.type = request.type
    if request.name is not None:
        entity.name = request.name.strip()
    if request.description is not None:
        entity.description = request.description.strip()
    entity.updated_at = datetime.now(UTC)
    if user_id:
        entity.updated_by = user_id
    session.add(entity)
    try:
        session.commit()
    except IntegrityError as e:
        session.rollback()
        raise DuplicateNameError(new_name, f"Ya existe una entidad llamada '{new_name}' en esta colección.") from e
    session.refresh(entity)
    logger.info(
        "Entity '%s' updated in collection %s",
        entity.name,
        entity.collection_id,
    )
    return entity


def bulk_delete_entities_service(session: Session, ids: list[str], collection_id: str) -> None:
    """Elimina múltiples entidades en cascada filtrando por colección."""
    items = session.exec(
        select(Entity).where(
            Entity.id.in_(ids),
            Entity.collection_id == collection_id,
            Entity.is_deleted.is_(False),
        ),
    ).all()
    bulk_delete_items(session, items, delete_entity_service)


def delete_entity_service(session: Session, entity: Entity) -> bool:
    """Elimina una entidad y todos sus contenidos en cascada.

    Args:
        session: Sesión de base de datos activa.
        entity: Instancia de la entidad a eliminar.

    Returns:
        True siempre (la eliminación en cascada se encarga de todo).

    """
    cascade_delete_entity(session, entity)
    db_commit(session, f"delete_entity({entity.id})")
    logger.info(
        "Entity '%s' (%s) deleted from collection %s",
        entity.name,
        entity.id,
        entity.collection_id,
    )
    return True
