from fastapi import APIRouter
from app.models.models import CreateEntityRequest
from app.services.entities_service import create_entity_service

router = APIRouter(prefix="/entities", tags=["entities"])


@router.post("/create", status_code=201)
async def create_entity(request: CreateEntityRequest):
    response = create_entity_service(request)
    return {"message": response, "status": "success"}
