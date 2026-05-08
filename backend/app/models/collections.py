from typing import Optional
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import (
    SQLModel,
    Field as SQLField,
    Column,
    String,
    ForeignKey,
    UniqueConstraint,
)
import uuid

# ── Tabla DB ──────────────────────────────────────────────────────────────────


class Collection(SQLModel, table=True):
    __tablename__ = "collections"
    __table_args__ = (
        UniqueConstraint("name", "owner_id", name="uq_collection_name_owner"),
    )

    id: str = SQLField(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=36
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
    is_deleted: bool = SQLField(default=False)
    deleted_at: Optional[datetime] = SQLField(default=None)


# ── API schemas ───────────────────────────────────────────────────────────────


class CreateCollectionRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)


class UpdateCollectionRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)


class CollectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    owner_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    document_count: int = 0
    entity_count: int = 0
