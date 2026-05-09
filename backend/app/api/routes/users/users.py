from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlmodel import Session, select

from app.core.database.dependencies import get_current_db_user
from app.core.api.filters import _CONTENT_CONDITIONS, _IMAGE_CONDITIONS
from app.models.schemas.user_schemas import (
    AvatarResponse,
    UpdateProfileRequest,
    UserProfileResponse,
)
from app.models.schemas.public import (
    PublicProfileResponse,
    SharedContentSummary,
    SharedImageSummary,
)
from app.models.db.user import User
from app.services.profile.profile_service import (
    delete_profile_image,
    get_avatar_info,
    upload_profile_image,
)
from app.database import get_session
from app.models.db.collection import Collection
from app.models.db.entity import Entity
from app.models.db.entity_content import EntityContent
from app.models.db.image_generation import ImageGeneration, ImageRecord

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfileResponse)
def get_my_profile(user: User = Depends(get_current_db_user)):
    """Obtiene el perfil del usuario autenticado."""
    return user


@router.patch("/me", response_model=UserProfileResponse)
def update_my_profile(
    request: UpdateProfileRequest,
    user: User = Depends(get_current_db_user),
    session: Session = Depends(get_session),
):
    """Actualiza el perfil del usuario autenticado (display_name, bio, email)."""
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
def get_my_avatar(user: User = Depends(get_current_db_user)):
    """Obtiene la información del avatar del usuario autenticado."""
    return get_avatar_info(user)


@router.post("/me/avatar", response_model=AvatarResponse)
async def upload_my_avatar(
    user: User = Depends(get_current_db_user),
    session: Session = Depends(get_session),
    file: UploadFile = File(...),
):
    """Sube o reemplaza la imagen de perfil del usuario autenticado."""
    try:
        avatar_url = await upload_profile_image(session, user, file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return AvatarResponse(avatar_url=avatar_url, has_avatar=True)


@router.delete("/me/avatar", status_code=204)
def delete_my_avatar(
    user: User = Depends(get_current_db_user),
    session: Session = Depends(get_session),
):
    """Elimina la imagen de perfil del usuario autenticado."""
    delete_profile_image(session, user)
    return Response(status_code=204)


@router.get("/{username}/profile", response_model=PublicProfileResponse)
def get_public_profile(
    username: str,
    session: Session = Depends(get_session),
):
    """Obtiene el perfil público de un usuario con sus contenidos e imágenes compartidos."""
    user = session.exec(
        select(User).where(User.username == username, User.is_deleted == False)
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    content_conditions = _CONTENT_CONDITIONS + (Collection.owner_id == user.id,)
    image_conditions = _IMAGE_CONDITIONS + (Collection.owner_id == user.id,)

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
