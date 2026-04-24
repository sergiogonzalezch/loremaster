from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session

from app.core.deps import get_entity_or_404
from app.database import get_session
from app.models.entities import Entity, EntityResponse
from app.models.entity_content import (
    EntityContentResponse,
    GenerateContentRequest,
    UpdateContentRequest,
)
from app.models.enums import ContentCategory
from app.models.shared import PaginatedResponse
from app.services import content_management_service, generation_service
from app.services.generation_service import PendingLimitExceededError

router = APIRouter(prefix="/collections", tags=["entity-content"])


@router.post(
    "/{collection_id}/entities/{entity_id}/generate/{category}",
    response_model=EntityContentResponse,
    status_code=201,
)
def generate_content(
    category: ContentCategory,
    request: GenerateContentRequest,
    entity: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    try:
        return generation_service.generate(session, entity, category, request.query)
    except PendingLimitExceededError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        if str(e) == "Contenido no permitido.":
            raise HTTPException(status_code=422, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
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
    category: Optional[ContentCategory] = Query(default=None),
    status: Literal["active", "pending", "confirmed", "discarded", "all"] = Query(
        default="active"
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    order: Literal["asc", "desc"] = Query(default="desc"),
    _: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    items, total = content_management_service.list_contents(
        session,
        entity_id,
        collection_id,
        category,
        status,
        page,
        page_size,
        order,
    )
    return PaginatedResponse.build(items, total, page, page_size)


@router.patch(
    "/{collection_id}/entities/{entity_id}/contents/{content_id}",
    response_model=EntityContentResponse,
)
def edit_content(
    entity_id: str,
    collection_id: str,
    content_id: str,
    request: UpdateContentRequest,
    _: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    try:
        result = content_management_service.edit_content(
            session, content_id, entity_id, collection_id, request.content
        )
    except ValueError:
        raise HTTPException(
            status_code=409, detail="No se puede editar un contenido descartado."
        )
    if not result:
        raise HTTPException(status_code=404, detail="Contenido no encontrado.")
    return result


@router.post(
    "/{collection_id}/entities/{entity_id}/contents/{content_id}/confirm",
    response_model=EntityResponse,
)
def confirm_content(
    content_id: str,
    entity: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    result = content_management_service.confirm_content(session, content_id, entity)
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
    _: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    result = content_management_service.discard_content(
        session, content_id, entity_id, collection_id
    )
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
    _: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    deleted = content_management_service.soft_delete_content(
        session, content_id, entity_id, collection_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Contenido no encontrado.")
    return Response(status_code=204)
