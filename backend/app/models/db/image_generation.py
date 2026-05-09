from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, ForeignKey, String
from sqlmodel import SQLModel, Field as SQLField

from app.core.soft_delete import SoftDeleteMixin


class ImageGeneration(SQLModel, SoftDeleteMixin, table=True):
    __tablename__ = "image_generations"

    id: str = SQLField(
        default_factory=lambda: str(__import__("uuid").uuid4()),
        primary_key=True,
        max_length=36,
    )
    entity_id: str = SQLField(
        sa_column=Column(
            String(36),
            ForeignKey("entities.id"),
            nullable=False,
            index=True,
        )
    )
    collection_id: str = SQLField(
        sa_column=Column(
            String(36),
            ForeignKey("collections.id"),
            nullable=False,
            index=True,
        )
    )
    content_id: Optional[str] = SQLField(
        sa_column=Column(
            String(36),
            ForeignKey("entity_contents.id"),
            nullable=True,
            index=True,
        )
    )
    category: str = SQLField(max_length=50)

    auto_prompt: str = SQLField(max_length=1000)
    final_prompt: str = SQLField(max_length=1000)
    prompt_token_count: int = SQLField(default=0)

    batch_size: int = SQLField(default=4)
    backend: str = SQLField(default="mock", max_length=20)
    width: int = SQLField(default=1024)
    height: int = SQLField(default=1024)

    created_at: datetime = SQLField(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ImageRecord(SQLModel, SoftDeleteMixin, table=True):
    __tablename__ = "image_records"

    id: str = SQLField(
        default_factory=lambda: str(__import__("uuid").uuid4()),
        primary_key=True,
        max_length=36,
    )
    generation_id: str = SQLField(
        sa_column=Column(
            String(36),
            ForeignKey("image_generations.id"),
            nullable=False,
            index=True,
        )
    )
    entity_id: str = SQLField(
        sa_column=Column(
            String(36),
            ForeignKey("entities.id"),
            nullable=False,
            index=True,
        )
    )
    collection_id: str = SQLField(
        sa_column=Column(
            String(36),
            ForeignKey("collections.id"),
            nullable=False,
            index=True,
        )
    )

    seed: int = SQLField(default=42)
    storage_path: Optional[str] = SQLField(default=None, max_length=500)
    image_url: Optional[str] = SQLField(default=None, max_length=500)
    filename: Optional[str] = SQLField(default=None, max_length=255)
    extension: str = SQLField(default="png", max_length=10)
    width: int = SQLField(default=1024)
    height: int = SQLField(default=1024)
    generation_ms: int = SQLField(default=0)

    is_shared: bool = SQLField(default=False)
    created_at: datetime = SQLField(
        default_factory=lambda: datetime.now(timezone.utc)
    )
