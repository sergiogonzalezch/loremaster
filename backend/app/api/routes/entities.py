from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlmodel import Session

from app.core.deps import get_collection_or_404, get_entity_or_404
from app.database import get_session
from app.models.collections import Collection
from app.models.entities import (
    CreateEntityRequest,
    UpdateEntityRequest,
    Entity,
    EntityType,
    EntityResponse,
)
from app.models.shared import PaginatedResponse
from app.services.entities_service import (
    create_entity_service,
    delete_entity_service,
    list_entities_service,
    update_entity_service,
)

router = APIRouter(prefix="/collections", tags=["entities"])


@router.post(
    "/{collection_id}/entities", response_model=EntityResponse, status_code=201
)
def create_entity(
    collection_id: str,
    request: CreateEntityRequest,
    _: Collection = Depends(get_collection_or_404),
    session: Session = Depends(get_session),
):
    return create_entity_service(session, request, collection_id)


@router.get(
    "/{collection_id}/entities", response_model=PaginatedResponse[EntityResponse]
)
def list_entities(
    collection_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    name: Optional[str] = Query(default=None),
    type: Optional[EntityType] = Query(default=None),
    created_after: Optional[datetime] = Query(default=None),
    created_before: Optional[datetime] = Query(default=None),
    order: Literal["asc", "desc"] = Query(default="desc"),
    _: Collection = Depends(get_collection_or_404),
    session: Session = Depends(get_session),
):
    entities, total = list_entities_service(
        session,
        collection_id,
        page,
        page_size,
        name=name,
        entity_type=type,
        created_after=created_after,
        created_before=created_before,
        order=order,
    )
    return PaginatedResponse.build(entities, total, page, page_size)


@router.get("/{collection_id}/entities/{entity_id}", response_model=EntityResponse)
def get_entity(
    entity: Entity = Depends(get_entity_or_404),
):
    return entity


@router.patch("/{collection_id}/entities/{entity_id}", response_model=EntityResponse)
def update_entity(
    request: UpdateEntityRequest,
    entity: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    return update_entity_service(session, entity, request)


@router.delete("/{collection_id}/entities/{entity_id}", status_code=204)
def delete_entity(
    entity: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    delete_entity_service(session, entity)
    return Response(status_code=204)
