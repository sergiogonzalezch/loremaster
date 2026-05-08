from datetime import datetime, timezone
from typing import Optional
from pydantic import Field
from sqlmodel import SQLModel, Field as SQLField
import uuid

from app.models.user_schemas import (
    UserResponse,
    UserProfileResponse,
    UserAdminResponse,
    UpdateProfileRequest,
    AvatarResponse,
)
from app.models.public import (
    SharedContentSummary,
    SharedImageSummary,
    PublicProfileResponse,
    PublicFeedItem,
    PublicImageItem,
)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = SQLField(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=36
    )
    username: str = SQLField(index=True, unique=True, max_length=255)
    hashed_password: str = SQLField(max_length=255)
    email: Optional[str] = SQLField(default=None, max_length=255, unique=True)
    display_name: Optional[str] = SQLField(default=None, max_length=100)
    bio: Optional[str] = SQLField(default=None, max_length=500)
    avatar_path: Optional[str] = SQLField(default=None, max_length=500)
    is_admin: bool = SQLField(default=False)
    token_version: int = SQLField(default=0)
    created_at: datetime = SQLField(default_factory=lambda: datetime.now(timezone.utc))
    is_deleted: bool = SQLField(default=False)
    deleted_at: Optional[datetime] = SQLField(default=None)


__all__ = [
    "User",
    "UserResponse",
    "UserProfileResponse",
    "UserAdminResponse",
    "UpdateProfileRequest",
    "AvatarResponse",
    "SharedContentSummary",
    "SharedImageSummary",
    "PublicProfileResponse",
    "PublicFeedItem",
    "PublicImageItem",
]
