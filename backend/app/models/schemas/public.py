from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SharedContentSummary(BaseModel):
    """Resumen de un contenido compartido en el perfil público de un usuario.

    Attributes:
        id: Identificador del contenido.
        content: Texto completo del contenido.
        category: Categoría del contenido.
        entity_name: Nombre de la entidad asociada.
        entity_type: Tipo de la entidad.
        confirmed_at: Fecha de confirmación (None si no confirmado).
        created_at: Fecha de creación del contenido.
    """

    id: str
    content: str
    category: str
    entity_name: str
    entity_type: str
    confirmed_at: Optional[datetime] = None
    created_at: datetime


class SharedImageSummary(BaseModel):
    """Resumen de una imagen compartida en el perfil público de un usuario.

    Attributes:
        id: Identificador de la imagen.
        generation_id: Solicitud de generación asociada.
        image_url: URL pública de la imagen.
        storage_path: Ruta de almacenamiento.
        seed: Semilla del generador.
        auto_prompt: Prompt automático generado.
        final_prompt: Prompt final usado.
        entity_name: Nombre de la entidad asociada.
        entity_type: Tipo de la entidad.
        created_at: Fecha de generación.
    """

    id: str
    generation_id: str
    image_url: Optional[str] = None
    storage_path: Optional[str] = None
    seed: int
    auto_prompt: str
    final_prompt: str
    entity_name: str
    entity_type: str
    created_at: datetime


class PublicProfileResponse(BaseModel):
    """Perfil público de un usuario con sus contenidos e imágenes compartidos.

    Attributes:
        username: Nombre de usuario.
        display_name: Nombre visible públicamente.
        bio: Biografía pública.
        avatar_url: URL de la imagen de perfil.
        shared_contents: Lista de contenidos compartidos.
        shared_images: Lista de imágenes compartidas.
    """

    username: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    shared_contents: list[SharedContentSummary] = []
    shared_images: list[SharedImageSummary] = []


class PublicFeedItem(BaseModel):
    """Elemento del feed público de contenidos compartidos.

    Attributes:
        content_id: Identificador del contenido.
        content: Texto completo del contenido.
        content_preview: Vista previa truncada.
        category: Categoría del contenido.
        entity_name: Nombre de la entidad.
        entity_type: Tipo de la entidad.
        owner_username: Nombre del propietario.
        owner_display_name: Nombre visible del propietario.
        confirmed_at: Fecha de confirmación.
        created_at: Fecha de creación.
    """

    content_id: str
    content: str
    content_preview: str
    category: str
    entity_name: str
    entity_type: str
    owner_username: str
    owner_display_name: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    created_at: datetime


class PublicImageItem(BaseModel):
    """Elemento del feed público de imágenes compartidas.

    Attributes:
        image_id: Identificador de la imagen.
        generation_id: Solicitud de generación asociada.
        image_url: URL de la imagen.
        storage_path: Ruta de almacenamiento.
        seed: Semilla del generador.
        auto_prompt: Prompt automático.
        final_prompt: Prompt final.
        entity_name: Nombre de la entidad.
        entity_type: Tipo de la entidad.
        owner_username: Nombre del propietario.
        owner_display_name: Nombre visible del propietario.
        created_at: Fecha de generación.
    """

    image_id: str
    generation_id: str
    image_url: Optional[str] = None
    storage_path: Optional[str] = None
    seed: int
    auto_prompt: str
    final_prompt: str
    entity_name: str
    entity_type: str
    owner_username: str
    owner_display_name: Optional[str] = None
    created_at: datetime
