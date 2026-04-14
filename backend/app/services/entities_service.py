import logging
from datetime import datetime, timezone

from sqlmodel import Session

from app.models.entities import Entity, CreateEntityRequest, UpdateEntityRequest
from app.core.common import get_active_by_id, list_active_by_collection, soft_delete

logger = logging.getLogger(__name__)


def create_entity_service(
    session: Session, request: CreateEntityRequest, collection_id: str
) -> Entity:
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
    session: Session, entity_id: str, collection_id: str, request: UpdateEntityRequest
) -> Entity | None:
    entity = get_active_by_id(session, Entity, entity_id, collection_id)
    if not entity:
        return None
    entity.type = request.type
    entity.name = request.name
    entity.description = request.description
    entity.updated_at = datetime.now(timezone.utc)
    session.add(entity)
    session.commit()
    session.refresh(entity)
    return entity


def delete_entity_service(session: Session, entity_id: str, collection_id: str) -> bool:
    entity = get_active_by_id(session, Entity, entity_id, collection_id)
    if not entity:
        return False
    soft_delete(session, entity)
    session.commit()
    logger.info("Entity %s soft-deleted from collection %s", entity_id, collection_id)
    return True
