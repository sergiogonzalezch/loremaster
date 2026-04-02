from fastapi import APIRouter
import uuid
from app.services.documents_db_mock import entities
from app.schemas.models import CreateEntityRequest
router = APIRouter()

@router.post("/entities")
async def create_entity(request: CreateEntityRequest):
    entity_id = str(uuid.uuid4())
    entities[entity_id] = {
        "id": entity_id,
        "name": request.name,
        "description": request.description
    }

    return entities[entity_id]