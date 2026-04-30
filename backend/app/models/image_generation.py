# backend/app/models/image_generation.py

import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, ForeignKey, String
from sqlmodel import SQLModel, Field as SQLField

# ── Tabla DB ──────────────────────────────────────────────────────────────────


class ImageRecord(SQLModel, table=True):
    """
    Registro de imagen generada.
    La imagen física se almacena en: media/{collection_id}/{entity_id}/{id}.png
    Este modelo solo guarda los metadatos y la ruta relativa.
    """

    __tablename__ = "generated_images"

    id: str = SQLField(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        max_length=36,
    )
    entity_id: str = SQLField(
        sa_column=Column(
            String(36), ForeignKey("entities.id"), nullable=False, index=True
        )
    )
    collection_id: str = SQLField(
        sa_column=Column(
            String(36), ForeignKey("collections.id"), nullable=False, index=True
        )
    )
    content_id: Optional[str] = SQLField(
        sa_column=Column(
            String(36), ForeignKey("entity_contents.id"), nullable=True, index=True
        )
    )
    category: str = SQLField(max_length=50)

    # Prompt
    visual_prompt: str = SQLField(max_length=1000)
    prompt_token_count: int = SQLField(default=0)
    prompt_source: str = SQLField(
        max_length=50
    )  # content_direct | content_sentences | entity_only | description | name_only
    prompt_strategy: str = SQLField(
        max_length=50
    )  # direct | first_sentences | entity_only
    truncated: bool = SQLField(default=False)

    # Imagen
    # Ruta relativa desde MEDIA_ROOT: {collection_id}/{entity_id}/{id}.png
    # Ejemplo: "abc-123/def-456/img-uuid.png"
    image_path: Optional[str] = SQLField(default=None, max_length=500)
    # image_url: Optional[str] = SQLField(default=None, max_length=500)
    image_url: Optional[str] = None
    filename: Optional[str] = SQLField(default=None, max_length=255)
    extension: str = SQLField(default="png", max_length=10)
    width: int = SQLField(default=1024)
    height: int = SQLField(default=1024)

    # Generación
    backend: str = SQLField(default="mock", max_length=20)  # mock | local | runpod
    seed: int = SQLField(default=42)
    generation_ms: int = SQLField(default=0)

    # Ciclo de vida (igual que EntityContent)
    status: str = SQLField(
        default="pending", max_length=20
    )  # pending | confirmed | discarded
    created_at: datetime = SQLField(default_factory=lambda: datetime.now(timezone.utc))
    confirmed_at: Optional[datetime] = SQLField(default=None)
    updated_at: Optional[datetime] = SQLField(default=None)
    is_deleted: bool = SQLField(default=False)
    deleted_at: Optional[datetime] = SQLField(default=None)


# ── API Schemas ───────────────────────────────────────────────────────────────


class GenerateImageRequest(BaseModel):
    content_id: str = Field(
        ...,
        description="ID del EntityContent confirmado que sirve como base narrativa.",
    )


class GenerateImageResponse(BaseModel):
    id: str
    entity_id: str
    collection_id: str
    content_id: Optional[str]
    category: str

    # Prompt
    visual_prompt: str
    prompt_token_count: int
    prompt_source: str
    prompt_strategy: str
    truncated: bool

    # Imagen
    image_url: Optional[str] = None
    image_path: Optional[str]
    filename: Optional[str]
    extension: str
    width: int
    height: int

    # Generación
    backend: str
    seed: int
    generation_ms: int

    # Estado
    status: str
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
