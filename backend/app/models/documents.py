from enum import Enum
from typing import List, Optional
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, ForeignKey, String
from sqlmodel import SQLModel, Field
import uuid


class DocumentStatus(str, Enum):
    processing = "processing"
    completed = "completed"
    failed = "failed"


# ── Tabla DB ──────────────────────────────────────────────────────────────────


class Document(SQLModel, table=True):
    __tablename__ = "documents"

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
    filename: str = Field(max_length=255)
    file_type: str = Field(max_length=100)
    chunk_count: int = Field(default=0)
    status: DocumentStatus = Field(default=DocumentStatus.processing, max_length=50)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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
    status: DocumentStatus
    created_at: datetime


class DocumentListResponse(BaseModel):
    data: List[DocumentResponse]
    count: int
