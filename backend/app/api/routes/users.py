from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import Session, select

from app.core.auth_deps import get_current_user
from app.core.query_params import PaginationParams
from app.database import get_session
from app.models.collections import Collection
from app.models.entities import Entity
from app.models.entity_content import EntityContent
from app.models.enums import ContentStatus
from app.models.image_generation import ImageGeneration, ImageRecord
from app.models.shared import PaginatedResponse
from app.models.users import User, UpdateProfileRequest, UserProfileResponse
from app.services.user_image import (
    delete_profile_image,
    get_avatar_info,
    upload_profile_image,
)

router = APIRouter(prefix="/users", tags=["users"])


class AvatarResponse(BaseModel):
    avatar_url: str | None
    has_avatar: bool


class SharedContentSummary(BaseModel):
    id: str
    content: str
    category: str
    entity_name: str
    entity_type: str
    confirmed_at: datetime | None
    created_at: datetime


class SharedImageSummary(BaseModel):
    id: str
    generation_id: str
    image_url: str | None
    storage_path: str | None
    seed: int
    auto_prompt: str
    final_prompt: str
    entity_name: str
    entity_type: str
    created_at: datetime


class PublicProfileResponse(BaseModel):
    username: str
    display_name: str | None
    bio: str | None
    avatar_url: str | None
    shared_contents: list[SharedContentSummary]
    shared_images: list[SharedImageSummary]


class PublicFeedItem(BaseModel):
    content_id: str
    content: str
    content_preview: str
    category: str
    entity_name: str
    entity_type: str
    owner_username: str
    owner_display_name: str | None
    confirmed_at: datetime | None
    created_at: datetime


class PublicImageItem(BaseModel):
    image_id: str
    generation_id: str
    image_url: str | None
    storage_path: str | None
    seed: int
    auto_prompt: str
    final_prompt: str
    entity_name: str
    entity_type: str
    owner_username: str
    owner_display_name: str | None
    created_at: datetime


public_router = APIRouter(prefix="/public", tags=["public"])

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


@public_router.get("/feed", response_model=PaginatedResponse[PublicFeedItem])
def get_public_feed(
    pagination: Annotated[PaginationParams, Depends()],
    session: Session = Depends(get_session),
):
    base = (
        select(EntityContent)
        .join(Entity, EntityContent.entity_id == Entity.id)
        .join(Collection, EntityContent.collection_id == Collection.id)
        .join(User, Collection.owner_id == User.id)
        .where(*_CONTENT_CONDITIONS)
    )
    total = session.exec(select(func.count()).select_from(base.subquery())).one()
    skip = (pagination.page - 1) * pagination.page_size
    rows = session.exec(
        select(EntityContent, Entity, User)
        .join(Entity, EntityContent.entity_id == Entity.id)
        .join(Collection, EntityContent.collection_id == Collection.id)
        .join(User, Collection.owner_id == User.id)
        .where(*_CONTENT_CONDITIONS)
        .order_by(EntityContent.confirmed_at.desc(), EntityContent.id.asc())
        .offset(skip)
        .limit(pagination.page_size)
    ).all()
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
    base = (
        select(ImageRecord)
        .join(ImageGeneration, ImageRecord.generation_id == ImageGeneration.id)
        .join(Entity, ImageRecord.entity_id == Entity.id)
        .join(Collection, ImageRecord.collection_id == Collection.id)
        .join(User, Collection.owner_id == User.id)
        .where(*_IMAGE_CONDITIONS)
    )
    total = session.exec(select(func.count()).select_from(base.subquery())).one()
    skip = (pagination.page - 1) * pagination.page_size
    rows = session.exec(
        select(ImageRecord, ImageGeneration, Entity, User)
        .join(ImageGeneration, ImageRecord.generation_id == ImageGeneration.id)
        .join(Entity, ImageRecord.entity_id == Entity.id)
        .join(Collection, ImageRecord.collection_id == Collection.id)
        .join(User, Collection.owner_id == User.id)
        .where(*_IMAGE_CONDITIONS)
        .order_by(ImageRecord.created_at.desc(), ImageRecord.id.asc())
        .offset(skip)
        .limit(pagination.page_size)
    ).all()
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
    return PaginatedResponse.build(items, total, pagination.page, pagination.page_size)


@router.get("/me", response_model=UserProfileResponse)
def get_my_profile(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    user = session.get(User, current_user["sub"])
    if not user or user.is_deleted:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return user


@router.patch("/me", response_model=UserProfileResponse)
def update_my_profile(
    request: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    user = session.get(User, current_user["sub"])
    if not user or user.is_deleted:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    if request.display_name is not None:
        user.display_name = request.display_name
    if request.bio is not None:
        user.bio = request.bio
    if request.email is not None:
        user.email = request.email

    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.get("/me/avatar", response_model=AvatarResponse)
def get_my_avatar(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    user = session.get(User, current_user["sub"])
    if not user or user.is_deleted:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return get_avatar_info(user)


@router.post("/me/avatar", response_model=AvatarResponse)
async def upload_my_avatar(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
    file: UploadFile = File(...),
):
    user = session.get(User, current_user["sub"])
    if not user or user.is_deleted:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    try:
        avatar_url = await upload_profile_image(session, user, file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return AvatarResponse(avatar_url=avatar_url, has_avatar=True)


@router.delete("/me/avatar", status_code=204)
def delete_my_avatar(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    user = session.get(User, current_user["sub"])
    if not user or user.is_deleted:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    delete_profile_image(session, user)
    return Response(status_code=204)


@router.get("/{username}/profile", response_model=PublicProfileResponse)
def get_public_profile(
    username: str,
    session: Session = Depends(get_session),
):
    user = session.exec(
        select(User).where(User.username == username, User.is_deleted == False)
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    content_rows = session.exec(
        select(EntityContent, Entity)
        .join(Entity, EntityContent.entity_id == Entity.id)
        .join(Collection, EntityContent.collection_id == Collection.id)
        .where(
            Collection.owner_id == user.id,
            EntityContent.is_shared == True,
            EntityContent.is_deleted == False,
            EntityContent.status == ContentStatus.confirmed,
            Entity.is_deleted == False,
            Collection.is_deleted == False,
        )
        .order_by(EntityContent.confirmed_at.desc())
    ).all()

    image_rows = session.exec(
        select(ImageRecord, ImageGeneration, Entity)
        .join(ImageGeneration, ImageRecord.generation_id == ImageGeneration.id)
        .join(Entity, ImageRecord.entity_id == Entity.id)
        .join(Collection, ImageRecord.collection_id == Collection.id)
        .where(
            Collection.owner_id == user.id,
            ImageRecord.is_shared == True,
            ImageRecord.is_deleted == False,
            ImageGeneration.is_deleted == False,
            Entity.is_deleted == False,
            Collection.is_deleted == False,
        )
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
