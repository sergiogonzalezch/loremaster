import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.entities import Entity, CreateEntityRequest, UpdateEntityRequest
from app.core.common import get_active_by_id, list_active_by_collection, soft_delete
from app.services.entity_text_draft_service import soft_delete_all_drafts

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


def get_entity_service(
    session: Session, entity_id: str, collection_id: str
) -> Entity | None:
    return get_active_by_id(session, Entity, entity_id, collection_id)


def list_entities_service(session: Session, collection_id: str) -> list[Entity]:
    return list_active_by_collection(session, Entity, collection_id)


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
    deleted = soft_delete_all_drafts(
        session, entity_id=entity.id, collection_id=entity.collection_id
    )
    logger.info("Soft-deleted %d draft(s) for entity %s", deleted, entity.id)
    soft_delete(session, entity)
    session.commit()
    logger.info(
        "Entity %s soft-deleted from collection %s", entity.id, entity.collection_id
    )
    return True
