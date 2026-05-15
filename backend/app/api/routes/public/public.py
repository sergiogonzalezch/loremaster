"""Rutas públicas para feed de contenidos e imágenes compartidas."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.api.params import PaginationParams
from app.database import get_session
from app.models.schemas.public import PublicFeedItem, PublicImageItem
from app.models.shared import PaginatedResponse
from app.services.public import get_public_feed, get_public_images

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/feed", response_model=PaginatedResponse[PublicFeedItem])
def feed(
    pagination: Annotated[PaginationParams, Depends()],
    session: Annotated[Session, Depends(get_session)],
):
    """Obtiene el feed público de contenidos compartidos. No requiere autenticación."""
    items, total = get_public_feed(session, pagination.page, pagination.page_size)
    return PaginatedResponse.build(items, total, pagination.page, pagination.page_size)


@router.get("/images", response_model=PaginatedResponse[PublicImageItem])
def images(
    pagination: Annotated[PaginationParams, Depends()],
    session: Annotated[Session, Depends(get_session)],
):
    """Obtiene el feed público de imágenes compartidas. No requiere autenticación."""
    items, total = get_public_images(session, pagination.page, pagination.page_size)
    return PaginatedResponse.build(items, total, pagination.page, pagination.page_size)
