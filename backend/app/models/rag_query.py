from pydantic import BaseModel, Field


class RagQueryRequest(BaseModel):
    query: str = Field(
        ..., min_length=5, description="Pregunta o consulta para generar texto."
    )


class RagQueryResponse(BaseModel):
    answer: str = Field(..., description="Texto generado en respuesta a la consulta.")
    query: str = Field(..., description="Consulta original enviada por el usuario.")
    sources_count: int = Field(
        ..., description="Número de fragmentos de contexto usados."
    )
