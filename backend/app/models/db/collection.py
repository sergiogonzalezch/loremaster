"""Modelo de base de datos para colecciones de documentos y entidades."""

from datetime import datetime, timezone

from sqlalchemy import Column, ForeignKey, String, UniqueConstraint
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel

from app.core.database.soft_delete import SoftDeleteMixin


class Collection(SQLModel, SoftDeleteMixin, table=True):
    """Representa una colección de documentos y entidades de un mundo fictional.

    Una colección pertenece a un usuario (owner_id) y agrupa documentos
    para RAG, entidades asociadas y sus contenidos generados.

    Attributes:
        id: Identificador único UUID.
        name: Nombre de la colección (único por propietario).
        description: Descripción breve del mundo o proyecto.
        owner_id: UUID del usuario propietario.
        created_at: Fecha y hora de creación (UTC).
        updated_at: Fecha y hora de última modificación (UTC).
        updated_by: UUID del último usuario que modificó (audit trail).

    """

    __tablename__ = "collections"
    __table_args__ = (
        UniqueConstraint("name", "owner_id", name="uq_collection_name_owner"),
    )

    id: str = SQLField(
        default_factory=lambda: str(__import__("uuid").uuid4()),
        primary_key=True,
        max_length=36,
    )
    name: str = SQLField(index=True, max_length=255)
    description: str = SQLField(default="", max_length=2000)
    owner_id: str | None = SQLField(
        sa_column=Column(
            String(36),
            ForeignKey("users.id"),
            nullable=True,
            index=True,
        )
    )
    created_at: datetime = SQLField(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = SQLField(default=None)
    updated_by: str | None = SQLField(default=None, max_length=36)
