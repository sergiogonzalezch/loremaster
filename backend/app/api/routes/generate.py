from fastapi import APIRouter
from app.services.generate_service import text_generation_service
from app.models.generate import GenerateTextRequest

router = APIRouter(prefix="/collections", tags=["generate"])


@router.post("/{collection_id}/generate/text")
async def generate(request: GenerateTextRequest, collection_id: str):
    return await text_generation_service(request.query, collection_id=collection_id)
