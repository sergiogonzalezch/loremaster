from fastapi import APIRouter
from app.schemas.models import CreateEntityRequest

router = APIRouter()


@router.post("/entities")
async def create_entity(request: CreateEntityRequest):
    response = create_entity(request)
    return {"message": response, "status": "success"}
