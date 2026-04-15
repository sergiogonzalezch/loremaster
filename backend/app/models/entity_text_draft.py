# backend/app/models/entity_draft.py

from typing import List, Optional
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict
from sqlmodel import SQLModel, Field
import uuid


class EntityTextDraft(SQLModel, table=True):
    __tablename__ = "entity_text_drafts"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=36
    )
    entity_id: str = Field(index=True, max_length=36)
    collection_id: str = Field(index=True, max_length=36)
    query: str = Field(max_length=1000)
    content: str = Field(max_length=10000)
    sources_count: int = Field(default=0)
    is_confirmed: bool = Field(default=False)
    is_discarded: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    confirmed_at: Optional[datetime] = Field(default=None)


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
    is_confirmed: bool
    is_discarded: bool
    created_at: datetime
    confirmed_at: Optional[datetime] = None


class EntityTextDraftListResponse(BaseModel):
    data: List[EntityTextDraftResponse]
    count: int