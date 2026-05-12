# app/services/image_generation_service.py

import logging
import uuid as _uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Session, select

from app.core.config import settings
from app.core.database.utils import db_commit
from app.core.exceptions import NoContextAvailableError
from app.core.storage import build_generation_path, save_file
from app.domain.content_guard import check_user_input
from app.engine.comfyui_client import (
    ComfyUIClient,
    inject_prompt,
    inject_seed,
    load_template,
)
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

logger = logging.getLogger(__name__)

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
    return session.exec(
        select(EntityContent).where(
            EntityContent.id == content_id,
            EntityContent.entity_id == entity.id,
            EntityContent.collection_id == entity.collection_id,
            EntityContent.status == ContentStatus.confirmed,
            EntityContent.is_deleted.is_(False),
        )
    ).first()


def _build_url(storage_path: str | None) -> str | None:
    if not storage_path:
        return None
    return f"{settings.storage_base_url}/{storage_path}"


def _create_image_record(
    session: Session,
    entity: Entity,
    generation_id: str,
    image_id: str,
    storage_path: str | None,
    filename: str,
    seed: int,
    image_url: str | None,
) -> ImageRecord:
    record = ImageRecord(
        id=image_id,
        generation_id=generation_id,
        entity_id=entity.id,
        collection_id=entity.collection_id,
        seed=seed,
        storage_path=storage_path,
        image_url=image_url,
        filename=filename,
        extension="png",
        width=settings.image_width,
        height=settings.image_height,
        generation_ms=0,
    )
    session.add(record)
    return record


def _create_image_result(
    image_id: str,
    storage_path: str | None,
    seed: int,
) -> ImageResult:
    return ImageResult(
        id=image_id,
        image_url=_build_url(storage_path),
        seed=seed,
        width=settings.image_width,
        height=settings.image_height,
        generation_ms=0,
    )


def _create_image_generation(
    session: Session,
    entity: Entity,
    generation_id: str,
    content_id: str,
    category: str,
    auto_prompt: str,
    final_prompt: str,
    batch_size: int,
    backend: str,
) -> ImageGeneration:
    generation = ImageGeneration(
        id=generation_id,
        entity_id=entity.id,
        collection_id=entity.collection_id,
        content_id=content_id,
        category=category,
        auto_prompt=auto_prompt,
        final_prompt=final_prompt,
        prompt_token_count=len(auto_prompt) // 4,
        batch_size=batch_size,
        backend=backend,
        width=settings.image_width,
        height=settings.image_height,
    )
    session.add(generation)
    return generation


def _generate_mock_images(
    entity: Entity,
    batch_size: int,
    seed_base: int,
) -> list[tuple[str, str, int]]:
    images = []
    for i in range(batch_size):
        image_id = str(_uuid.uuid4())
        seed = seed_base + i
        placeholder_url = (
            f"https://placehold.co/{settings.image_width}x{settings.image_height}/1a1a2e/9d6fe8"
            f"?text={entity.name.replace(' ', '+')}+{i+1}"
        )
        images.append((image_id, placeholder_url, seed))
    return images


def _save_comfyui_image(
    image_data: bytes,
    username: str,
    entity: Entity,
    generation_id: str,
    filename: str,
) -> str:
    relative_path = build_generation_path(
        username,
        entity.collection_id,
        entity.id,
        generation_id,
        filename,
    )
    save_file(image_data, relative_path)
    return relative_path


def _generate_comfyui_images(
    session: Session,
    username: str,
    entity: Entity,
    content_id: str,
    auto_prompt: str,
    final_prompt: str,
    batch_size: int,
    category: str,
    seed_base: int,
) -> tuple[str, list[ImageResult]]:
    generation_id = str(_uuid.uuid4())

    _create_image_generation(
        session=session,
        entity=entity,
        generation_id=generation_id,
        content_id=content_id,
        category=category,
        auto_prompt=auto_prompt,
        final_prompt=final_prompt,
        batch_size=batch_size,
        backend="comfyui",
    )

    client = ComfyUIClient(base_url=settings.comfyui_url)
    workflow_base = load_template("flux2-klein-4b-api.json")
    workflow_base = inject_prompt(workflow_base, final_prompt)

    images_result: list[ImageResult] = []

    for i in range(batch_size):
        seed = seed_base + i
        workflow = inject_seed(workflow_base, seed)

        try:
            prompt_id = client.queue_prompt(workflow)
            result = client.get_history_until_complete(prompt_id)
            output_images = client.get_output_images(result)
        except Exception as exc:
            logger.warning(
                "ComfyUI falló en iteración %d/%d: %s", i + 1, batch_size, exc
            )
            continue

        for img_info in output_images[:1]:
            try:
                image_data = client.download_image(
                    filename=img_info["filename"],
                    subfolder=img_info["subfolder"],
                    folder_type=img_info["type"],
                )
            except Exception as exc:
                logger.warning("Descarga falló en iteración %d: %s", i + 1, exc)
                continue

            image_id = str(_uuid.uuid4())
            filename = f"{image_id}.png"

            storage_path = _save_comfyui_image(
                image_data=image_data,
                username=username,
                entity=entity,
                generation_id=generation_id,
                filename=filename,
            )

            _create_image_record(
                session=session,
                entity=entity,
                generation_id=generation_id,
                image_id=image_id,
                storage_path=storage_path,
                filename=filename,
                seed=seed,
                image_url=_build_url(storage_path),
            )

            images_result.append(
                _create_image_result(
                    image_id=image_id,
                    storage_path=storage_path,
                    seed=seed,
                )
            )

    if not images_result:
        raise RuntimeError("No se generaron imágenes desde ComfyUI")

    return generation_id, images_result


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
        raise NoContextAvailableError

    if content.category not in ALLOWED_IMAGE_CATEGORIES:
        raise ValueError(
            f"Categoría '{content.category.value}' no soportada para generación de imágenes"
        )

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
    """
    Genera un batch de imágenes.

    Raises:
        NoContextAvailableError: Si el contenido no existe o no está confirmado
        ValueError: Si image_backend no es "mock" ni "comfyui"
    """
    content = _get_confirmed_content(session, entity, content_id)
    if not content:
        raise NoContextAvailableError

    check_user_input(auto_prompt)
    check_user_input(final_prompt)

    effective_seed_base = (
        seed_base if seed_base is not None else settings.image_seed_base
    )
    images_result: list[ImageResult] = []

    if settings.image_backend == "mock":
        mock_images = _generate_mock_images(entity, batch_size, effective_seed_base)
        generation_id = str(_uuid.uuid4())

        _create_image_generation(
            session=session,
            entity=entity,
            generation_id=generation_id,
            content_id=content_id,
            category=content.category.value,
            auto_prompt=auto_prompt,
            final_prompt=final_prompt,
            batch_size=batch_size,
            backend="mock",
        )

        for image_id, image_url, seed in mock_images:
            _create_image_record(
                session=session,
                entity=entity,
                generation_id=generation_id,
                image_id=image_id,
                storage_path=None,
                filename=f"{image_id}.png",
                seed=seed,
                image_url=image_url,
            )

            images_result.append(
                ImageResult(
                    id=image_id,
                    image_url=image_url,
                    seed=seed,
                    width=settings.image_width,
                    height=settings.image_height,
                    generation_ms=0,
                )
            )

    elif settings.image_backend == "comfyui":
        generation_id, images_result = _generate_comfyui_images(
            session=session,
            username=username,
            entity=entity,
            content_id=content_id,
            auto_prompt=auto_prompt,
            final_prompt=final_prompt,
            batch_size=batch_size,
            category=content.category.value,
            seed_base=effective_seed_base,
        )

    else:
        raise ValueError(
            f"Backend '{settings.image_backend}' no soportado. "
            "Usar: 'mock' o 'comfyui'"
        )

    db_commit(session, f"generate_images({entity.id})")

    return GenerateImagesResponse(
        generation_id=generation_id,
        auto_prompt=auto_prompt,
        final_prompt=final_prompt,
        batch_size=batch_size,
        backend=settings.image_backend,
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
    """
    Marca o desmarca una imagen como compartida públicamente.

    Raises:
        NoContextAvailableError: Si la imagen no existe o no pertenece a la entidad
    """
    record = session.exec(
        select(ImageRecord).where(
            ImageRecord.id == image_id,
            ImageRecord.generation_id == generation_id,
            ImageRecord.entity_id == entity.id,
            ImageRecord.is_deleted.is_(False),
        )
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
            ImageRecord.is_deleted.is_(False),
        )
    ).first()

    if not record:
        raise NoContextAvailableError

    record.is_shared = False
    record.is_deleted = True
    record.deleted_at = datetime.now(timezone.utc)

    # Bugfix: storage_path puede ser None en imágenes mock aunque el backend cambie
    if settings.image_backend != "mock" and record.storage_path:
        full_path = Path(settings.media_root) / record.storage_path
        # L-3: evitar TOCTOU usando try/except en lugar de if exists()
        if full_path:
            try:
                full_path.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass

    db_commit(session, f"delete_image({image_id})")


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
            ImageGeneration.is_deleted.is_(False),
        )
    ).first()

    if not generation:
        raise NoContextAvailableError

    records = session.exec(
        select(ImageRecord).where(
            ImageRecord.generation_id == generation_id,
            ImageRecord.is_deleted.is_(False),
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
        batch_size=generation.batch_size,
        backend=generation.backend,
        images=images,
    )


def list_generations_service(
    session: Session,
    entity: Entity,
) -> tuple[list, int]:
    """
    Lista todas las generaciones de imágenes de una entidad.

    Returns:
        (generations_list, total_count)
    """
    generations = session.exec(
        select(ImageGeneration)
        .where(
            ImageGeneration.entity_id == entity.id,
            ImageGeneration.collection_id == entity.collection_id,
            ImageGeneration.is_deleted.is_(False),
        )
        .order_by(ImageGeneration.created_at.desc())
    ).all()

    result = []
    for gen in generations:
        records = session.exec(
            select(ImageRecord)
            .where(
                ImageRecord.generation_id == gen.id,
                ImageRecord.is_deleted.is_(False),
            )
            .order_by(ImageRecord.seed.asc())
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
