from app.services.documents_db_mock import entities
import uuid


def create_entity_service(request: dict):
    entity_id = str(uuid.uuid4())
    entities[entity_id] = {
        "id": entity_id,
        "name": request.name,
        "description": request.description,
    }

    return f"Entidad creada con ID: {entity_id}, nombre: {request.name}, descripción: {request.description}"
