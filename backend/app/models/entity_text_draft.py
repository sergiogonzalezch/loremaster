from enum import Enum
from typing import Optional
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, ForeignKey, String
from sqlmodel import SQLModel, Field
import uuid


class DraftStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    discarded = "discarded"


class EntityTextDraft(SQLModel, table=True):
    __tablename__ = "entity_text_drafts"

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
    query: str = Field(max_length=1000)
    content: str = Field(max_length=10000)
    sources_count: int = Field(default=0)
    status: DraftStatus = Field(default=DraftStatus.pending)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confirmed_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = Field(default=None)


# ── API schemas ───────────────────────────────────────────────────────────────


class GenerateEntityTextDraftRequest(BaseModel):
    query: str = Field(..., min_length=5)


class UpdateEntityTextDraftContentRequest(BaseModel):
    content: str = Field(..., min_length=1)


class EntityTextDraftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    entity_id: str
    collection_id: str
    query: str
    content: str
    sources_count: int
    status: DraftStatus
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
