from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    created_at: datetime


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime


class UserAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    is_admin: bool
    is_deleted: bool
    created_at: datetime


class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=100)
    bio: Optional[str] = Field(default=None, max_length=500)
    email: Optional[str] = Field(default=None, max_length=255)


class AvatarResponse(BaseModel):
    avatar_url: str | None
    has_avatar: bool
