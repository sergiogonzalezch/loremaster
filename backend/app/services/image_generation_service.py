# app/services/image_generation_service.py

from sqlmodel import Session, select

from app.core.config import settings
from app.core.exceptions import ContentNotAllowedError, NoContextAvailableError
from app.domain.content_guard import check_user_input
from app.domain.prompt_builder import build_visual_prompt
from app.models.entities import Entity
from app.models.entity_content import EntityContent
from app.models.enums import ContentStatus
from app.models.image_generation import GenerateImageResponse


def generate_image_service(
    session: Session,
    entity: Entity,
    content_id: str | None,
) -> GenerateImageResponse:

    # 1. Resolver el contenido narrativo base
    confirmed_content = ""
    resolved_content_id = content_id

    if content_id:
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
            raise NoContextAvailableError()

        confirmed_content = content.content
    else:
        # Buscar el confirmed más reciente de cualquier categoría
        latest = session.exec(
            select(EntityContent)
            .where(
                EntityContent.entity_id == entity.id,
                EntityContent.collection_id == entity.collection_id,
                EntityContent.status == ContentStatus.confirmed,
                EntityContent.is_deleted == False,
            )
            .order_by(EntityContent.confirmed_at.desc())
        ).first()

        if latest:
            confirmed_content = latest.content
            resolved_content_id = latest.id
        else:
            raise NoContextAvailableError()

    # 2. Guardrail sobre el contenido que se va a usar
    if confirmed_content:
        check_user_input(confirmed_content[:500])  # muestra representativa

    # 3. Construir prompt visual
    result = build_visual_prompt(
        entity_type=entity.type,
        entity_name=entity.name,
        entity_description=entity.description,
        confirmed_content=confirmed_content,
        max_tokens=settings.image_prompt_max_tokens,
        target_tokens=settings.image_prompt_target_tokens,
    )

    # 4. Mock: no llamar a ComfyUI todavía
    placeholder_url = (
        f"https://placehold.co/1024x1024/1a1a2e/9d6fe8"
        f"?text={entity.name.replace(' ', '+')}"
    )

    return GenerateImageResponse(
        image_url=placeholder_url,
        visual_prompt=result["prompt"],
        token_count=result["token_count"],
        truncated=result["truncated"],
        prompt_source=result["source"],
        seed=42,
        backend="mock",
        generation_ms=0,
        entity_id=entity.id,
        collection_id=entity.collection_id,
        content_id=resolved_content_id,
    )
