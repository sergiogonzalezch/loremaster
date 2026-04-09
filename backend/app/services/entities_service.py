import uuid
from datetime import datetime, timezone

from app.models.entities import CreateEntityRequest, UpdateEntityRequest
from app.services.documents_db_mock import entities


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_entity_service(request: CreateEntityRequest, collection_id: str) -> dict:
    now = _now()
    entity = {
        "id": str(uuid.uuid4()),
        "collection_id": collection_id,
        "name": request.name,
        "description": request.description,
        "created_at": now,
        "updated_at": None,
        "is_deleted": False,
        "deleted_at": None,
    }
    entities[entity["id"]] = entity
    return entity


def get_entity_service(entity_id: str, collection_id: str) -> dict | None:
    entity = entities.get(entity_id)
    if not entity or entity["collection_id"] != collection_id or entity["is_deleted"]:
        return None
    return entity


def list_entities_service(collection_id: str) -> list[dict]:
    return [
        e
        for e in entities.values()
        if e["collection_id"] == collection_id and not e["is_deleted"]
    ]


def update_entity_service(
    entity_id: str, collection_id: str, request: UpdateEntityRequest
) -> dict | None:
    entity = entities.get(entity_id)
    if not entity or entity["collection_id"] != collection_id or entity["is_deleted"]:
        return None
    entity["name"] = request.name
    entity["description"] = request.description
    entity["updated_at"] = _now()
    return entity


def delete_entity_service(entity_id: str, collection_id: str) -> bool:
    entity = entities.get(entity_id)
    if not entity or entity["collection_id"] != collection_id or entity["is_deleted"]:
        return False
    now = _now()
    entity["is_deleted"] = True
    entity["deleted_at"] = now
    entity["updated_at"] = now
    return True
