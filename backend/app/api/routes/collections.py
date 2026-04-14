from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.database import get_session
from app.models.collections import (
    CreateCollectionRequest,
    CollectionResponse,
    CollectionListResponse,
)
from app.services.collection_service import (
    create_collection_service,
    list_collections_service,
    get_collection_service,
    delete_collection_service,
)

router = APIRouter(prefix="/collections", tags=["collections"])


@router.post("/", response_model=CollectionResponse, status_code=201)
async def create_collection(
    request: CreateCollectionRequest,
    session: Session = Depends(get_session),
):
    return create_collection_service(session, request.name, request.description)


@router.get("/", response_model=CollectionListResponse)
async def get_collections(session: Session = Depends(get_session)):
    items = list_collections_service(session)
    return CollectionListResponse(data=items, count=len(items))


@router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection(
    collection_id: str,
    session: Session = Depends(get_session),
):
    collection = get_collection_service(session, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.delete("/{collection_id}")
async def delete_collection(
    collection_id: str,
    session: Session = Depends(get_session),
):
    result = delete_collection_service(session, collection_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"message": f"Collection {collection_id} deleted successfully"}