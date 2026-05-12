"""Modelo de base de datos para contenidos generados de entidades."""

from datetime import datetime, timezone

from sqlalchemy import Column, ForeignKey, String
from sqlmodel import Field, SQLModel

from app.core.database.soft_delete import SoftDeleteMixin
from app.models.enums import ContentCategory, ContentStatus


class EntityContent(SQLModel, SoftDeleteMixin, table=True):
    """Contenido generado por RAG asociado a una entidad.

        Representa una versión del contenido (backstory, scene, etc.) con su
        estado de revisión. La información original de la generación se almacena
        en GeneratedText.

    Attributes:
            id: Identificador único UUID.
            entity_id: Entidad a la que pertenece el contenido.
            collection_id: Colección de la entidad.
            generated_text_id: Referencia al texto original generado por el LLM.
            category: Categoría del contenido (lore, backstory, personality, etc.).
            content: Texto del contenido generado.
            status: Estado del contenido (pending, confirmed, discarded).
            is_shared: Si el contenido ha sido compartido en el feed público.
            created_at: Fecha y hora de creación (UTC).
            confirmed_at: Fecha y hora de confirmación (UTC), o None.
            updated_at: Fecha y hora de última modificación (UTC).
            updated_by: UUID del último usuario que modificó (audit trail).

    """

    __tablename__ = "entity_contents"

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
        )
    )
    collection_id: str = Field(
        sa_column=Column(
            String(36),
            ForeignKey("collections.id"),
            nullable=False,
            index=True,
        )
    )
    generated_text_id: str = Field(
        sa_column=Column(
            String(36),
            ForeignKey("generated_texts.id"),
            nullable=False,
            index=True,
        )
    )
    category: ContentCategory = Field(max_length=50)
    content: str = Field(max_length=10000)
    status: ContentStatus = Field(default=ContentStatus.pending, max_length=50)
    is_shared: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confirmed_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)
    updated_by: str | None = Field(default=None, max_length=36)
