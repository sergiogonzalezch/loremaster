from fastapi import APIRouter
from app.services.generate_service import generate_response
from app.models.models import GenerateTextRequest

router = APIRouter(prefix="/generate", tags=["generate"])


@router.post("/text")
async def generate(request: GenerateTextRequest, collection_id: str = None):
    return {
        "message": generate_response(request.query, collection_id=collection_id),
        "status": "success",
    }
