"""Modelo de base de datos para registro de eventos de moderación."""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class ModerationLog(SQLModel, table=True):
    """Registro de eventos de moderación de contenido.

    Almacena de forma inmutable los textos que fueron evaluados por los
    guardrails de contenido (input o output). No se usa soft-delete.

    Attributes:
        id: Identificador autoincremental.
        layer: Capa donde ocurrió la evaluación (input, output, document).
        snippet: Fragmento del texto evaluado (truncado a 200 chars).
        user_id: Clerk sub del usuario autenticado (si disponible).
        collection_id: ID de la colección (si disponible).
        entity_id: ID de la entidad (si disponible).
        operation: Operación que disparó el evento (generate, edit, share, upload, query).
        pattern_matched: Expresión regular que coincidió (truncada a 200 chars).
        created_at: Fecha y hora del evento (UTC).

    """

    __tablename__ = "moderation_log"

    id: int = Field(default=None, primary_key=True)
    layer: str
    snippet: str = Field(max_length=200)
    user_id: str | None = Field(default=None, max_length=128)
    collection_id: str | None = Field(default=None, max_length=36)
    entity_id: str | None = Field(default=None, max_length=36)
    operation: str | None = Field(default=None, max_length=32)
    pattern_matched: str | None = Field(default=None, max_length=200)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
