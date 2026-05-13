"""Rutas de perfil de usuario y gestión de avatares."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlmodel import Session

from app.core.database.dependencies import get_current_db_user
from app.database import get_session
from app.models.db.user import User
from app.models.schemas.public import PublicProfileResponse
from app.models.schemas.user import (
    AvatarResponse,
    UpdateProfileRequest,
    UserProfileResponse,
)
from app.services.profile.profile_service import (
    delete_profile_image,
    get_avatar_info,
    get_public_profile,
    update_profile,
    upload_profile_image,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfileResponse)
def get_my_profile(user: Annotated[User, Depends(get_current_db_user)]):
    """Obtiene el perfil del usuario autenticado."""
    return user


@router.patch("/me", response_model=UserProfileResponse)
def update_my_profile(
    request: UpdateProfileRequest,
    user: Annotated[User, Depends(get_current_db_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Actualiza el perfil del usuario autenticado (display_name, bio, email)."""
    return update_profile(session, user, request)


@router.get("/me/avatar", response_model=AvatarResponse)
def get_my_avatar(user: Annotated[User, Depends(get_current_db_user)]):
    """Obtiene la información del avatar del usuario autenticado."""
    return get_avatar_info(user)


@router.post("/me/avatar", response_model=AvatarResponse)
async def upload_my_avatar(
    user: Annotated[User, Depends(get_current_db_user)],
    session: Annotated[Session, Depends(get_session)],
    file: Annotated[UploadFile, File(...)],
):
    """Sube o reemplaza la imagen de perfil del usuario autenticado."""
    try:
        avatar_url = await upload_profile_image(session, user, file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return AvatarResponse(avatar_url=avatar_url, has_avatar=True)


@router.delete("/me/avatar", status_code=204)
def delete_my_avatar(
    user: Annotated[User, Depends(get_current_db_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Elimina la imagen de perfil del usuario autenticado."""
    delete_profile_image(session, user)
    return Response(status_code=204)


@router.get("/{username}/profile", response_model=PublicProfileResponse)
def get_user_public_profile(
    username: str,
    session: Annotated[Session, Depends(get_session)],
):
    """Obtiene el perfil público de un usuario con sus contenidos e imágenes compartidos."""
    return get_public_profile(session, username)
