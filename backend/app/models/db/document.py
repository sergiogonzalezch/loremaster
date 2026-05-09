from datetime import datetime, timezone
from typing import Optional
from enum import Enum

from sqlalchemy import Column, ForeignKey, String, Text
from sqlmodel import SQLModel, Field

from app.core.database.soft_delete import SoftDeleteMixin


class DocumentStatus(str, Enum):
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Document(SQLModel, SoftDeleteMixin, table=True):
    __tablename__ = "documents"

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
    filename: str = Field(max_length=255)
    file_type: str = Field(max_length=100)
    chunk_count: int = Field(default=0)
    status: DocumentStatus = Field(default=DocumentStatus.processing, max_length=50)
    processing_error: Optional[str] = Field(
        sa_column=Column(Text, nullable=True), default=None
    )
    raw_text: Optional[str] = Field(sa_column=Column(Text, nullable=True), default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
