from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api.dependencies import get_valid_collection
from app.database import get_session
from app.models.collections import Collection
from app.models.entities import (
    CreateEntityRequest,
    UpdateEntityRequest,
    EntityResponse,
    EntityListResponse,
)
from app.services.entities_service import (
    create_entity_service,
    get_entity_service,
    delete_entity_service,
    list_entities_service,
    update_entity_service,
)

router = APIRouter(prefix="/collections", tags=["entities"])


@router.post("/{collection_id}/entities", response_model=EntityResponse)
async def create_entity(
    collection_id: str,
    request: CreateEntityRequest,
    collection: Collection = Depends(get_valid_collection),
    session: Session = Depends(get_session),
):
    return create_entity_service(session, request, collection_id)


@router.get("/{collection_id}/entities", response_model=EntityListResponse)
async def list_entities(
    collection_id: str,
    collection: Collection = Depends(get_valid_collection),
    session: Session = Depends(get_session),
):
    entities = list_entities_service(session, collection_id)
    return EntityListResponse(data=entities, count=len(entities))


@router.get("/{collection_id}/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(
    collection_id: str,
    entity_id: str,
    collection: Collection = Depends(get_valid_collection),
    session: Session = Depends(get_session),
):
    entity = get_entity_service(session, entity_id, collection_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.put("/{collection_id}/entities/{entity_id}", response_model=EntityResponse)
async def update_entity(
    collection_id: str,
    entity_id: str,
    request: UpdateEntityRequest,
    collection: Collection = Depends(get_valid_collection),
    session: Session = Depends(get_session),
):
    entity = update_entity_service(session, entity_id, collection_id, request)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.delete("/{collection_id}/entities/{entity_id}")
async def delete_entity(
    collection_id: str,
    entity_id: str,
    collection: Collection = Depends(get_valid_collection),
    session: Session = Depends(get_session),
):
    success = delete_entity_service(session, entity_id, collection_id)
    if not success:
        raise HTTPException(status_code=404, detail="Entity not found")
    return {"message": "Deleted successfully"}