# backend/app/api/routes/image_generation.py

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.deps import get_entity_or_404
from app.core.exceptions import (
    DatabaseError,
    GeneratedContentBlockedError,
    ContentNotConfirmedError
)
from app.database import get_session
from app.models.entities import Entity
from app.models.image_generation import GenerateImageRequest, GenerateImageResponse
from app.services.image_generation_service import generate_image_service

router = APIRouter(prefix="/collections", tags=["image-generation"])


@router.post(
    "/{collection_id}/entities/{entity_id}/generate/image",
    response_model=GenerateImageResponse,
    status_code=201,
)
def generate_image(
    request: GenerateImageRequest,
    entity: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    try:
        return generate_image_service(session, entity, request.content_id)
    except ContentNotConfirmedError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except GeneratedContentBlockedError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Error interno del servidor.")
