# app/api/routes/image_generation.py

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.deps import get_entity_or_404
from app.core.exceptions import ContentNotAllowedError, NoContextAvailableError
from app.database import get_session
from app.models.entities import Entity
from app.models.image_generation import GenerateImageRequest, GenerateImageResponse
from app.services.image_generation_service import generate_image_service

router = APIRouter(prefix="/collections", tags=["image-generation"])


@router.post(
    "/{collection_id}/entities/{entity_id}/generate/image",
    response_model=GenerateImageResponse,
    status_code=200,
)
def generate_image(
    request: GenerateImageRequest,
    entity: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    try:
        return generate_image_service(session, entity, request.content_id)
    except NoContextAvailableError:
        raise HTTPException(
            status_code=422,
            detail=(
                "La entidad no tiene contenido confirmado. "
                "Genera y confirma al menos un contenido antes de crear una imagen."
            ),
        )
    except ContentNotAllowedError as e:
        raise HTTPException(status_code=422, detail=str(e))