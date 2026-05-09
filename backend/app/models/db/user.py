from datetime import datetime, timezone
from typing import Optional

from sqlmodel import SQLModel, Field as SQLField

from app.core.database.soft_delete import SoftDeleteMixin


class User(SQLModel, SoftDeleteMixin, table=True):
    __tablename__ = "users"

    id: str = SQLField(
        default_factory=lambda: str(__import__("uuid").uuid4()),
        primary_key=True,
        max_length=36,
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
