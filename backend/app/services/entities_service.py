import logging
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.database import engine
from app.models.entities import Entity, CreateEntityRequest, UpdateEntityRequest

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_entity_service(request: CreateEntityRequest, collection_id: str) -> Entity:
    with Session(engine) as session:
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


def get_entity_service(entity_id: str, collection_id: str) -> Entity | None:
    with Session(engine) as session:
        stmt = select(Entity).where(
            Entity.id == entity_id,
            Entity.collection_id == collection_id,
            Entity.is_deleted == False,
        )
        return session.exec(stmt).first()


def list_entities_service(collection_id: str) -> list[Entity]:
    with Session(engine) as session:
        stmt = select(Entity).where(
            Entity.collection_id == collection_id,
            Entity.is_deleted == False,
        )
        return session.exec(stmt).all()


def update_entity_service(
    entity_id: str, collection_id: str, request: UpdateEntityRequest
) -> Entity | None:
    with Session(engine) as session:
        stmt = select(Entity).where(
            Entity.id == entity_id,
            Entity.collection_id == collection_id,
            Entity.is_deleted == False,
        )
        entity = session.exec(stmt).first()
        if not entity:
            return None
        entity.type = request.type
        entity.name = request.name
        entity.description = request.description
        entity.updated_at = _now()
        session.add(entity)
        session.commit()
        session.refresh(entity)
        return entity


def delete_entity_service(entity_id: str, collection_id: str) -> bool:
    with Session(engine) as session:
        stmt = select(Entity).where(
            Entity.id == entity_id,
            Entity.collection_id == collection_id,
            Entity.is_deleted == False,
        )
        entity = session.exec(stmt).first()
        if not entity:
            return False
        now = _now()
        entity.is_deleted = True
        entity.deleted_at = now
        entity.updated_at = now
        session.add(entity)
        session.commit()
        logger.info("Entity %s soft-deleted from collection %s", entity_id, collection_id)
        return True
