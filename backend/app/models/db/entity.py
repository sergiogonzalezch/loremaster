from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, ForeignKey, String, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.database.soft_delete import SoftDeleteMixin


class EntityType(str, Enum):
    """Tipos de entidad que pueden existir dentro de una colección.

    Attributes:
        character: Persona, héroe, NPC o cualquier ser consciente.
        creature: Bestia, monstruo o ser no humano.
        faction: Organización, guild, reino o grupo.
        location: Lugar, ciudad, dungeon o región geográfica.
        item: Objeto, artefacto, arma o recurso.
    """

    character = "character"
    creature = "creature"
    faction = "faction"
    location = "location"
    item = "item"


class Entity(SQLModel, SoftDeleteMixin, table=True):
    """Entidad dentro de una colección (personaje, criatura, facción, etc.).

    Attributes:
            id: Identificador único UUID.
            collection_id: Colección a la que pertenece.
            type: Tipo de entidad (character, creature, location, faction, item).
            name: Nombre único dentro de la colección.
            description: Descripción inicial o notes de referencia.
            created_at: Fecha y hora de creación (UTC).
            updated_at: Fecha y hora de última modificación (UTC).
            updated_by: UUID del último usuario que modificó (audit trail).
    """

    __tablename__ = "entities"
    __table_args__ = (
        UniqueConstraint("collection_id", "name", name="uq_entity_collection_name"),
    )

    id: str = Field(
        default_factory=lambda: str(__import__("uuid").uuid4()),
        primary_key=True,
        max_length=36,
    )
    collection_id: str = Field(
        sa_column=Column(
            String(36),
            ForeignKey("collections.id"),
            nullable=False,
            index=True,
        )
    )
    type: EntityType = Field(index=True, max_length=50)
    name: str = Field(max_length=200)
    description: str = Field(default="", max_length=2000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = Field(default=None)
    updated_by: str | None = Field(default=None, max_length=36)
