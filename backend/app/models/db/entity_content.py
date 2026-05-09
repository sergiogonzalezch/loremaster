from datetime import datetime, timezone

from sqlalchemy import Column, ForeignKey, String
from sqlmodel import SQLModel, Field

from app.core.database.soft_delete import SoftDeleteMixin
from app.models.enums import ContentCategory, ContentStatus


class EntityContent(SQLModel, SoftDeleteMixin, table=True):
    __tablename__ = "entity_contents"

    id: str = Field(
        default_factory=lambda: str(__import__("uuid").uuid4()),
        primary_key=True,
        max_length=36,
    )
    entity_id: str = Field(
        sa_column=Column(
            String(36),
            ForeignKey("entities.id"),
            nullable=False,
            index=True,
        )
    )
    collection_id: str = Field(
        sa_column=Column(
            String(36),
            ForeignKey("collections.id"),
            nullable=False,
            index=True,
        )
    )
    generated_text_id: str = Field(
        sa_column=Column(
            String(36),
            ForeignKey("generated_texts.id"),
            nullable=False,
            index=True,
        )
    )
    category: ContentCategory = Field(max_length=50)
    content: str = Field(max_length=10000)
    status: ContentStatus = Field(default=ContentStatus.pending, max_length=50)
    is_shared: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    confirmed_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)
