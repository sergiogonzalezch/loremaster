# backend/app/api/routes/image_generation.py

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.deps import get_entity_or_404
from app.core.exceptions import (
    DatabaseError,
    NoContextAvailableError,
)
from app.database import get_session
from app.models.entities import Entity
from app.models.image_generation import (
    BuildPromptRequest,
    BuildPromptResponse,
    GenerateImagesRequest,
    GenerateImagesResponse,
    ImageGenerationListResponse,
)
from app.services.image_generation_service import (
    build_prompt_service,
    generate_images_service,
    delete_image_service,
    get_generation_service,
    list_generations_service,
)

router = APIRouter(prefix="/collections", tags=["image-generation"])


@router.post(
    "/{collection_id}/entities/{entity_id}/image-generation/build-prompt",
    response_model=BuildPromptResponse,
)
def build_prompt(
    request: BuildPromptRequest,
    entity: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    """Construye el prompt automático sin guardar nada."""
    try:
        return build_prompt_service(session, entity, request.content_id)
    except NoContextAvailableError:
        raise HTTPException(
            status_code=422,
            detail=(
                "El contenido indicado no existe, no está confirmado "
                "o no pertenece a esta entidad."
            ),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{collection_id}/entities/{entity_id}/image-generation/generate",
    response_model=GenerateImagesResponse,
    status_code=201,
)
def generate_images(
    request: GenerateImagesRequest,
    entity: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    """Genera el batch de imágenes."""
    try:
        return generate_images_service(
            session,
            entity,
            request.content_id,
            request.final_prompt,
            request.batch_size,
        )
    except NoContextAvailableError:
        raise HTTPException(
            status_code=422,
            detail=(
                "El contenido indicado no existe, no está confirmado "
                "o no pertenece a esta entidad."
            ),
        )
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="batch_size debe estar entre 1 y 4.",
        )
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Error interno del servidor.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{collection_id}/entities/{entity_id}/image-generation/{generation_id}/images/{image_id}",
    status_code=204,
)
def delete_image(
    generation_id: str,
    image_id: str,
    entity: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    """Elimina una imagen individual del batch."""
    try:
        delete_image_service(session, entity, generation_id, image_id)
    except NoContextAvailableError:
        raise HTTPException(
            status_code=404,
            detail="Imagen no encontrada.",
        )
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Error interno del servidor.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{collection_id}/entities/{entity_id}/image-generation/{generation_id}",
    response_model=GenerateImagesResponse,
)
def get_generation(
    generation_id: str,
    entity: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    """Obtiene una generación existente con sus imágenes."""
    try:
        return get_generation_service(session, entity, generation_id)
    except NoContextAvailableError:
        raise HTTPException(
            status_code=404,
            detail="Generación no encontrada.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{collection_id}/entities/{entity_id}/image-generation",
    response_model=ImageGenerationListResponse,
)
def list_generations(
    entity: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    """Lista todas las generaciones de imágenes de una entidad."""
    try:
        generations, total = list_generations_service(session, entity)
        return ImageGenerationListResponse(generations=generations, total=total)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))