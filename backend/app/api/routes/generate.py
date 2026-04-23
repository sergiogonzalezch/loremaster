from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import get_collection_or_404
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
    try:
        return text_generation_service(request.query, collection_id=collection_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
