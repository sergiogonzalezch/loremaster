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
