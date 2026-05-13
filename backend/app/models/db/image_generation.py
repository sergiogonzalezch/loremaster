"""Modelos de base de datos para generación de imágenes y registros de imágenes."""

from datetime import datetime, timezone

from sqlalchemy import Column, ForeignKey, String
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel

from app.core.database.soft_delete import SoftDeleteMixin


class ImageGeneration(SQLModel, SoftDeleteMixin, table=True):
    """Solicitud de generación de imágenes para una entidad.

    Registra los prompts generados por el LLM y los parámetros usados.
    Cada solicitud puede generar múltiples imágenes (batch).

    Attributes:
        id: Identificador único UUID.
        entity_id: Entidad asociada a la generación.
        collection_id: Colección de la entidad.
        content_id: EntityContent usado como fuente del prompt (opcional).
        category: Categoría del contenido usado como base.
        auto_prompt: Prompt generado automáticamente por el LLM.
        final_prompt: Prompt final enviado al motor de generación.
        prompt_token_count: Número de tokens del prompt.
        batch_size: Cantidad de imágenes a generar (1-4).
        backend: Motor usado (comfyui, mock, etc.).
        width: Ancho de las imágenes generadas.
        height: Alto de las imágenes generadas.
        created_at: Fecha y hora de la solicitud (UTC).

    """

    __tablename__ = "image_generations"

    id: str = SQLField(
        default_factory=lambda: str(__import__("uuid").uuid4()),
        primary_key=True,
        max_length=36,
    )
    entity_id: str = SQLField(
        sa_column=Column(
            String(36),
            ForeignKey("entities.id"),
            nullable=False,
            index=True,
        ),
    )
    collection_id: str = SQLField(
        sa_column=Column(
            String(36),
            ForeignKey("collections.id"),
            nullable=False,
            index=True,
        ),
    )
    content_id: str | None = SQLField(
        sa_column=Column(
            String(36),
            ForeignKey("entity_contents.id"),
            nullable=True,
            index=True,
        ),
    )
    category: str = SQLField(max_length=50)

    auto_prompt: str = SQLField(max_length=1000)
    final_prompt: str = SQLField(max_length=1000)
    prompt_token_count: int = SQLField(default=0)

    batch_size: int = SQLField(default=4)
    backend: str = SQLField(default="mock", max_length=20)
    width: int = SQLField(default=1024)
    height: int = SQLField(default=1024)

    created_at: datetime = SQLField(default_factory=lambda: datetime.now(timezone.utc))


class ImageRecord(SQLModel, SoftDeleteMixin, table=True):
    """Registro de una imagen individual generada dentro de un batch.

    Attributes:
        id: Identificador único UUID.
        generation_id: ImageGeneration a la que pertenece.
        entity_id: Entidad asociada a la imagen.
        collection_id: Colección de la entidad.
        seed: Semilla del generador para reproducibilidad.
        storage_path: Ruta de almacenamiento local del archivo.
        image_url: URL pública de la imagen (si está disponible).
        filename: Nombre del archivo generado.
        extension: Extensión del archivo (png, jpg, etc.).
        width: Ancho de la imagen.
        height: Alto de la imagen.
        generation_ms: Tiempo de generación en milisegundos.
        is_shared: Si la imagen ha sido compartida en el feed público.
        created_at: Fecha y hora de generación (UTC).

    """

    __tablename__ = "image_records"

    id: str = SQLField(
        default_factory=lambda: str(__import__("uuid").uuid4()),
        primary_key=True,
        max_length=36,
    )
    generation_id: str = SQLField(
        sa_column=Column(
            String(36),
            ForeignKey("image_generations.id"),
            nullable=False,
            index=True,
        ),
    )
    entity_id: str = SQLField(
        sa_column=Column(
            String(36),
            ForeignKey("entities.id"),
            nullable=False,
            index=True,
        ),
    )
    collection_id: str = SQLField(
        sa_column=Column(
            String(36),
            ForeignKey("collections.id"),
            nullable=False,
            index=True,
        ),
    )

    seed: int = SQLField(default=42)
    storage_path: str | None = SQLField(default=None, max_length=500)
    image_url: str | None = SQLField(default=None, max_length=500)
    filename: str | None = SQLField(default=None, max_length=255)
    extension: str = SQLField(default="png", max_length=10)
    width: int = SQLField(default=1024)
    height: int = SQLField(default=1024)
    generation_ms: int = SQLField(default=0)

    is_shared: bool = SQLField(default=False)
    created_at: datetime = SQLField(default_factory=lambda: datetime.now(timezone.utc))
