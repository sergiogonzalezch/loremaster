"""Modelo de base de datos para textos generados por el pipeline LLM."""

from datetime import UTC, datetime

from sqlalchemy import Column, ForeignKey, String
from sqlmodel import Field, SQLModel


class GeneratedText(SQLModel, table=True):
    """Registro de una llamada al pipeline LLM de generación.

    Almacena la consulta original, la respuesta cruda del LLM y metadatos
    de la generación (número de fuentes, tokens estimados). Es inmutable
    tras su creación.

    Attributes:
        id: Identificador único UUID.
        entity_id: Entidad para la que se generó el contenido.
        collection_id: Colección de la entidad.
        category: Categoría del contenido generado.
        query: Consulta/prompt original enviado por el usuario.
        raw_content: Respuesta cruda del LLM (sin edición).
        sources_count: Número de fragmentos de contexto utilizados.
        token_count: Estimación del número de tokens de la respuesta.
        created_at: Fecha y hora de generación (UTC).

    """

    __tablename__ = "generated_texts"

    id: str = Field(
        default_factory=lambda: str(__import__("uuid").uuid4()),
        primary_key=True,
        max_length=36,
    )
    entity_id: str = Field(
        sa_column=Column(
            String(36),
            ForeignKey("entities.id"),
            nullable=False,
            index=True,
        ),
    )
    collection_id: str = Field(
        sa_column=Column(
            String(36),
            ForeignKey("collections.id"),
            nullable=False,
            index=True,
        ),
    )
    category: str = Field(max_length=50)
    query: str = Field(max_length=2000)
    raw_content: str = Field(max_length=10000)
    sources_count: int = Field(default=0)
    token_count: int = Field(default=0)
    model_used: str | None = Field(default=None, max_length=100)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
