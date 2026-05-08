from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlmodel import Session

from app.core.deps import get_current_db_user
from app.models.users import (
    AvatarResponse,
    PublicProfileResponse,
    UpdateProfileRequest,
    User,
    UserProfileResponse,
)
from app.services.public_service import get_user_public_profile
from app.services.user_image import (
    delete_profile_image,
    get_avatar_info,
    upload_profile_image,
)
from app.database import get_session

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfileResponse)
def get_my_profile(user: User = Depends(get_current_db_user)):
    return user


@router.patch("/me", response_model=UserProfileResponse)
def update_my_profile(
    request: UpdateProfileRequest,
    user: User = Depends(get_current_db_user),
    session: Session = Depends(get_session),
):
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
    return get_avatar_info(user)


@router.post("/me/avatar", response_model=AvatarResponse)
async def upload_my_avatar(
    user: User = Depends(get_current_db_user),
    session: Session = Depends(get_session),
    file: UploadFile = File(...),
):
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
    delete_profile_image(session, user)
    return Response(status_code=204)


@router.get("/{username}/profile", response_model=PublicProfileResponse)
def get_public_profile(
    username: str,
    session: Session = Depends(get_session),
):
    return get_user_public_profile(session, username)