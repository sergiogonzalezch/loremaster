import uuid
from app.services.documents_db_mock import entities


def create_entity_service(request, collection_id: str):
    entity_id = str(uuid.uuid4())

    entity = {
        "id": entity_id,
        "collection_id": collection_id,
        "name": request.name,
        "description": request.description,
    }

    entities[entity_id] = entity
    return entity


def get_entity_service(entity_id: str, collection_id: str):
    entity = entities.get(entity_id)

    if not entity or entity["collection_id"] != collection_id:
        return None

    return entity


def list_entities_service(collection_id: str):
    return [
        entity
        for entity in entities.values()
        if entity["collection_id"] == collection_id
    ]


def update_entity_service(entity_id: str, collection_id: str, request):
    entity = entities.get(entity_id)

    if not entity or entity["collection_id"] != collection_id:
        return None

    entity["name"] = request.name
    entity["description"] = request.description

    return entity


def delete_entity_service(entity_id: str, collection_id: str):
    entity = entities.get(entity_id)

    if not entity or entity["collection_id"] != collection_id:
        return False

    del entities[entity_id]
    return True
