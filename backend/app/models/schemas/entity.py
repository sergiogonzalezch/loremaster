"""Esquemas Pydantic para entidades."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.db.entity import EntityType


class EntityRequest(BaseModel):
    """Esquema para crear una nueva entidad.

    Attributes:
        type: Tipo de entidad (character, creature, faction, location, item).
        name: Nombre único dentro de la colección.
        description: Descripción inicial de referencia.

    """

    type: EntityType
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)


CreateEntityRequest = EntityRequest


class UpdateEntityRequest(BaseModel):
    """Esquema para actualizar una entidad existente.

    Attributes:
        type: Nuevo tipo (opcional).
        name: Nuevo nombre (opcional).
        description: Nueva descripción (opcional).

    """

    type: EntityType | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class EntityResponse(BaseModel):
    """Respuesta con los datos de una entidad.

    Attributes:
        id: Identificador único.
        collection_id: Colección a la que pertenece.
        type: Tipo de entidad.
        name: Nombre.
        description: Descripción.
        created_at: Fecha de creación.
        updated_at: Fecha de última modificación.

    """

    id: str
    collection_id: str
    type: EntityType
    name: str
    description: str
    created_at: datetime
    updated_at: datetime | None = None
