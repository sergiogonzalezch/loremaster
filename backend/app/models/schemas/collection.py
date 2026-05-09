from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CreateCollectionRequest(BaseModel):
    """Esquema para la creación de una nueva colección.

    Attributes:
        name: Nombre de la colección (1-255 caracteres).
        description: Descripción opcional del mundo o proyecto.
    """

    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)


class UpdateCollectionRequest(BaseModel):
    """Esquema para actualizar el nombre o descripción de una colección.

    Attributes:
        name: Nuevo nombre (opcional).
        description: Nueva descripción (opcional).
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)


class CollectionResponse(BaseModel):
    """Respuesta con los datos de una colección.

    Attributes:
        id: Identificador único.
        name: Nombre de la colección.
        description: Descripción.
        owner_id: UUID del propietario.
        created_at: Fecha de creación.
        updated_at: Fecha de última modificación.
        document_count: Número de documentos en la colección.
        entity_count: Número de entidades en la colección.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    owner_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    document_count: int = 0
    entity_count: int = 0
