from fastapi import APIRouter, Depends

from app.core.valid_collection import get_collection_or_404
from app.models.collections import Collection
from app.services.generate_service import text_generation_service
from app.models.generate import GenerateTextRequest, GenerateTextResponse

router = APIRouter(prefix="/collections", tags=["generate"])


@router.post("/{collection_id}/generate/text", response_model=GenerateTextResponse)
async def generate(
    request: GenerateTextRequest,
    collection_id: str,
    _: Collection = Depends(get_collection_or_404),
):
    return text_generation_service(request.query, collection_id=collection_id)
