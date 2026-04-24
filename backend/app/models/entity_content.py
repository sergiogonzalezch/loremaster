from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, ForeignKey, String
from sqlmodel import SQLModel, Field
import uuid

from app.models.enums import ContentCategory, ContentStatus


class EntityContent(SQLModel, table=True):
    __tablename__ = "entity_contents"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=36
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
        )
    )
    category: ContentCategory = Field(max_length=50)
    content: str = Field(max_length=10000)
    status: ContentStatus = Field(default=ContentStatus.pending, max_length=50)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confirmed_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = Field(default=None)


# ── API schemas ───────────────────────────────────────────────────────────────


class EntityContentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    entity_id: str
    collection_id: str
    generated_text_id: str
    category: ContentCategory
    content: str
    status: ContentStatus
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class GenerateContentRequest(BaseModel):
    query: str = Field(..., min_length=5)


class UpdateContentRequest(BaseModel):
    content: str = Field(..., min_length=1)
