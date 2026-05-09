from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BuildPromptRequest(BaseModel):
    """Esquema para generar un prompt automático a partir de un contenido.

    Attributes:
        content_id: ID del EntityContent confirmado a usar como base.
    """

    content_id: str


class GenerateImagesRequest(BaseModel):
    """Esquema para solicitar la generación de imágenes.

    Attributes:
        content_id: ID del contenido de referencia.
        auto_prompt: Prompt generado automáticamente por el LLM.
        final_prompt: Prompt final enviado al motor.
        batch_size: Cantidad de imágenes a generar (1-4).
        seed_base: Semilla base para reproducibilidad del batch.
    """

    content_id: str
    auto_prompt: str
    final_prompt: str
    batch_size: int = Field(default=4, ge=1, le=4)
    seed_base: Optional[int] = None


class DeleteImageRequest(BaseModel):
    """Esquema para eliminar una imagen generada.

    Attributes:
        image_id: ID de la imagen a eliminar.
    """

    image_id: str


class ShareImageRequest(BaseModel):
    """Esquema para compartir o dejar de compartir una imagen.

    Attributes:
        shared: True para compartir, False para dejar de compartir.
    """

    shared: bool


class ImageResult(BaseModel):
    """Resultado individual de una imagen dentro de un batch.

    Attributes:
        id: Identificador de la imagen.
        image_url: URL pública de la imagen.
        seed: Semilla usada.
        width: Ancho en píxeles.
        height: Alto en píxeles.
        generation_ms: Tiempo de generación.
    """

    id: str
    image_url: Optional[str] = None
    seed: int
    width: int
    height: int
    generation_ms: int


class BuildPromptResponse(BaseModel):
    """Respuesta tras generar un prompt automático.

    Attributes:
        auto_prompt: Prompt generado por el LLM.
        token_count: Número de tokens del prompt.
    """

    auto_prompt: str
    token_count: int


class GenerateImagesResponse(BaseModel):
    """Respuesta completa tras la generación de imágenes.

    Attributes:
        generation_id: ID de la solicitud de generación.
        auto_prompt: Prompt automático usado.
        final_prompt: Prompt final.
        batch_size: Cantidad de imágenes generadas.
        backend: Motor de generación utilizado.
        images: Lista de imágenes generadas.
    """

    generation_id: str
    auto_prompt: str
    final_prompt: str
    batch_size: int
    backend: str
    images: list[ImageResult]


class ImageGenerationResponse(BaseModel):
    """Respuesta con los datos de una solicitud de generación de imágenes.

    Attributes:
        id: Identificador de la solicitud.
        entity_id: Entidad asociada.
        collection_id: Colección de la entidad.
        content_id: Contenido usado como base (opcional).
        category: Categoría del contenido.
        auto_prompt: Prompt automático.
        final_prompt: Prompt final.
        prompt_token_count: Tokens del prompt.
        batch_size: Tamaño del batch.
        backend: Motor usado.
        width: Ancho de las imágenes.
        height: Alto de las imágenes.
        created_at: Fecha de creación.
        is_deleted: Si está eliminada.
        deleted_at: Fecha de eliminación.
    """

    id: str
    entity_id: str
    collection_id: str
    content_id: Optional[str] = None
    category: str
    auto_prompt: str
    final_prompt: str
    prompt_token_count: int
    batch_size: int
    backend: str
    width: int
    height: int
    created_at: datetime
    is_deleted: bool
    deleted_at: Optional[datetime] = None


class ImageRecordResponse(BaseModel):
    """Respuesta con los datos de una imagen individual.

    Attributes:
        id: Identificador de la imagen.
        generation_id: Solicitud de generación.
        entity_id: Entidad asociada.
        collection_id: Colección.
        seed: Semilla.
        storage_path: Ruta de almacenamiento.
        image_url: URL pública.
        filename: Nombre del archivo.
        extension: Extensión.
        width: Ancho.
        height: Alto.
        generation_ms: Tiempo de generación.
        is_shared: Si está compartida.
        created_at: Fecha de creación.
        is_deleted: Si está eliminada.
        deleted_at: Fecha de eliminación.
    """

    id: str
    generation_id: str
    entity_id: str
    collection_id: str
    seed: int
    storage_path: Optional[str] = None
    image_url: Optional[str] = None
    filename: Optional[str] = None
    extension: str
    width: int
    height: int
    generation_ms: int
    is_shared: bool = False
    created_at: datetime
    is_deleted: bool
    deleted_at: Optional[datetime] = None


class ImageGenerationListItem(BaseModel):
    """Elemento de listado de solicitudes de generación con sus imágenes.

    Attributes:
        id: ID de la solicitud.
        entity_id: Entidad.
        collection_id: Colección.
        content_id: Contenido base (opcional).
        category: Categoría.
        auto_prompt: Prompt automático.
        final_prompt: Prompt final.
        batch_size: Tamaño del batch.
        backend: Motor usado.
        width: Ancho.
        height: Alto.
        created_at: Fecha de creación.
        is_deleted: Si está eliminada.
        images: Lista de imágenes generadas.
    """

    id: str
    entity_id: str
    collection_id: str
    content_id: Optional[str] = None
    category: str
    auto_prompt: str
    final_prompt: str
    batch_size: int
    backend: str
    width: int
    height: int
    created_at: datetime
    is_deleted: bool
    images: list[ImageRecordResponse]


class ImageGenerationListResponse(BaseModel):
    """Respuesta paginada con el listado de solicitudes de generación.

    Attributes:
        generations: Lista de solicitudes con sus imágenes.
    """

    generations: list[ImageGenerationListItem]
