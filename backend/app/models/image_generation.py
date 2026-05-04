# backend/app/models/image_generation.py

import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, ForeignKey, String
from sqlmodel import SQLModel, Field as SQLField

# ── Tabla DB: image_generations (un registro por batch) ───────────────────────────────


class ImageGeneration(SQLModel, table=True):
    """
    Registro de generación de imágenes en batch.
    Almacena los metadatos del prompt y configuración de la generación.
    """

    __tablename__ = "image_generations"

    id: str = SQLField(
        default_factory=lambda: str(uuid.uuid4()),
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

    # Prompt
    auto_prompt: str = SQLField(max_length=1000)
    final_prompt: str = SQLField(max_length=1000)
    prompt_token_count: int = SQLField(default=0)

    # Generación
    batch_size: int = SQLField(default=4)
    backend: str = SQLField(default="mock", max_length=20)  # mock | local | runpod
    width: int = SQLField(default=1024)
    height: int = SQLField(default=1024)

    # Ciclo de vida
    created_at: datetime = SQLField(default_factory=lambda: datetime.now(timezone.utc))
    is_deleted: bool = SQLField(default=False)
    deleted_at: Optional[datetime] = SQLField(default=None)


# ── Tabla DB: image_records (una por imagen dentro del batch) ─────────────────────────────


class ImageRecord(SQLModel, table=True):
    """
    Registro de imagen individual generada dentro de un batch.
    La imagen física se almacena en: media/{collection_id}/{entity_id}/{generation_id}/{id}.png
    """

    __tablename__ = "image_records"

    id: str = SQLField(
        default_factory=lambda: str(uuid.uuid4()),
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

    # Imagen
    seed: int = SQLField(default=42)
    storage_path: Optional[str] = SQLField(default=None, max_length=500)
    image_url: Optional[str] = SQLField(default=None, max_length=500)
    filename: Optional[str] = SQLField(default=None, max_length=255)
    extension: str = SQLField(default="png", max_length=10)
    width: int = SQLField(default=1024)
    height: int = SQLField(default=1024)
    generation_ms: int = SQLField(default=0)

    # Ciclo de vida
    created_at: datetime = SQLField(default_factory=lambda: datetime.now(timezone.utc))
    is_deleted: bool = SQLField(default=False)
    deleted_at: Optional[datetime] = SQLField(default=None)


# ── API Schemas: Request ───────────────────────────────────────────────────────────────


class BuildPromptRequest(BaseModel):
    content_id: str = Field(
        ...,
        description="ID del EntityContent confirmado que sirve como base narrativa.",
    )


class GenerateImagesRequest(BaseModel):
    content_id: str = Field(
        ...,
        description="ID del EntityContent confirmado.",
    )
    auto_prompt: str = Field(
        ...,
        description="Prompt generado por el LLM (del build).",
    )
    final_prompt: str = Field(
        ...,
        description="Prompt aprobada/editado por el usuario.",
    )
    batch_size: int = Field(
        default=4,
        ge=1,
        le=4,
        description="Cantidad de imágenes a generar (1-4).",
    )


class DeleteImageRequest(BaseModel):
    image_id: str = Field(
        ...,
        description="ID de la imagen a eliminar.",
    )


# ── API Schemas: Response ───────────────────────────────────────────────────────


class ImageResult(BaseModel):
    id: str
    image_url: Optional[str] = None
    seed: int
    width: int
    height: int
    generation_ms: int


class BuildPromptResponse(BaseModel):
    auto_prompt: str
    token_count: int


class GenerateImagesResponse(BaseModel):
    generation_id: str
    auto_prompt: str
    final_prompt: str
    batch_size: int
    backend: str
    images: list[ImageResult]


class ImageGenerationResponse(BaseModel):
    id: str
    entity_id: str
    collection_id: str
    content_id: Optional[str] = None
    category: str

    auto_prompt: str
    final_prompt: str
    prompt_token_count: int

    batch_size: int
    backend: str
    width: int
    height: int

    created_at: datetime
    is_deleted: bool
    deleted_at: Optional[datetime] = None


class ImageRecordResponse(BaseModel):
    id: str
    generation_id: str
    entity_id: str
    collection_id: str

    seed: int
    storage_path: Optional[str] = None
    image_url: Optional[str] = None
    filename: Optional[str] = None
    extension: str
    width: int
    height: int
    generation_ms: int

    created_at: datetime
    is_deleted: bool
    deleted_at: Optional[datetime] = None


class ImageGenerationListItem(BaseModel):
    id: str
    entity_id: str
    collection_id: str
    content_id: Optional[str] = None
    category: str
    auto_prompt: str
    final_prompt: str
    batch_size: int
    backend: str
    width: int
    height: int
    created_at: datetime
    is_deleted: bool

    images: list[ImageRecordResponse]


class ImageGenerationListResponse(BaseModel):
    """Lista de generaciones de imágenes de una entidad."""

    generations: list[ImageGenerationListItem]
    total: int
