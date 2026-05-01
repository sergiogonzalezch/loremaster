import logging
from datetime import datetime, timezone
from typing import Literal, Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Session, select

from app.core.exceptions import DatabaseError, DuplicateEntityNameError
from app.models.entities import (
    Entity,
    EntityType,
    CreateEntityRequest,
    UpdateEntityRequest,
)
from app.services.deletion_service import cascade_delete_entity

logger = logging.getLogger(__name__)


def _find_by_name(
    session: Session, collection_id: str, name: str
) -> Entity | None:
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

    total = session.exec(
        select(func.count()).select_from(select(Entity).where(*conditions).subquery())
    ).one()
    sort_col = Entity.created_at.asc() if order == "asc" else Entity.created_at.desc()
    skip = (page - 1) * page_size
    items = session.exec(
        select(Entity)
        .where(*conditions)
        .order_by(sort_col)
        .offset(skip)
        .limit(page_size)
    ).all()
    return list(items), total


def update_entity_service(
    session: Session, entity: Entity, request: UpdateEntityRequest
) -> Entity:
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
    try:
        cascade_delete_entity(session, entity)
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error("DB commit failed deleting entity %s: %s", entity.id, e)
        raise DatabaseError() from e
    logger.info(
        "Entity '%s' (%s) deleted from collection %s",
        entity.name,
        entity.id,
        entity.collection_id,
    )
    return True
