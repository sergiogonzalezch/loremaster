from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import SQLModel, Field as SQLField
import uuid


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


class SharedContentSummary(BaseModel):
    id: str
    content: str
    category: str
    entity_name: str
    entity_type: str
    confirmed_at: Optional[datetime] = None
    created_at: datetime


class SharedImageSummary(BaseModel):
    id: str
    generation_id: str
    image_url: Optional[str] = None
    storage_path: Optional[str] = None
    seed: int
    auto_prompt: str
    final_prompt: str
    entity_name: str
    entity_type: str
    created_at: datetime


class PublicProfileResponse(BaseModel):
    username: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    shared_contents: list[SharedContentSummary] = []
    shared_images: list[SharedImageSummary] = []


class PublicFeedItem(BaseModel):
    content_id: str
    content: str
    content_preview: str
    category: str
    entity_name: str
    entity_type: str
    owner_username: str
    owner_display_name: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    created_at: datetime


class PublicImageItem(BaseModel):
    image_id: str
    generation_id: str
    image_url: Optional[str] = None
    storage_path: Optional[str] = None
    seed: int
    auto_prompt: str
    final_prompt: str
    entity_name: str
    entity_type: str
    owner_username: str
    owner_display_name: Optional[str] = None
    created_at: datetime
