from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, ForeignKey, String, UniqueConstraint
from sqlmodel import SQLModel, Field as SQLField

from app.core.database.soft_delete import SoftDeleteMixin


class Collection(SQLModel, SoftDeleteMixin, table=True):
    __tablename__ = "collections"
    __table_args__ = (
        UniqueConstraint("name", "owner_id", name="uq_collection_name_owner"),
    )

    id: str = SQLField(
        default_factory=lambda: str(__import__("uuid").uuid4()),
        primary_key=True,
        max_length=36,
    )
    name: str = SQLField(index=True, max_length=255)
    description: str = SQLField(default="", max_length=2000)
    owner_id: Optional[str] = SQLField(
        sa_column=Column(
            String(36),
            ForeignKey("users.id"),
            nullable=True,
            index=True,
        )
    )
    created_at: datetime = SQLField(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = SQLField(default=None)
