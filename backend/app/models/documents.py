from typing import List, Optional
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict
from sqlmodel import SQLModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    import uuid
    return str(uuid.uuid4())


# ── Tabla DB ──────────────────────────────────────────────────────────────────

class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: str = Field(default_factory=_new_id, primary_key=True, max_length=36)
    collection_id: str = Field(index=True, max_length=36)
    filename: str = Field(max_length=255)
    file_type: str = Field(max_length=100)
    chunk_count: int = Field(default=0)
    status: str = Field(default="completed", max_length=50)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = Field(default=None)


# ── API schemas ───────────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    collection_id: str
    filename: str
    file_type: str
    chunk_count: int
    status: str
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    data: List[DocumentResponse]
    count: int
