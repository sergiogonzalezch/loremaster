from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class ModerationLog(SQLModel, table=True):
    """Registro de eventos de moderación de contenido.

    Almacena de forma inmutable los textos que fueron evaluados por los
    guardrails de contenido (input o output). No se usa soft-delete.

    Attributes:
        id: Identificador autoincremental.
        layer: Capa donde ocurrió la evaluación (input, output, guard).
        snippet: Fragmento del texto evaluado (truncado a 200 chars).
        created_at: Fecha y hora del evento (UTC).
    """

    __tablename__ = "moderation_log"

    id: int = Field(default=None, primary_key=True)
    layer: str
    snippet: str = Field(max_length=200)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
