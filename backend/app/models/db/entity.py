from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, ForeignKey, String, UniqueConstraint
from sqlmodel import SQLModel, Field

from app.core.database.soft_delete import SoftDeleteMixin


class EntityType(str, Enum):
    character = "character"
    creature = "creature"
    faction = "faction"
    location = "location"
    item = "item"


class Entity(SQLModel, SoftDeleteMixin, table=True):
    __tablename__ = "entities"
    __table_args__ = (
        UniqueConstraint("collection_id", "name", name="uq_entity_collection_name"),
    )

    id: str = Field(
        default_factory=lambda: str(__import__("uuid").uuid4()),
        primary_key=True,
        max_length=36,
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
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime | None = Field(default=None)
