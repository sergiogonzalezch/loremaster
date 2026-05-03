# app/services/image_generation_service.py

import uuid as _uuid
import os

from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.core.config import settings
from app.core.exceptions import DatabaseError, NoContextAvailableError
from app.domain.prompt_builder import build_visual_prompt, get_prompt_source_label
from app.models.entities import Entity
from app.models.entity_content import EntityContent
from app.models.enums import ContentCategory, ContentStatus
from app.models.image_generation import (
    ImageGeneration,
    ImageRecord,
    BuildPromptRequest,
    BuildPromptResponse,
    GenerateImagesRequest,
    GenerateImagesResponse,
    ImageResult,
    ImageGenerationResponse,
    ImageRecordResponse,
)

ALLOWED_IMAGE_CATEGORIES = {
    ContentCategory.extended_description,
    ContentCategory.backstory,
    ContentCategory.scene,
    ContentCategory.chapter,
}


def _get_confirmed_content(
    session: Session,
    entity: Entity,
    content_id: str,
) -> EntityContent | None:
    """Busca un EntityContent confirmado que pertenezca a la entidad."""
    return session.exec(
        select(EntityContent).where(
            EntityContent.id == content_id,
            EntityContent.entity_id == entity.id,
            EntityContent.collection_id == entity.collection_id,
            EntityContent.status == ContentStatus.confirmed,
            EntityContent.is_deleted == False,
        )
    ).first()


def _build_url(storage_path: str | None) -> str | None:
    """Construye la URL completa desde el storage_path."""
    if not storage_path:
        return None
    return f"{settings.storage_base_url}/{storage_path}"


def _generate_mock_images(
    entity: Entity,
    batch_size: int,
) -> list[tuple[str, str]]:
    """Genera URLs placeholder para el backend mock."""
    images = []
    for i in range(batch_size):
        image_id = str(_uuid.uuid4())
        seed = settings.image_seed_base + i
        placeholder_url = (
            f"https://placehold.co/{settings.image_width}x{settings.image_height}/1a1a2e/9d6fe8"
            f"?text={entity.name.replace(' ', '+')}+{i+1}"
        )
        images.append((image_id, placeholder_url))
    return images


def build_prompt_service(
    session: Session,
    entity: Entity,
    content_id: str,
) -> BuildPromptResponse:
    """
    Construye el prompt automático sin guardar nada (efímero).

    Flujo:
    1. Validar que content_id pertenece al entity y está confirmado
    2. Validar que la categoría es soportada para imágenes
    3. build_visual_prompt() con estrategia según settings.prompt_strategy
    4. Retornar respuesta efímera

    Raises:
        NoContextAvailableError: Si el contenido no existe o no está confirmado
        ValueError: Si la categoría no es soportada para generación de imágenes
    """
    content = _get_confirmed_content(session, entity, content_id)
    if not content:
        raise NoContextAvailableError()

    if content.category not in ALLOWED_IMAGE_CATEGORIES:
        raise ValueError(
            f"Categoría '{content.category.value}' no soportada para generación de imágenes"
        )

    build_result = build_visual_prompt(
        entity_type=entity.type,
        entity_name=entity.name,
        entity_description=entity.description,
        confirmed_content=content.content,
        category=content.category,
        max_tokens=settings.image_prompt_max_tokens,
        target_tokens=settings.image_prompt_target_tokens,
    )

    return BuildPromptResponse(
        auto_prompt=build_result["prompt"],
        prompt_source=build_result["source"],
        prompt_source_label=get_prompt_source_label(build_result["source"]),
        prompt_strategy=build_result["strategy"],
        token_count=build_result["token_count"],
        truncated=build_result["truncated"],
    )


def generate_images_service(
    session: Session,
    entity: Entity,
    content_id: str,
    final_prompt: str,
    batch_size: int,
) -> GenerateImagesResponse:
    """
    Genera un batch de imágenes.

    Flujo:
    1. Validar content_id confirmado
    2. Obtener auto_prompt del content_id (para guardar en DB)
    3. Si backend == "mock": generar placeholders (sin persistencia)
    4. Si backend != "mock": generar imágenes reales + persistir
    5. Retornar respuesta

    Raises:
        NoContextAvailableError: Si el contenido no existe o no está confirmado
    """
    content = _get_confirmed_content(session, entity, content_id)
    if not content:
        raise NoContextAvailableError()

    auto_build = build_visual_prompt(
        entity_type=entity.type,
        entity_name=entity.name,
        entity_description=entity.description,
        confirmed_content=content.content,
        category=content.category,
        max_tokens=settings.image_prompt_max_tokens,
        target_tokens=settings.image_prompt_target_tokens,
    )

    generation_id = str(_uuid.uuid4())
    generation = ImageGeneration(
        id=generation_id,
        entity_id=entity.id,
        collection_id=entity.collection_id,
        content_id=content_id,
        category=content.category.value,
        auto_prompt=auto_build["prompt"],
        final_prompt=final_prompt,
        prompt_token_count=auto_build["token_count"],
        prompt_source=auto_build["source"],
        truncated=auto_build["truncated"],
        batch_size=batch_size,
        backend=settings.image_backend,
        width=settings.image_width,
        height=settings.image_height,
    )

    session.add(generation)

    images_result: list[ImageResult] = []

    if settings.image_backend == "mock":
        mock_images = _generate_mock_images(entity, batch_size)
        for image_id, image_url in mock_images:
            images_result.append(
                ImageResult(
                    id=image_id,
                    image_url=image_url,
                    seed=settings.image_seed_base + len(images_result),
                    width=settings.image_width,
                    height=settings.image_height,
                    generation_ms=0,
                )
            )
    else:
        for i in range(batch_size):
            image_id = str(_uuid.uuid4())
            seed = settings.image_seed_base + i
            storage_path = (
                f"{entity.collection_id}/{entity.id}/{generation_id}/{image_id}.png"
            )

            record = ImageRecord(
                id=image_id,
                generation_id=generation_id,
                entity_id=entity.id,
                collection_id=entity.collection_id,
                seed=seed,
                storage_path=storage_path,
                filename=f"{image_id}.png",
                extension="png",
                width=settings.image_width,
                height=settings.image_height,
                generation_ms=0,
            )
            session.add(record)

            images_result.append(
                ImageResult(
                    id=image_id,
                    image_url=_build_url(storage_path),
                    seed=seed,
                    width=settings.image_width,
                    height=settings.image_height,
                    generation_ms=0,
                )
            )

    try:
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        raise DatabaseError() from e

    return GenerateImagesResponse(
        generation_id=generation_id,
        auto_prompt=auto_build["prompt"],
        final_prompt=final_prompt,
        prompt_source=auto_build["source"],
        prompt_source_label=get_prompt_source_label(auto_build["source"]),
        batch_size=batch_size,
        backend=settings.image_backend,
        images=images_result,
    )


def delete_image_service(
    session: Session,
    entity: Entity,
    generation_id: str,
    image_id: str,
) -> None:
    """
    Elimina una imagen individual del batch (soft delete).

    Raises:
        NoContextAvailableError: Si la imagen no existe o no pertenece a la entidad
    """
    record = session.exec(
        select(ImageRecord).where(
            ImageRecord.id == image_id,
            ImageRecord.generation_id == generation_id,
            ImageRecord.entity_id == entity.id,
            ImageRecord.is_deleted == False,
        )
    ).first()

    if not record:
        raise NoContextAvailableError()

    record.is_deleted = True
    record.deleted_at = datetime.now(timezone.utc)

    if settings.image_backend != "mock":
        full_path = os.path.join(settings.media_root, record.storage_path)
        if full_path and os.path.exists(full_path):
            try:
                os.remove(full_path)
            except OSError:
                pass

    try:
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        raise DatabaseError() from e


def get_generation_service(
    session: Session,
    entity: Entity,
    generation_id: str,
) -> GenerateImagesResponse:
    """
    Obtiene una generación existente con sus imágenes.

    Raises:
        NoContextAvailableError: Si la generación no existe o no pertenece a la entidad
    """
    generation = session.exec(
        select(ImageGeneration).where(
            ImageGeneration.id == generation_id,
            ImageGeneration.entity_id == entity.id,
            ImageGeneration.is_deleted == False,
        )
    ).first()

    if not generation:
        raise NoContextAvailableError()

    records = session.exec(
        select(ImageRecord).where(
            ImageRecord.generation_id == generation_id,
            ImageRecord.is_deleted == False,
        )
    ).all()

    images = [
        ImageResult(
            id=r.id,
            image_url=_build_url(r.storage_path),
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
        prompt_source=generation.prompt_source,
        prompt_source_label=get_prompt_source_label(generation.prompt_source),
        batch_size=generation.batch_size,
        backend=generation.backend,
        images=images,
    )