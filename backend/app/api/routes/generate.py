from fastapi import APIRouter
from app.services.generate_service import generate_response
from app.models.generate import GenerateTextRequest

router = APIRouter(prefix="/collections", tags=["generate"])


@router.post("/{collection_id}/generate/text")
async def generate(request: GenerateTextRequest, collection_id: str):
    return {
        "message": await generate_response(request.query, collection_id=collection_id),
        "status": "success",
    }
