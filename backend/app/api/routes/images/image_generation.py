"""Rutas de generación de imágenes para entidades."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.auth.dependencies import get_current_user
from app.core.database.dependencies import get_entity_or_404_owned
from app.core.exceptions import (
    DatabaseError,
    NoContextAvailableError,
)
from app.database import get_session
from app.models.db.entity import Entity
from app.models.schemas.image_generation import (
    BuildPromptRequest,
    BuildPromptResponse,
    GenerateImagesRequest,
    GenerateImagesResponse,
    ImageGenerationListResponse,
    ImageRecordResponse,
    ShareImageRequest,
)
from app.services.image.image_generation_service import (
    build_prompt_service,
    delete_image_service,
    generate_images_service,
    get_generation_service,
    list_generations_service,
    share_image_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collections", tags=["image-generation"])


@router.post(
    "/{collection_id}/entities/{entity_id}/image-generation/build-prompt",
    response_model=BuildPromptResponse,
)
def build_prompt(
    request: BuildPromptRequest,
    entity: Annotated[Entity, Depends(get_entity_or_404_owned)],
    session: Annotated[Session, Depends(get_session)],
):
    """Genera un prompt visual a partir de un contenido confirmado.

    Usa el LLM para transformar el texto del contenido en una descripción
    visual adecuada para generación de imágenes. No guarda nada en BD.
    """
    try:
        return build_prompt_service(session, entity, request.content_id)
    except NoContextAvailableError as e:
        raise HTTPException(
            status_code=422,
            detail=(
                "El contenido indicado no existe, no está confirmado "
                "o no pertenece a esta entidad."
            ),
        ) from e
    except Exception as e:
        logger.exception("Error inesperado en build_prompt")
        raise HTTPException(
            status_code=500, detail="Error interno del servidor.",
        ) from e


@router.post(
    "/{collection_id}/entities/{entity_id}/image-generation/generate",
    response_model=GenerateImagesResponse,
    status_code=201,
)
def generate_images(
    request: GenerateImagesRequest,
    entity: Annotated[Entity, Depends(get_entity_or_404_owned)],
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Genera un batch de imágenes usando ComfyUI o mock.

    Aplica guardrails al prompt antes de enviarlo al motor.
    """
    try:
        return generate_images_service(
            session,
            current_user["username"],
            entity,
            request.content_id,
            request.auto_prompt,
            request.final_prompt,
            request.batch_size,
            request.seed_base,
        )
    except NoContextAvailableError as e:
        raise HTTPException(
            status_code=422,
            detail=(
                "El contenido indicado no existe, no está confirmado "
                "o no pertenece a esta entidad."
            ),
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail="batch_size debe estar entre 1 y 4.",
        ) from e
    except DatabaseError as e:
        raise HTTPException(
            status_code=500, detail="Error interno del servidor.",
        ) from e
    except Exception as e:
        logger.exception("Error inesperado en generate_images")
        raise HTTPException(
            status_code=500, detail="Error interno del servidor.",
        ) from e


@router.patch(
    "/{collection_id}/entities/{entity_id}/image-generation/{generation_id}/images/{image_id}/share",
    response_model=ImageRecordResponse,
)
def share_image(
    generation_id: str,
    image_id: str,
    request: ShareImageRequest,
    entity: Annotated[Entity, Depends(get_entity_or_404_owned)],
    session: Annotated[Session, Depends(get_session)],
):
    """Marca o desmarca una imagen como compartida públicamente."""
    try:
        return share_image_service(
            session, entity, generation_id, image_id, shared=request.shared,
        )
    except NoContextAvailableError as e:
        raise HTTPException(status_code=404, detail="Imagen no encontrada.") from e
    except DatabaseError as e:
        raise HTTPException(
            status_code=500, detail="Error interno del servidor.",
        ) from e


@router.delete(
    "/{collection_id}/entities/{entity_id}/image-generation/{generation_id}/images/{image_id}",
    status_code=204,
)
def delete_image(
    generation_id: str,
    image_id: str,
    entity: Annotated[Entity, Depends(get_entity_or_404_owned)],
    session: Annotated[Session, Depends(get_session)],
):
    """Elimina una imagen individual del batch (soft delete)."""
    try:
        delete_image_service(session, entity, generation_id, image_id)
    except NoContextAvailableError as e:
        raise HTTPException(
            status_code=404,
            detail="Imagen no encontrada.",
        ) from e
    except DatabaseError as e:
        raise HTTPException(
            status_code=500, detail="Error interno del servidor.",
        ) from e
    except Exception as e:
        logger.exception("Error inesperado en delete_image")
        raise HTTPException(
            status_code=500, detail="Error interno del servidor.",
        ) from e


@router.get(
    "/{collection_id}/entities/{entity_id}/image-generation/{generation_id}",
    response_model=GenerateImagesResponse,
)
def get_generation(
    generation_id: str,
    entity: Annotated[Entity, Depends(get_entity_or_404_owned)],
    session: Annotated[Session, Depends(get_session)],
):
    """Obtiene una solicitud de generación con sus imágenes."""
    try:
        return get_generation_service(session, entity, generation_id)
    except NoContextAvailableError as e:
        raise HTTPException(
            status_code=404,
            detail="Generación no encontrada.",
        ) from e
    except Exception as e:
        logger.exception("Error inesperado en get_generation")
        raise HTTPException(
            status_code=500, detail="Error interno del servidor.",
        ) from e


@router.get(
    "/{collection_id}/entities/{entity_id}/image-generation",
    response_model=ImageGenerationListResponse,
)
def list_generations(
    entity: Annotated[Entity, Depends(get_entity_or_404_owned)],
    session: Annotated[Session, Depends(get_session)],
):
    """Lista todas las solicitudes de generación de imágenes de una entidad."""
    try:
        generations, total = list_generations_service(session, entity)
        return ImageGenerationListResponse(generations=generations, total=total)
    except Exception as e:
        logger.exception("Error inesperado en list_generations")
        raise HTTPException(
            status_code=500, detail="Error interno del servidor.",
        ) from e
