import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session

logger = logging.getLogger(__name__)

from app.core.api.params import DateRangeParams, PaginationParams
from app.core.database.dependencies import (
    get_collection_or_404_owned,
)
from app.core.auth.dependencies import get_current_user
from app.core.exceptions import DatabaseError, DuplicateCollectionNameError
from app.database import get_session
from app.models.db.collection import Collection
from app.models.schemas.collection import (
    CreateCollectionRequest,
    UpdateCollectionRequest,
    CollectionResponse,
)
from app.models.shared import PaginatedResponse
from app.services.collection.collection_service import (
    create_collection_service,
    get_collection_with_counts_service,
    list_collections_service,
    update_collection_service,
    delete_collection_service,
)

router = APIRouter(prefix="/collections", tags=["collections"])


@router.post("/", response_model=CollectionResponse, status_code=201)
def create_collection(
    request: CreateCollectionRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Crea una nueva colección para el usuario autenticado.

    Returns:
        Colección creada con status 201.
    """
    try:
        return create_collection_service(
            session, current_user["sub"], request.name, request.description
        )
    except DuplicateCollectionNameError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/", response_model=PaginatedResponse[CollectionResponse])
def get_collections(
    pagination: Annotated[PaginationParams, Depends()],
    dates: Annotated[DateRangeParams, Depends()],
    name: Optional[str] = Query(default=None),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Lista las colecciones del usuario autenticado con filtros y paginación."""
    items, total = list_collections_service(
        session,
        current_user["sub"],
        pagination.page,
        pagination.page_size,
        name=name,
        created_after=dates.created_after,
        created_before=dates.created_before,
        order=pagination.order,
    )
    return PaginatedResponse.build(items, total, pagination.page, pagination.page_size)


@router.get("/{collection_id}", response_model=CollectionResponse)
def get_collection(
    collection: Collection = Depends(get_collection_or_404_owned),
    session: Session = Depends(get_session),
):
    """Obtiene los datos de una colección con recuentos de documentos y entidades."""
    return get_collection_with_counts_service(session, collection)


@router.patch("/{collection_id}", response_model=CollectionResponse)
def update_collection(
    request: UpdateCollectionRequest,
    collection: Collection = Depends(get_collection_or_404_owned),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Actualiza el nombre o descripción de una colección."""
    try:
        return update_collection_service(session, collection, request, current_user["sub"])
    except DuplicateCollectionNameError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/{collection_id}", status_code=204)
def delete_collection(
    collection: Collection = Depends(get_collection_or_404_owned),
    session: Session = Depends(get_session),
):
    """Elimina una colección y todos sus contenidos en cascada."""
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
