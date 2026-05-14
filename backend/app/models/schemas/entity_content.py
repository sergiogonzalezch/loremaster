"""Esquemas Pydantic para contenidos de entidad."""

from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.enums import ContentCategory, ContentStatus


class EntityContentResponse(BaseModel):
    """Respuesta con los datos completos de un contenido de entidad.

    Attributes:
        id: Identificador único.
        entity_id: Entidad propietaria.
        collection_id: Colección de la entidad.
        generated_text_id: Referencia al GeneratedText.
        category: Categoría del contenido.
        content: Texto final (puede estar editado).
        raw_content: Texto original del LLM (None si fue editado).
        was_edited: Indica si el contenido fue editado tras la generación.
        query: Consulta original del usuario.
        sources_count: Fragmentos de contexto utilizados.
        token_count: Tokens estimados de la respuesta.
        status: Estado del ciclo de vida.
        is_shared: Si está compartido en el feed público.
        created_at: Fecha de creación.
        confirmed_at: Fecha de confirmación.
        updated_at: Fecha de última modificación.

    """

    id: str
    entity_id: str
    collection_id: str
    generated_text_id: str
    category: ContentCategory
    content: str
    raw_content: str | None = None
    was_edited: bool = False
    query: str | None = None
    sources_count: int = 0
    token_count: int = 0
    model_used: str | None = None
    status: ContentStatus
    is_shared: bool = False
    created_at: datetime
    confirmed_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def compute_was_edited(self) -> "EntityContentResponse":
        """Calcula si el contenido fue editado comparando con el texto original."""
        if self.raw_content is not None:
            object.__setattr__(self, "was_edited", self.content != self.raw_content)
        return self


class GenerateContentRequest(BaseModel):
    """Esquema para solicitar la generación de contenido.

    Attributes:
        query: Consulta o prompt del usuario para la generación.
        model: Modelo Ollama a usar. Si es None usa el modelo por defecto del servidor.

    """

    query: str = Field(..., min_length=5, max_length=2000)
    model: str | None = Field(default=None, max_length=100)


class UpdateContentRequest(BaseModel):
    """Esquema para editar el texto de un contenido.

    Attributes:
        content: Nuevo texto para el contenido.

    """

    content: str = Field(..., min_length=1, max_length=10000)


class ShareContentRequest(BaseModel):
    """Esquema para compartir o dejar de compartir un contenido.

    Attributes:
        shared: True para compartir, False para dejar de compartir.

    """

    shared: bool
