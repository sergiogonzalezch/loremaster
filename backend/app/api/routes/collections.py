from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from app.database import engine
from app.models.collections import (
    Collection,
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

# from app.services.documents_db_mock import collections  # replaced by SQLite

router = APIRouter(prefix="/collections", tags=["collections"])


@router.post("/", response_model=CollectionResponse, status_code=201)
async def create_collection(request: CreateCollectionRequest):
    with Session(engine) as session:
        existing = session.exec(
            select(Collection).where(
                Collection.name == request.name, Collection.is_deleted == False
            )
        ).first()
        if existing:
            raise HTTPException(
                status_code=409, detail="Collection name already exists"
            )
    return create_collection_service(request.name, request.description)


@router.get("/", response_model=CollectionListResponse)
async def get_collections():
    items = list_collections_service()
    return CollectionListResponse(data=items, count=len(items))


@router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection(collection_id: str):
    collection = get_collection_service(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.delete("/{collection_id}")
async def delete_collection(collection_id: str):
    result = delete_collection_service(collection_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"message": f"Collection {collection_id} deleted successfully"}
