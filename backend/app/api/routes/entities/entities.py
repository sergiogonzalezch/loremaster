"""Rutas de entidades para CRUD y listado dentro de colecciones."""

import contextlib
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session, select

from app.core.api.params import DateRangeParams, PaginationParams
from app.core.auth.dependencies import get_current_user
from app.core.database.dependencies import (
    get_collection_or_404_owned,
    get_entity_or_404_owned,
)
from app.core.exceptions import DatabaseError, DuplicateEntityNameError
from app.database import get_session
from app.models.db.collection import Collection
from app.models.db.entity import Entity, EntityType
from app.models.schemas.collection import BulkDeleteRequest
from app.models.schemas.entity import (
    CreateEntityRequest,
    EntityResponse,
    UpdateEntityRequest,
)
from app.models.shared import PaginatedResponse
from app.services.entity.entities_service import (
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
    _: Collection = Depends(get_collection_or_404_owned),
    session: Session = Depends(get_session),
):
    """Crea una nueva entidad (character, creature, faction, location o item)."""
    try:
        return create_entity_service(session, request, collection_id)
    except DuplicateEntityNameError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get(
    "/{collection_id}/entities", response_model=PaginatedResponse[EntityResponse]
)
def list_entities(
    collection_id: str,
    pagination: Annotated[PaginationParams, Depends()],
    dates: Annotated[DateRangeParams, Depends()],
    name: str | None = Query(default=None),
    type: EntityType | None = Query(default=None),  # noqa: A002
    _: Collection = Depends(get_collection_or_404_owned),
    session: Session = Depends(get_session),
):
    """Lista las entidades de una colección con filtros y paginación."""
    entities, total = list_entities_service(
        session,
        collection_id,
        pagination.page,
        pagination.page_size,
        name=name,
        entity_type=type,
        created_after=dates.created_after,
        created_before=dates.created_before,
        order=pagination.order,
    )
    return PaginatedResponse.build(
        entities, total, pagination.page, pagination.page_size
    )


@router.get("/{collection_id}/entities/{entity_id}", response_model=EntityResponse)
def get_entity(
    entity: Entity = Depends(get_entity_or_404_owned),
):
    """Obtiene los datos de una entidad específica."""
    return entity


@router.patch("/{collection_id}/entities/{entity_id}", response_model=EntityResponse)
def update_entity(
    request: UpdateEntityRequest,
    entity: Entity = Depends(get_entity_or_404_owned),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Actualiza los campos de una entidad existente."""
    try:
        return update_entity_service(session, entity, request, current_user["sub"])
    except DuplicateEntityNameError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/{collection_id}/entities/{entity_id}", status_code=204)
def delete_entity(
    entity: Entity = Depends(get_entity_or_404_owned),
    session: Session = Depends(get_session),
):
    """Elimina una entidad y todos sus contenidos en cascada."""
    try:
        delete_entity_service(session, entity)
    except DatabaseError as e:
        raise HTTPException(
            status_code=500, detail="Error interno del servidor."
        ) from e
    return Response(status_code=204)


@router.post("/{collection_id}/entities/bulk-delete", status_code=204)
def bulk_delete_entities(
    collection_id: str,
    request: BulkDeleteRequest,
    _: Collection = Depends(get_collection_or_404_owned),
    session: Session = Depends(get_session),
):
    """Elimina múltiples entidades en cascada."""
    entities = session.exec(
        select(Entity).where(
            Entity.id.in_(request.ids),
            Entity.collection_id == collection_id,
            Entity.is_deleted.is_(False),
        )
    ).all()

    for entity in entities:
        with contextlib.suppress(Exception):
            delete_entity_service(session, entity)

    return Response(status_code=204)
