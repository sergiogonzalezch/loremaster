from fastapi import APIRouter, Depends, Response
from sqlmodel import Session

from app.core.valid_collection import get_collection_or_404
from app.database import get_session
from app.models.collections import (
    Collection,
    CreateCollectionRequest,
    CollectionResponse,
    CollectionListResponse,
)
from app.services.collection_service import (
    create_collection_service,
    list_collections_service,
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
    collection: Collection = Depends(get_collection_or_404),
):
    return collection


@router.delete("/{collection_id}", status_code=204)
async def delete_collection(
    collection: Collection = Depends(get_collection_or_404),
    session: Session = Depends(get_session),
):
    delete_collection_service(session, collection)
    return Response(status_code=204)