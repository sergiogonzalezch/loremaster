from fastapi import APIRouter
from app.services.generate_service import generate_response
from app.models.models import GenerateTextRequest

router = APIRouter(prefix="/collections", tags=["generate"])


@router.post("/{collection_id}/text")
async def generate(request: GenerateTextRequest, collection_id: str):
    return {
        "message": generate_response(request.query, collection_id=collection_id),
        "status": "success",
    }
