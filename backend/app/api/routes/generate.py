from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.dependencies import get_valid_collection
from app.database import get_session
from app.models.collections import Collection
from app.services.generate_service import text_generation_service
from app.models.generate import GenerateTextRequest, GenerateTextResponse

router = APIRouter(prefix="/collections", tags=["generate"])


@router.post("/{collection_id}/text", response_model=GenerateTextResponse)
async def generate(
    request: GenerateTextRequest,
    collection_id: str,
    collection: Collection = Depends(get_valid_collection),
    session: Session = Depends(get_session),
):
    return await text_generation_service(
        session, request.query, collection_id=collection_id
    )
