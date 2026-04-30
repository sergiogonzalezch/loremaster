# app/services/image_generation_service.py

import uuid as _uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.core.config import settings
from app.core.exceptions import (
    DatabaseError,
    ContentNotConfirmedError
)
from app.domain.content_guard import check_generated_output
from app.domain.prompt_builder import build_visual_prompt
from app.models.entities import Entity
from app.models.entity_content import EntityContent
from app.models.enums import ContentStatus
from app.models.image_generation import ImageRecord, GenerateImageResponse


def generate_image_service(
    session: Session,
    entity: Entity,
    content_id: str,
) -> GenerateImageResponse:
    """
    Genera un preview de imagen para un EntityContent confirmado.

    Flujo:
    1. Verificar que content_id pertenece a esta entidad y está confirmed
    2. Guardrail sobre el contenido
    3. build_visual_prompt() con estrategia por categoría (Opción C)
    4. [MOCK] Generar URL placeholder — aquí irá ComfyUI en Opción B
    5. Persistir ImageRecord con metadatos
    6. Retornar response

    # [OPTION_B] Cuando se integre ComfyUI:
    # - Reemplazar el bloque MOCK con invoke_comfy_pipeline(visual_prompt, seed)
    # - La función retornará image_bytes
    # - Guardar image_bytes en MEDIA_ROOT/{collection_id}/{entity_id}/{id}.png
    # - Actualizar image_path e image_url en el ImageRecord
    """

    # 1. Resolver contenido confirmado
    content = session.exec(
        select(EntityContent).where(
            EntityContent.id == content_id,
            EntityContent.entity_id == entity.id,
            EntityContent.collection_id == entity.collection_id,
            EntityContent.status == ContentStatus.confirmed,
            EntityContent.is_deleted == False,
        )
    ).first()

    if not content:
        raise ContentNotConfirmedError()

    # 2. Guardrail
    if content.content:
        # check_user_input(content.content[:500])
        check_generated_output(content.content[:500])

    # 3. Construir prompt visual
    build_result = build_visual_prompt(
        entity_type=entity.type,
        entity_name=entity.name,
        entity_description=entity.description,
        confirmed_content=content.content,
        category=content.category,
        max_tokens=settings.image_prompt_max_tokens,
        target_tokens=settings.image_prompt_target_tokens,
    )

    # 4. [MOCK] — reemplazar con ComfyUI en Opción B
    # [OPTION_B] image_bytes = await invoke_comfy_pipeline(
    #     prompt=build_result["prompt"],
    #     seed=seed,
    #     width=1024,
    #     height=1024,
    # )
    image_id = str(_uuid.uuid4())
    seed = 42

    placeholder_url = (
        f"https://placehold.co/1024x1024/1a1a2e/9d6fe8"
        f"?text={entity.name.replace(' ', '+')}"
    )

    # Ruta relativa donde se guardaría la imagen real
    # [OPTION_B] Aquí se guardaría image_bytes en esta ruta
    relative_path = f"{entity.collection_id}/{entity.id}/{image_id}.png"
    filename = f"{image_id}.png"

    # 5. Persistir registro
    record = ImageRecord(
        id=image_id,
        entity_id=entity.id,
        collection_id=entity.collection_id,
        content_id=content_id,
        category=content.category.value,
        visual_prompt=build_result["prompt"],
        prompt_token_count=build_result["token_count"],
        prompt_source=build_result["source"],
        prompt_strategy=build_result["strategy"],
        truncated=build_result["truncated"],
        image_path=relative_path,
        image_url=placeholder_url,  # [OPTION_B] será la URL real de S3/local
        filename=filename,
        extension="png",
        width=1024,
        height=1024,
        backend=settings.image_backend,
        seed=seed,
        generation_ms=0,  # [OPTION_B] medir tiempo real
        status="pending",
    )

    session.add(record)
    try:
        session.commit()
        session.refresh(record)
    except SQLAlchemyError as e:
        session.rollback()
        raise DatabaseError() from e

    return GenerateImageResponse(
        id=record.id,
        entity_id=record.entity_id,
        collection_id=record.collection_id,
        content_id=record.content_id,
        category=record.category,
        visual_prompt=record.visual_prompt,
        prompt_token_count=record.prompt_token_count,
        prompt_source=record.prompt_source,
        prompt_strategy=record.prompt_strategy,
        truncated=record.truncated,
        image_url=record.image_url,
        image_path=record.image_path,
        filename=record.filename,
        extension=record.extension,
        width=record.width,
        height=record.height,
        backend=record.backend,
        seed=record.seed,
        generation_ms=record.generation_ms,
        status=record.status,
        created_at=record.created_at,
        confirmed_at=record.confirmed_at,
        updated_at=record.updated_at,
    )
