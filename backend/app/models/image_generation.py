# app/models/image_generation.py

from pydantic import BaseModel, Field
from typing import Optional


class GenerateImageRequest(BaseModel):
    content_id: Optional[str] = Field(
        default=None,
        description=(
            "ID de EntityContent confirmado a usar como base narrativa. "
            "Si no se proporciona, se usa la descripción de la entidad."
        ),
    )


class GenerateImageResponse(BaseModel):
    image_url: str
    visual_prompt: str
    token_count: int
    truncated: bool
    prompt_source: str          # "content" | "description" | "name_only"
    seed: int
    backend: str                # "mock" | "local" | "runpod"
    generation_ms: int
    entity_id: str
    collection_id: str
    content_id: Optional[str] = None