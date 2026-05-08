from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.query_params import PaginationParams
from app.database import get_session
from app.models.shared import PaginatedResponse
from app.models.users import PublicFeedItem, PublicImageItem
from app.services.public_service import get_public_feed_page, get_public_images_page

public_router = APIRouter(prefix="/public", tags=["public"])


@public_router.get("/feed", response_model=PaginatedResponse[PublicFeedItem])
def get_public_feed(
    pagination: Annotated[PaginationParams, Depends()],
    session: Session = Depends(get_session),
):
    items, total = get_public_feed_page(session, pagination.page, pagination.page_size)
    return PaginatedResponse.build(items, total, pagination.page, pagination.page_size)


@public_router.get("/images", response_model=PaginatedResponse[PublicImageItem])
def get_public_images(
    pagination: Annotated[PaginationParams, Depends()],
    session: Session = Depends(get_session),
):
    items, total = get_public_images_page(session, pagination.page, pagination.page_size)
    return PaginatedResponse.build(items, total, pagination.page, pagination.page_size)