import logging
from datetime import datetime, timezone
from typing import Literal, Optional

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.exceptions import DuplicateEntityNameError
from app.core.database.utils import paginate_with_sort, db_commit
from app.models.db.entity import Entity, EntityType
from app.models.schemas.entity import CreateEntityRequest, UpdateEntityRequest
from app.services.deletion_service import cascade_delete_entity

logger = logging.getLogger(__name__)


def _find_by_name(session: Session, collection_id: str, name: str) -> Entity | None:
    """Reserva nombres incluso si la entidad fue soft-deleted."""
    return session.exec(
        select(Entity).where(
            Entity.collection_id == collection_id,
            Entity.name == name,
        )
    ).first()


def create_entity_service(
    session: Session, request: CreateEntityRequest, collection_id: str
) -> Entity:
    """Crea una nueva entidad dentro de una colección.

    Args:
        session: Sesión de base de datos activa.
        request: Datos de la entidad a crear.
        collection_id: Identificador de la colección.

    Returns:
        Instancia de la entidad creada.

    Raises:
        DuplicateEntityNameError: Si ya existe una entidad con ese nombre.
    """
    name = request.name.strip()
    description = request.description.strip()
    if _find_by_name(session, collection_id, name):
        raise DuplicateEntityNameError(name)
    entity = Entity(
        collection_id=collection_id,
        type=request.type,
        name=name,
        description=description,
    )
    session.add(entity)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise DuplicateEntityNameError(name)
    session.refresh(entity)
    logger.info("Entity '%s' created in collection %s", name, collection_id)
    return entity


def list_entities_service(
    session: Session,
    collection_id: str,
    page: int = 1,
    page_size: int = 20,
    name: Optional[str] = None,
    entity_type: Optional[EntityType] = None,
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None,
    order: Literal["asc", "desc"] = "desc",
) -> tuple[list[Entity], int]:
    """Lista las entidades de una colección con paginación y filtros.

    Args:
        session: Sesión de base de datos activa.
        collection_id: Identificador de la colección.
        page: Número de página.
        page_size: Elementos por página.
        name: Filtrar por nombre (búsqueda parcial).
        entity_type: Filtrar por tipo de entidad.
        created_after: Filtrar por fecha de creación mínima.
        created_before: Filtrar por fecha de creación máxima.
        order: Orden ascendente o descendente.

    Returns:
        Tupla de (lista de entidades, total de resultados).
    """
    conditions = [
        Entity.collection_id == collection_id,
        Entity.is_deleted == False,
    ]
    if name:
        conditions.append(Entity.name.ilike(f"%{name}%"))
    if entity_type:
        conditions.append(Entity.type == entity_type)
    if created_after:
        conditions.append(Entity.created_at >= created_after)
    if created_before:
        conditions.append(Entity.created_at <= created_before)

    return paginate_with_sort(
        session,
        Entity,
        conditions,
        page=page,
        page_size=page_size,
        order_col=Entity.created_at,
        order=order,
    )


def update_entity_service(
    session: Session,
    entity: Entity,
    request: UpdateEntityRequest,
    user_id: Optional[str] = None,
) -> Entity:
    """Actualiza los campos de una entidad existente.

    Args:
        session: Sesión de base de datos activa.
        entity: Instancia de la entidad a actualizar.
        request: Esquema con los campos a modificar.

    Returns:
        Instancia de la entidad actualizada.

    Raises:
        DuplicateEntityNameError: Si el nuevo nombre ya está en uso.
    """
    new_name = request.name.strip() if request.name is not None else entity.name
    if new_name != entity.name and _find_by_name(
        session, entity.collection_id, new_name
    ):
        raise DuplicateEntityNameError(new_name)
    if request.type is not None:
        entity.type = request.type
    if request.name is not None:
        entity.name = request.name.strip()
    if request.description is not None:
        entity.description = request.description.strip()
    entity.updated_at = datetime.now(timezone.utc)
    if user_id:
        entity.updated_by = user_id
    session.add(entity)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise DuplicateEntityNameError(new_name)
    session.refresh(entity)
    logger.info(
        "Entity '%s' updated in collection %s", entity.name, entity.collection_id
    )
    return entity


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
