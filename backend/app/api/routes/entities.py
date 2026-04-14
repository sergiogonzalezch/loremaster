from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_valid_collection
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
):
    entity = create_entity_service(request, collection_id)
    return entity


@router.get("/{collection_id}/entities", response_model=EntityListResponse)
async def list_entities(
    collection_id: str,
    collection: Collection = Depends(get_valid_collection),
):
    entities = list_entities_service(collection_id)
    return EntityListResponse(data=entities, count=len(entities))


@router.get("/{collection_id}/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(
    collection_id: str,
    entity_id: str,
    collection: Collection = Depends(get_valid_collection),
):
    entity = get_entity_service(entity_id, collection_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.put("/{collection_id}/entities/{entity_id}", response_model=EntityResponse)
async def update_entity(
    collection_id: str,
    entity_id: str,
    request: UpdateEntityRequest,
    collection: Collection = Depends(get_valid_collection),
):
    entity = update_entity_service(entity_id, collection_id, request)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.delete("/{collection_id}/entities/{entity_id}")
async def delete_entity(
    collection_id: str,
    entity_id: str,
    collection: Collection = Depends(get_valid_collection),
):
    success = delete_entity_service(entity_id, collection_id)
    if not success:
        raise HTTPException(status_code=404, detail="Entity not found")
    return {"message": "Deleted successfully"}
