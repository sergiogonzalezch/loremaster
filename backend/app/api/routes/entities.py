from fastapi import APIRouter
from app.models.models import CreateEntityRequest

router = APIRouter(prefix="/entities", tags=["entities"])


@router.post("/create")
async def create_entity(request: CreateEntityRequest):
    response = create_entity(request)
    return {"message": response, "status": "success"}
