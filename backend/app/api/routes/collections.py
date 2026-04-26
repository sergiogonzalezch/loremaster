import logging
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session

logger = logging.getLogger(__name__)

from app.core.deps import get_collection_or_404
from app.core.exceptions import DatabaseError, DuplicateCollectionNameError
from app.database import get_session
from app.models.collections import (
    Collection,
    CreateCollectionRequest,
    UpdateCollectionRequest,
    CollectionResponse,
)
from app.models.shared import PaginatedResponse
from app.services.collection_service import (
    create_collection_service,
    list_collections_service,
    update_collection_service,
    delete_collection_service,
    _fetch_counts,
)

router = APIRouter(prefix="/collections", tags=["collections"])


@router.post("/", response_model=CollectionResponse, status_code=201)
def create_collection(
    request: CreateCollectionRequest,
    session: Session = Depends(get_session),
):
    try:
        return create_collection_service(session, request.name, request.description)
    except DuplicateCollectionNameError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/", response_model=PaginatedResponse[CollectionResponse])
def get_collections(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    name: Optional[str] = Query(default=None),
    created_after: Optional[datetime] = Query(default=None),
    created_before: Optional[datetime] = Query(default=None),
    order: Literal["asc", "desc"] = Query(default="desc"),
    session: Session = Depends(get_session),
):
    items, total = list_collections_service(
        session,
        page,
        page_size,
        name=name,
        created_after=created_after,
        created_before=created_before,
        order=order,
    )
    return PaginatedResponse.build(items, total, page, page_size)


@router.get("/{collection_id}", response_model=CollectionResponse)
def get_collection(
    collection: Collection = Depends(get_collection_or_404),
    session: Session = Depends(get_session),
):
    doc_counts, entity_counts = _fetch_counts(session, [collection.id])
    return {
        **collection.model_dump(),
        "document_count": doc_counts.get(collection.id, 0),
        "entity_count": entity_counts.get(collection.id, 0),
    }


@router.patch("/{collection_id}", response_model=CollectionResponse)
def update_collection(
    request: UpdateCollectionRequest,
    collection: Collection = Depends(get_collection_or_404),
    session: Session = Depends(get_session),
):
    try:
        return update_collection_service(session, collection, request)
    except DuplicateCollectionNameError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/{collection_id}", status_code=204)
def delete_collection(
    collection: Collection = Depends(get_collection_or_404),
    session: Session = Depends(get_session),
):
    try:
        vectors_cleaned = delete_collection_service(session, collection)
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Error interno del servidor.")
    if not vectors_cleaned:
        logger.warning(
            "Collection %s soft-deleted but Qdrant vectors were NOT removed — manual cleanup needed.",
            collection.id,
        )
    return Response(status_code=204)
