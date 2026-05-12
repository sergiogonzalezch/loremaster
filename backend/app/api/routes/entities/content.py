from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session

from app.core.api.params import PaginationParams
from app.core.auth.dependencies import get_current_user
from app.core.database.dependencies import get_entity_or_404_owned
from app.core.exceptions import (
    ContentDiscardedError,
    ContentNotAllowedError,
    ContentNotShareableError,
    DatabaseError,
    GeneratedContentBlockedError,
    InvalidCategoryError,
    NoContextAvailableError,
    PendingLimitExceededError,
)
from app.database import get_session
from app.models.db.entity import Entity
from app.models.schemas.entity import EntityResponse
from app.models.schemas.entity_content import (
    EntityContentResponse,
    GenerateContentRequest,
    ShareContentRequest,
    UpdateContentRequest,
)
from app.models.enums import ContentCategory
from app.models.shared import PaginatedResponse
from app.services.entity import content_service, generation_service
from app.services.moderation.moderation_service import log_moderation_event

router = APIRouter(prefix="/collections", tags=["entity-content"])


@router.post(
    "/{collection_id}/entities/{entity_id}/generate/{category}",
    response_model=EntityContentResponse,
    status_code=201,
)
def generate_content(
    category: ContentCategory,
    request: GenerateContentRequest,
    entity: Entity = Depends(get_entity_or_404_owned),
    session: Session = Depends(get_session),
):
    """Genera contenido RAG para una entidad usando el pipeline LLM.

    Crea un EntityContent en estado 'pending' junto con su GeneratedText.
    Aplica guardrails de entrada y salida.
    """
    try:
        return generation_service.generate(session, entity, category, request.query)
    except PendingLimitExceededError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ContentNotAllowedError as e:
        log_moderation_event(session, "input", e.snippet)
        raise HTTPException(status_code=422, detail=str(e))
    except InvalidCategoryError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except NoContextAvailableError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except GeneratedContentBlockedError as e:
        log_moderation_event(session, "output", e.snippet)
        raise HTTPException(status_code=422, detail=str(e))
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Error interno del servidor.")
    except RuntimeError:
        raise HTTPException(
            status_code=503, detail="No fue posible generar el contenido solicitado."
        )


@router.get(
    "/{collection_id}/entities/{entity_id}/contents",
    response_model=PaginatedResponse[EntityContentResponse],
)
def list_contents(
    entity_id: str,
    collection_id: str,
    pagination: Annotated[PaginationParams, Depends()],
    category: Optional[ContentCategory] = Query(default=None),
    status: Literal["active", "pending", "confirmed", "discarded", "all"] = Query(
        default="active"
    ),
    _: Entity = Depends(get_entity_or_404_owned),
    session: Session = Depends(get_session),
):
    """Lista los contenidos de una entidad con filtros y paginación."""
    items, total = content_service.list_contents(
        session,
        entity_id,
        collection_id,
        category,
        status,
        pagination.page,
        pagination.page_size,
        pagination.order,
    )
    return PaginatedResponse.build(items, total, pagination.page, pagination.page_size)


@router.patch(
    "/{collection_id}/entities/{entity_id}/contents/{content_id}",
    response_model=EntityContentResponse,
)
def edit_content(
    entity_id: str,
    collection_id: str,
    content_id: str,
    request: UpdateContentRequest,
    _: Entity = Depends(get_entity_or_404_owned),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Edita el texto de un contenido activo (pending o confirmed)."""
    try:
        result = content_service.edit_content(
            session,
            content_id,
            entity_id,
            collection_id,
            request.content,
            current_user["sub"],
        )
    except ContentDiscardedError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Error interno del servidor.")
    if not result:
        raise HTTPException(status_code=404, detail="Contenido no encontrado.")
    return result


@router.post(
    "/{collection_id}/entities/{entity_id}/contents/{content_id}/confirm",
    response_model=EntityResponse,
)
def confirm_content(
    content_id: str,
    entity: Entity = Depends(get_entity_or_404_owned),
    session: Session = Depends(get_session),
):
    """Confirma un contenido pending y descarta sus hermanos de la misma categoría."""
    try:
        result = content_service.confirm_content(session, content_id, entity)
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Error interno del servidor.")
    if not result:
        raise HTTPException(status_code=404, detail="Contenido no encontrado.")
    session.refresh(entity)
    return entity


@router.patch(
    "/{collection_id}/entities/{entity_id}/contents/{content_id}/discard",
    response_model=EntityContentResponse,
)
def discard_content(
    entity_id: str,
    collection_id: str,
    content_id: str,
    _: Entity = Depends(get_entity_or_404_owned),
    session: Session = Depends(get_session),
):
    """Descarta un contenido pendiente."""
    try:
        result = content_service.discard_content(
            session, content_id, entity_id, collection_id
        )
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Error interno del servidor.")
    if not result:
        raise HTTPException(status_code=404, detail="Contenido no encontrado.")
    return result


@router.patch(
    "/{collection_id}/entities/{entity_id}/contents/{content_id}/share",
    response_model=EntityContentResponse,
)
def share_content(
    entity_id: str,
    collection_id: str,
    content_id: str,
    request: ShareContentRequest,
    _: Entity = Depends(get_entity_or_404_owned),
    session: Session = Depends(get_session),
):
    """Comparte o deja de compartir un contenido en el feed público.

    Solo contenidos en estado 'confirmed' pueden compartirse.
    """
    try:
        result = content_service.share_content(
            session, content_id, entity_id, collection_id, request.shared
        )
    except ContentNotShareableError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Error interno del servidor.")
    if not result:
        raise HTTPException(status_code=404, detail="Contenido no encontrado.")
    return result


@router.delete(
    "/{collection_id}/entities/{entity_id}/contents/{content_id}",
    status_code=204,
)
def delete_content(
    entity_id: str,
    collection_id: str,
    content_id: str,
    _: Entity = Depends(get_entity_or_404_owned),
    session: Session = Depends(get_session),
):
    """Elimina suavemente un contenido de entidad."""
    try:
        deleted = content_service.soft_delete_content(
            session, content_id, entity_id, collection_id
        )
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Error interno del servidor.")
    if not deleted:
        raise HTTPException(status_code=404, detail="Contenido no encontrado.")
    return Response(status_code=204)
