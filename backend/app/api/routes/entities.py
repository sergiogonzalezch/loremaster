from fastapi import APIRouter
import uuid
from app.services.documents_db_mock import entities

router = APIRouter()

@router.post("/entities")
async def create_entity(name: str, description: str):
    entity_id = str(uuid.uuid4())
    entity = {
        "id": entity_id,
        "name": name,
        "description": description
    }

    return entities[entity_id]