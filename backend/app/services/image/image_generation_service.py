"""Servicios de lógica de negocio para generación de imágenes."""

import logging
import uuid as _uuid
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

from sqlmodel import Session, select

from app.core.config import settings
from app.core.database.utils import db_commit
from app.core.exceptions import NoContextAvailableError
from app.core.storage import build_storage_url
from app.domain.content_guard import check_prompt_length, check_user_input
from app.engine.image_prompt_builder import build_visual_prompt
from app.models.db.entity import Entity
from app.models.db.entity_content import EntityContent
from app.models.db.image_generation import ImageGeneration, ImageRecord
from app.models.enums import ContentCategory, ContentStatus
from app.models.schemas.image_generation import (
    BuildPromptResponse,
    GenerateImagesResponse,
    ImageGenerationListItem,
    ImageRecordResponse,
    ImageResult,
)
from app.services.image._backends import (
    _generate_comfyui_images,
    _generate_mock_images,
    _GenerationParams,
    _ImageData,
)

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_CATEGORIES = {
    ContentCategory.extended_description,
    ContentCategory.backstory,
    ContentCategory.scene,
}


# ── Helpers de consulta / persistencia ───────────────────────────────────────

def _get_confirmed_content(
    session: Session,
    entity: Entity,
    content_id: str,
) -> EntityContent | None:
    return session.exec(
        select(EntityContent).where(
            EntityContent.id == content_id,
            EntityContent.entity_id == entity.id,
            EntityContent.collection_id == entity.collection_id,
            EntityContent.status == ContentStatus.confirmed,
            EntityContent.is_deleted.is_(False),
        ),
    ).first()


def _build_url(storage_path: str | None) -> str | None:
    return build_storage_url(storage_path)


def _create_image_generation(
    session: Session,
    entity: Entity,
    generation_id: str,
    params: _GenerationParams,
) -> ImageGeneration:
    generation = ImageGeneration(
        id=generation_id,
        entity_id=entity.id,
        collection_id=entity.collection_id,
        content_id=params.content_id,
        category=params.category,
        auto_prompt=params.auto_prompt,
        final_prompt=params.final_prompt,
        prompt_token_count=len(params.auto_prompt) // 4,
        batch_size=params.batch_size,
        backend=params.backend,
        width=settings.image_width,
        height=settings.image_height,
    )
    session.add(generation)
    return generation


def _create_image_record(
    session: Session,
    entity: Entity,
    generation_id: str,
    data: _ImageData,
) -> ImageRecord:
    record = ImageRecord(
        id=data.image_id,
        generation_id=generation_id,
        entity_id=entity.id,
        collection_id=entity.collection_id,
        seed=data.seed,
        storage_path=data.storage_path,
        image_url=data.image_url,
        filename=data.filename,
        extension="png",
        width=settings.image_width,
        height=settings.image_height,
        generation_ms=0,
    )
    session.add(record)
    return record


# ── API pública ───────────────────────────────────────────────────────────────

def build_prompt_service(
    session: Session,
    entity: Entity,
    content_id: str,
) -> BuildPromptResponse:
    """Construye el prompt automático sin guardar nada (efímero).

    Raises:
        NoContextAvailableError: Si el contenido no existe o no está confirmado.

    """
    content = _get_confirmed_content(session, entity, content_id)
    if not content:
        raise NoContextAvailableError

    if content.category not in ALLOWED_IMAGE_CATEGORIES:
        msg = f"Categoría '{content.category.value}' no soportada para generación de imágenes"
        raise ValueError(msg)

    build_result = build_visual_prompt(
        entity_type=entity.type,
        confirmed_content=content.content,
        category=content.category,
        max_tokens=settings.image_prompt_tokens,
    )
    return BuildPromptResponse(
        auto_prompt=build_result["prompt"],
        token_count=build_result["token_count"],
    )


def generate_images_service(
    session: Session,
    username: str,
    entity: Entity,
    content_id: str,
    auto_prompt: str,
    final_prompt: str,
    batch_size: int,
    seed_base: int | None = None,
) -> GenerateImagesResponse:
    """Genera un batch de imágenes usando el backend configurado.

    Raises:
        NoContextAvailableError: Si el contenido no existe o no está confirmado.
        ValueError: Si image_backend no es "mock" ni "comfyui".
        ComfyUIUnavailableError / ComfyUITimeoutError: Errores del backend ComfyUI.

    """
    content = _get_confirmed_content(session, entity, content_id)
    if not content:
        raise NoContextAvailableError

    check_prompt_length(final_prompt)
    check_user_input(auto_prompt)
    check_user_input(final_prompt)

    params = _GenerationParams(
        content_id=content_id,
        category=content.category.value,
        auto_prompt=auto_prompt,
        final_prompt=final_prompt,
        batch_size=batch_size,
        seed_base=seed_base if seed_base is not None else settings.image_seed_base,
        backend=settings.image_backend,
    )

    generation_id = str(_uuid.uuid4())
    _create_image_generation(session, entity, generation_id, params)

    if params.backend == "mock":
        images_data = _generate_mock_images(entity, params.batch_size, params.seed_base)
    elif params.backend == "comfyui":
        images_data = _generate_comfyui_images(username, entity, params, generation_id)
    else:
        msg = f"Backend '{params.backend}' no soportado. Usar: 'mock' o 'comfyui'"
        raise ValueError(msg)

    images_result: list[ImageResult] = []
    for data in images_data:
        _create_image_record(session, entity, generation_id, data)
        images_result.append(
            ImageResult(
                id=data.image_id,
                image_url=_build_url(data.storage_path) or data.image_url,
                seed=data.seed,
                width=settings.image_width,
                height=settings.image_height,
                generation_ms=0,
            )
        )

    db_commit(session, f"generate_images({entity.id})")
    return GenerateImagesResponse(
        generation_id=generation_id,
        auto_prompt=auto_prompt,
        final_prompt=final_prompt,
        batch_size=batch_size,
        backend=params.backend,
        images=images_result,
    )


def share_image_service(
    session: Session,
    entity: Entity,
    generation_id: str,
    image_id: str,
    *,
    shared: bool,
) -> ImageRecordResponse:
    """Marca o desmarca una imagen como compartida públicamente.

    Raises:
        NoContextAvailableError: Si la imagen no existe o no pertenece a la entidad.

    """
    record = session.exec(
        select(ImageRecord).where(
            ImageRecord.id == image_id,
            ImageRecord.generation_id == generation_id,
            ImageRecord.entity_id == entity.id,
            ImageRecord.is_deleted.is_(False),
        ),
    ).first()
    if not record:
        raise NoContextAvailableError

    record.is_shared = shared
    db_commit(session, f"share_image({image_id})")
    session.refresh(record)

    return ImageRecordResponse(
        id=record.id,
        generation_id=record.generation_id,
        entity_id=record.entity_id,
        collection_id=record.collection_id,
        seed=record.seed,
        storage_path=record.storage_path,
        image_url=record.image_url,
        filename=record.filename,
        extension=record.extension,
        width=record.width,
        height=record.height,
        generation_ms=record.generation_ms,
        is_shared=record.is_shared,
        created_at=record.created_at,
        is_deleted=record.is_deleted,
        deleted_at=record.deleted_at,
    )


def delete_image_service(
    session: Session,
    entity: Entity,
    generation_id: str,
    image_id: str,
) -> None:
    """Elimina una imagen individual del batch (soft delete + borrado de fichero).

    Raises:
        NoContextAvailableError: Si la imagen no existe o no pertenece a la entidad.

    """
    record = session.exec(
        select(ImageRecord).where(
            ImageRecord.id == image_id,
            ImageRecord.generation_id == generation_id,
            ImageRecord.entity_id == entity.id,
            ImageRecord.is_deleted.is_(False),
        ),
    ).first()
    if not record:
        raise NoContextAvailableError

    record.is_shared = False
    record.is_deleted = True
    record.deleted_at = datetime.now(UTC)

    # storage_path puede ser None en imágenes mock aunque el backend cambie
    if settings.image_backend != "mock" and record.storage_path:
        full_path = Path(settings.media_root) / record.storage_path
        with suppress(FileNotFoundError, OSError):
            full_path.unlink()

    db_commit(session, f"delete_image({image_id})")


def get_generation_service(
    session: Session,
    entity: Entity,
    generation_id: str,
) -> GenerateImagesResponse:
    """Obtiene una generación existente con sus imágenes.

    Raises:
        NoContextAvailableError: Si la generación no existe o no pertenece a la entidad.

    """
    generation = session.exec(
        select(ImageGeneration).where(
            ImageGeneration.id == generation_id,
            ImageGeneration.entity_id == entity.id,
            ImageGeneration.is_deleted.is_(False),
        ),
    ).first()
    if not generation:
        raise NoContextAvailableError

    records = session.exec(
        select(ImageRecord).where(
            ImageRecord.generation_id == generation_id,
            ImageRecord.is_deleted.is_(False),
        ),
    ).all()

    images = [
        ImageResult(
            id=r.id,
            image_url=_build_url(r.storage_path) or r.image_url,
            seed=r.seed,
            width=r.width,
            height=r.height,
            generation_ms=r.generation_ms,
        )
        for r in records
    ]

    return GenerateImagesResponse(
        generation_id=generation.id,
        auto_prompt=generation.auto_prompt,
        final_prompt=generation.final_prompt,
        batch_size=generation.batch_size,
        backend=generation.backend,
        images=images,
    )


def list_generations_service(
    session: Session,
    entity: Entity,
) -> tuple[list, int]:
    """Lista todas las generaciones de imágenes de una entidad."""
    generations = session.exec(
        select(ImageGeneration)
        .where(
            ImageGeneration.entity_id == entity.id,
            ImageGeneration.collection_id == entity.collection_id,
            ImageGeneration.is_deleted.is_(False),
        )
        .order_by(ImageGeneration.created_at.desc()),
    ).all()

    result = []
    for gen in generations:
        records = session.exec(
            select(ImageRecord)
            .where(
                ImageRecord.generation_id == gen.id,
                ImageRecord.is_deleted.is_(False),
            )
            .order_by(ImageRecord.seed.asc()),
        ).all()

        images = [
            ImageRecordResponse(
                id=r.id,
                generation_id=r.generation_id,
                entity_id=r.entity_id,
                collection_id=r.collection_id,
                seed=r.seed,
                storage_path=r.storage_path,
                image_url=r.image_url,
                filename=r.filename,
                extension=r.extension,
                width=r.width,
                height=r.height,
                generation_ms=r.generation_ms,
                is_shared=r.is_shared,
                created_at=r.created_at,
                is_deleted=r.is_deleted,
                deleted_at=r.deleted_at,
            )
            for r in records
        ]

        result.append(
            ImageGenerationListItem(
                id=gen.id,
                entity_id=gen.entity_id,
                collection_id=gen.collection_id,
                content_id=gen.content_id,
                category=gen.category,
                auto_prompt=gen.auto_prompt,
                final_prompt=gen.final_prompt,
                batch_size=gen.batch_size,
                backend=gen.backend,
                width=gen.width,
                height=gen.height,
                created_at=gen.created_at,
                is_deleted=gen.is_deleted,
                images=images,
            )
        )

    return result, len(result)
