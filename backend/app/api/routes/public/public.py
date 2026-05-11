from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.core.api.params import PaginationParams
from app.core.database.utils import paginate
from app.core.api.filters import _CONTENT_CONDITIONS, _IMAGE_CONDITIONS
from app.database import get_session
from app.models.shared import PaginatedResponse
from app.models.schemas.public import PublicFeedItem, PublicImageItem
from app.models.db.user import User
from app.models.db.collection import Collection
from app.models.db.entity import Entity
from app.models.db.entity_content import EntityContent
from app.models.db.image_generation import ImageGeneration, ImageRecord

public_router = APIRouter(prefix="/public", tags=["public"])


@public_router.get("/feed", response_model=PaginatedResponse[PublicFeedItem])
def get_public_feed(
    pagination: Annotated[PaginationParams, Depends()],
    session: Session = Depends(get_session),
):
    """Obtiene el feed público de contenidos compartidos por todos los usuarios.

    No requiere autenticación. Incluye solo contenidos confirmados.
    """
    base = (
        select(EntityContent, Entity, User)
        .join(Entity, EntityContent.entity_id == Entity.id)
        .join(Collection, EntityContent.collection_id == Collection.id)
        .join(User, Collection.owner_id == User.id)
        .where(*_CONTENT_CONDITIONS)
        .order_by(EntityContent.confirmed_at.desc(), EntityContent.id.asc())
    )
    rows, total = paginate(session, base, pagination.page, pagination.page_size)
    items = [
        PublicFeedItem(
            content_id=ec.id,
            content=ec.content,
            content_preview=ec.content[:300],
            category=ec.category,
            entity_name=en.name,
            entity_type=en.type,
            owner_username=u.username,
            owner_display_name=u.display_name,
            confirmed_at=ec.confirmed_at,
            created_at=ec.created_at,
        )
        for ec, en, u in rows
    ]
    return PaginatedResponse.build(items, total, pagination.page, pagination.page_size)


@public_router.get("/images", response_model=PaginatedResponse[PublicImageItem])
def get_public_images(
    pagination: Annotated[PaginationParams, Depends()],
    session: Session = Depends(get_session),
):
    """Obtiene el feed público de imágenes compartidas por todos los usuarios.

    No requiere autenticación.
    """
    base = (
        select(ImageRecord, ImageGeneration, Entity, User)
        .join(ImageGeneration, ImageRecord.generation_id == ImageGeneration.id)
        .join(Entity, ImageRecord.entity_id == Entity.id)
        .join(Collection, ImageRecord.collection_id == Collection.id)
        .join(User, Collection.owner_id == User.id)
        .where(*_IMAGE_CONDITIONS)
        .order_by(ImageRecord.created_at.desc(), ImageRecord.id.asc())
    )
    rows, total = paginate(session, base, pagination.page, pagination.page_size)
    items = [
        PublicImageItem(
            image_id=img.id,
            generation_id=img.generation_id,
            image_url=img.image_url,
            seed=img.seed,
            auto_prompt=gen.auto_prompt,
            final_prompt=gen.final_prompt,
            entity_name=en.name,
            entity_type=en.type,
            owner_username=u.username,
            owner_display_name=u.display_name,
            created_at=img.created_at,
        )
        for img, gen, en, u in rows
    ]
    return PaginatedResponse.build(items, total, pagination.page, pagination.page_size)
