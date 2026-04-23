from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session
from typing import Optional

from app.core.deps import get_entity_or_404
from app.database import get_session
from app.models.entities import Entity, EntityResponse
from app.models.entity_content import (
    EntityContentListResponse,
    EntityContentResponse,
    GenerateContentRequest,
    UpdateContentRequest,
)
from app.models.enums import ContentCategory
from app.services import content_management_service, generation_service

router = APIRouter(prefix="/collections", tags=["entity-content"])


@router.post(
    "/{collection_id}/entities/{entity_id}/generate/{category}",
    response_model=EntityContentResponse,
    status_code=201,
)
async def generate_content(
    category: ContentCategory,
    request: GenerateContentRequest,
    entity: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    try:
        return generation_service.generate(session, entity, category, request.query)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get(
    "/{collection_id}/entities/{entity_id}/contents",
    response_model=EntityContentListResponse,
)
async def list_contents(
    entity_id: str,
    collection_id: str,
    category: Optional[ContentCategory] = Query(default=None),
    _: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    items = content_management_service.list_contents(
        session, entity_id, collection_id, category
    )
    return EntityContentListResponse(items=items, total=len(items))


@router.patch(
    "/{collection_id}/entities/{entity_id}/contents/{content_id}",
    response_model=EntityContentResponse,
)
async def edit_content(
    entity_id: str,
    collection_id: str,
    content_id: str,
    request: UpdateContentRequest,
    _: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    result = content_management_service.edit_content(
        session, content_id, entity_id, collection_id, request.content
    )
    if not result:
        raise HTTPException(status_code=404, detail="Content not found")
    return result


@router.post(
    "/{collection_id}/entities/{entity_id}/contents/{content_id}/confirm",
    response_model=EntityResponse,
)
async def confirm_content(
    content_id: str,
    entity: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    result = content_management_service.confirm_content(session, content_id, entity)
    if not result:
        raise HTTPException(status_code=404, detail="Content not found")
    session.refresh(entity)
    return entity


@router.patch(
    "/{collection_id}/entities/{entity_id}/contents/{content_id}/discard",
    response_model=EntityContentResponse,
)
async def discard_content(
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
        raise HTTPException(status_code=404, detail="Content not found")
    return result


@router.delete(
    "/{collection_id}/entities/{entity_id}/contents/{content_id}",
    status_code=204,
)
async def delete_content(
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
        raise HTTPException(status_code=404, detail="Content not found")
    return Response(status_code=204)