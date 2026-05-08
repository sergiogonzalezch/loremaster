from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


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
    seed_base: Optional[int] = Field(
        default=None,
        description="Semilla base. None usa el valor de configuración.",
    )


class DeleteImageRequest(BaseModel):
    image_id: str = Field(
        ...,
        description="ID de la imagen a eliminar.",
    )


class ShareImageRequest(BaseModel):
    shared: bool


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

    is_shared: bool = False
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
    generations: list[ImageGenerationListItem]
