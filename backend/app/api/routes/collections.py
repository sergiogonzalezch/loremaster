from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlmodel import Session

from app.core.valid_collection import get_collection_or_404
from app.database import get_session
from app.models.collections import (
    Collection,
    CreateCollectionRequest,
    CollectionResponse,
)
from app.models.shared import PaginatedResponse
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


@router.get("/", response_model=PaginatedResponse[CollectionResponse])
async def get_collections(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    name: Optional[str] = Query(default=None),
    created_after: Optional[datetime] = Query(default=None),
    created_before: Optional[datetime] = Query(default=None),
    session: Session = Depends(get_session),
):
    items, total = list_collections_service(
        session, page, page_size,
        name=name, created_after=created_after, created_before=created_before,
    )
    return PaginatedResponse.build(items, total, page, page_size)


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
