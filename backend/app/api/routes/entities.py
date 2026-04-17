from fastapi import APIRouter, Depends, Response
from sqlmodel import Session

from app.core.valid_collection import get_collection_or_404, get_entity_or_404
from app.database import get_session
from app.models.collections import Collection
from app.models.entities import (
    CreateEntityRequest,
    UpdateEntityRequest,
    Entity,
    EntityResponse,
    EntityListResponse,
)
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
async def create_entity(
    collection_id: str,
    request: CreateEntityRequest,
    _: Collection = Depends(get_collection_or_404),
    session: Session = Depends(get_session),
):
    return create_entity_service(session, request, collection_id)


@router.get("/{collection_id}/entities", response_model=EntityListResponse)
async def list_entities(
    collection_id: str,
    _: Collection = Depends(get_collection_or_404),
    session: Session = Depends(get_session),
):
    entities = list_entities_service(session, collection_id)
    return EntityListResponse(data=entities, count=len(entities))


@router.get("/{collection_id}/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(
    entity: Entity = Depends(get_entity_or_404),
):
    return entity


@router.put("/{collection_id}/entities/{entity_id}", response_model=EntityResponse)
async def update_entity(
    request: UpdateEntityRequest,
    entity: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    return update_entity_service(session, entity, request)


@router.delete("/{collection_id}/entities/{entity_id}", status_code=204)
async def delete_entity(
    entity: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    delete_entity_service(session, entity)
    return Response(status_code=204)
