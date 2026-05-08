from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.core.common import paginate
from app.models.collections import Collection
from app.models.entities import Entity
from app.models.entity_content import EntityContent
from app.models.enums import ContentStatus
from app.models.image_generation import ImageGeneration, ImageRecord
from app.models.users import (
    PublicFeedItem,
    PublicImageItem,
    PublicProfileResponse,
    SharedContentSummary,
    SharedImageSummary,
    User,
)
from app.services.user_image import get_avatar_info

_CONTENT_CONDITIONS = [
    EntityContent.is_shared == True,
    EntityContent.is_deleted == False,
    EntityContent.status == ContentStatus.confirmed,
    Entity.is_deleted == False,
    Collection.is_deleted == False,
    User.is_deleted == False,
]

_IMAGE_CONDITIONS = [
    ImageRecord.is_shared == True,
    ImageRecord.is_deleted == False,
    ImageGeneration.is_deleted == False,
    Entity.is_deleted == False,
    Collection.is_deleted == False,
    User.is_deleted == False,
]


def get_public_feed_page(
    session: Session, page: int, page_size: int
) -> tuple[list[PublicFeedItem], int]:
    base = (
        select(EntityContent, Entity, User)
        .join(Entity, EntityContent.entity_id == Entity.id)
        .join(Collection, EntityContent.collection_id == Collection.id)
        .join(User, Collection.owner_id == User.id)
        .where(*_CONTENT_CONDITIONS)
        .order_by(EntityContent.confirmed_at.desc(), EntityContent.id.asc())
    )
    rows, total = paginate(session, base, page, page_size)
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
    return items, total


def get_public_images_page(
    session: Session, page: int, page_size: int
) -> tuple[list[PublicImageItem], int]:
    base = (
        select(ImageRecord, ImageGeneration, Entity, User)
        .join(ImageGeneration, ImageRecord.generation_id == ImageGeneration.id)
        .join(Entity, ImageRecord.entity_id == Entity.id)
        .join(Collection, ImageRecord.collection_id == Collection.id)
        .join(User, Collection.owner_id == User.id)
        .where(*_IMAGE_CONDITIONS)
        .order_by(ImageRecord.created_at.desc(), ImageRecord.id.asc())
    )
    rows, total = paginate(session, base, page, page_size)
    items = [
        PublicImageItem(
            image_id=img.id,
            generation_id=img.generation_id,
            image_url=img.image_url,
            storage_path=img.storage_path,
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
    return items, total


def get_user_public_profile(session: Session, username: str) -> PublicProfileResponse:
    user = session.exec(
        select(User).where(User.username == username, User.is_deleted == False)
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    content_conditions = _CONTENT_CONDITIONS + [Collection.owner_id == user.id]
    image_conditions = _IMAGE_CONDITIONS + [Collection.owner_id == user.id]

    content_rows = session.exec(
        select(EntityContent, Entity)
        .join(Entity, EntityContent.entity_id == Entity.id)
        .join(Collection, EntityContent.collection_id == Collection.id)
        .join(User, Collection.owner_id == User.id)
        .where(*content_conditions)
        .order_by(EntityContent.confirmed_at.desc())
    ).all()

    image_rows = session.exec(
        select(ImageRecord, ImageGeneration, Entity)
        .join(ImageGeneration, ImageRecord.generation_id == ImageGeneration.id)
        .join(Entity, ImageRecord.entity_id == Entity.id)
        .join(Collection, ImageRecord.collection_id == Collection.id)
        .join(User, Collection.owner_id == User.id)
        .where(*image_conditions)
        .order_by(ImageRecord.created_at.desc())
    ).all()

    return PublicProfileResponse(
        username=user.username,
        display_name=user.display_name,
        bio=user.bio,
        avatar_url=get_avatar_info(user)["avatar_url"],
        shared_contents=[
            SharedContentSummary(
                id=ec.id,
                content=ec.content,
                category=ec.category,
                entity_name=en.name,
                entity_type=en.type,
                confirmed_at=ec.confirmed_at,
                created_at=ec.created_at,
            )
            for ec, en in content_rows
        ],
        shared_images=[
            SharedImageSummary(
                id=img.id,
                generation_id=img.generation_id,
                image_url=img.image_url,
                storage_path=img.storage_path,
                seed=img.seed,
                auto_prompt=gen.auto_prompt,
                final_prompt=gen.final_prompt,
                entity_name=en.name,
                entity_type=en.type,
                created_at=img.created_at,
            )
            for img, gen, en in image_rows
        ],
    )