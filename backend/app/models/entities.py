from enum import Enum
from typing import Optional
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, ForeignKey, String, UniqueConstraint
from sqlmodel import SQLModel, Field
import uuid


class EntityType(str, Enum):
    character = "character"
    creature = "creature"
    faction = "faction"
    location = "location"
    item = "item"


# ── Tabla DB ──────────────────────────────────────────────────────────────────


class Entity(SQLModel, table=True):
    __tablename__ = "entities"
    __table_args__ = (
        UniqueConstraint("collection_id", "name", name="uq_entity_collection_name"),
    )

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=36
    )
    collection_id: str = Field(
        sa_column=Column(
            String(36),
            ForeignKey("collections.id"),
            nullable=False,
            index=True,
        )
    )
    type: EntityType = Field(index=True, max_length=50)
    name: str = Field(max_length=200)
    description: str = Field(default="", max_length=2000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default=None)
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = Field(default=None)


# ── API schemas (Pydantic — no generan tablas) ────────────────────────────────


class EntityRequest(BaseModel):
    type: EntityType
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)


CreateEntityRequest = EntityRequest


class UpdateEntityRequest(BaseModel):
    type: EntityType | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class EntityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    collection_id: str
    type: EntityType
    name: str
    description: str
    created_at: datetime
    updated_at: Optional[datetime]
