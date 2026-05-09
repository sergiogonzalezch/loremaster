from pydantic import BaseModel, Field


class RagQueryRequest(BaseModel):
    """Esquema para realizar una consulta RAG.

    Attributes:
        query: Pregunta o consulta del usuario sobre el mundo fictional.
    """

    query: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Pregunta o consulta para generar texto.",
    )


class RagQueryResponse(BaseModel):
    """Respuesta a una consulta RAG.

    Attributes:
        answer: Texto generado por el LLM con contexto de los documentos.
        query: Consulta original enviada por el usuario.
        sources_count: Número de fragmentos de contexto utilizados.
    """

    answer: str = Field(..., description="Texto generado en respuesta a la consulta.")
    query: str = Field(..., description="Consulta original enviada por el usuario.")
    sources_count: int = Field(
        ..., description="Número de fragmentos de contexto usados."
    )
