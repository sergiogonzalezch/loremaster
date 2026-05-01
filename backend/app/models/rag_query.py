from typing import Optional

from pydantic import BaseModel, Field


class RagQueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Pregunta o consulta para generar texto.",
    )
    extra_context: str = Field(
        default="",
        max_length=5000,
        description="Contexto adicional para enriquecer la respuesta.",
    )
    top_k: Optional[int] = Field(
        default=None,
        ge=1,
        le=50,
        description="Número máximo de fragmentos de contexto a recuperar.",
    )
    score_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Umbral mínimo de similitud para incluir un fragmento.",
    )


class RagQueryResponse(BaseModel):
    answer: str = Field(..., description="Texto generado en respuesta a la consulta.")
    query: str = Field(..., description="Consulta original enviada por el usuario.")
    sources_count: int = Field(
        ..., description="Número de fragmentos de contexto usados."
    )
