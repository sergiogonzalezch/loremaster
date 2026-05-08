from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import exists, or_
from sqlmodel import Session, select

from app.core.auth_deps import get_current_user
from app.database import get_session
from app.models.users import User, UpdateProfileRequest, UserProfileResponse
from app.models.collections import Collection
from app.models.entity_content import EntityContent
from app.models.image_generation import ImageRecord

router = APIRouter(prefix="/users", tags=["users"])


class CollectionSummary(BaseModel):
    id: str
    name: str
    description: str


class PublicProfileResponse(BaseModel):
    username: str
    display_name: str | None
    bio: str | None
    avatar_url: str | None
    public_collections: list[CollectionSummary]


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
    if request.avatar_url is not None:
        user.avatar_url = request.avatar_url
    if request.email is not None:
        user.email = request.email

    session.add(user)
    session.commit()
    session.refresh(user)
    return user


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

    has_shared_content = exists().where(
        EntityContent.collection_id == Collection.id,
        EntityContent.is_shared == True,
        EntityContent.is_deleted == False,
    )
    has_shared_image = exists().where(
        ImageRecord.collection_id == Collection.id,
        ImageRecord.is_shared == True,
        ImageRecord.is_deleted == False,
    )
    collections = session.exec(
        select(Collection).where(
            Collection.owner_id == user.id,
            Collection.is_deleted == False,
            or_(has_shared_content, has_shared_image),
        )
    ).all()

    return PublicProfileResponse(
        username=user.username,
        display_name=user.display_name,
        bio=user.bio,
        avatar_url=user.avatar_url,
        public_collections=[
            CollectionSummary(id=c.id, name=c.name, description=c.description)
            for c in collections
        ],
    )
