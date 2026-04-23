import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.models.entities import Entity, EntityType, CreateEntityRequest, UpdateEntityRequest
from app.services.deletion_service import cascade_delete_entity

logger = logging.getLogger(__name__)


def _find_active_by_name(
    session: Session, collection_id: str, name: str
) -> Entity | None:
    return session.exec(
        select(Entity).where(
            Entity.collection_id == collection_id,
            Entity.name == name,
            Entity.is_deleted == False,
        )
    ).first()


def create_entity_service(
    session: Session, request: CreateEntityRequest, collection_id: str
) -> Entity:
    if _find_active_by_name(session, collection_id, request.name):
        raise HTTPException(
            status_code=409,
            detail=f"An entity named '{request.name}' already exists in this collection.",
        )
    entity = Entity(
        collection_id=collection_id,
        type=request.type,
        name=request.name,
        description=request.description,
    )
    session.add(entity)
    session.commit()
    session.refresh(entity)
    logger.info("Entity '%s' created in collection %s", request.name, collection_id)
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
        select(func.count()).select_from(
            select(Entity).where(*conditions).subquery()
        )
    ).one()
    skip = (page - 1) * page_size
    items = session.exec(
        select(Entity).where(*conditions).offset(skip).limit(page_size)
    ).all()
    return list(items), total


def update_entity_service(
    session: Session, entity: Entity, request: UpdateEntityRequest
) -> Entity:
    new_name = request.name if request.name is not None else entity.name
    if new_name != entity.name and _find_active_by_name(
        session, entity.collection_id, new_name
    ):
        raise HTTPException(
            status_code=409,
            detail=f"An entity named '{new_name}' already exists in this collection.",
        )
    if request.type is not None:
        entity.type = request.type
    if request.name is not None:
        entity.name = request.name
    if request.description is not None:
        entity.description = request.description
    entity.updated_at = datetime.now(timezone.utc)
    session.add(entity)
    session.commit()
    session.refresh(entity)
    return entity


def delete_entity_service(session: Session, entity: Entity) -> bool:
    cascade_delete_entity(session, entity)
    session.commit()
    return True
