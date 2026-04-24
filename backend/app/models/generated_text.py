from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, ForeignKey, String
from sqlmodel import SQLModel, Field
import uuid

from app.models.enums import ContentCategory


class GeneratedText(SQLModel, table=True):
    __tablename__ = "generated_texts"

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
    category: ContentCategory = Field(max_length=50)
    query: str = Field(max_length=1000)
    raw_content: str = Field(max_length=10000)
    sources_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── API schemas ───────────────────────────────────────────────────────────────


class GeneratedTextResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    entity_id: str
    collection_id: str
    category: ContentCategory
    query: str
    raw_content: str
    sources_count: int
    created_at: datetime
