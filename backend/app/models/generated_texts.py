import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, ForeignKey, String
from sqlmodel import SQLModel, Field


class GeneratedText(SQLModel, table=True):
    __tablename__ = "generated_texts"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=36
    )
    entity_id: str = Field(
        sa_column=Column(String(36), ForeignKey("entities.id"), nullable=False, index=True)
    )
    collection_id: str = Field(
        sa_column=Column(String(36), ForeignKey("collections.id"), nullable=False, index=True)
    )
    category: str = Field(max_length=50)
    query: str = Field(max_length=2000)
    raw_content: str = Field(max_length=10000)
    sources_count: int = Field(default=0)
    token_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))