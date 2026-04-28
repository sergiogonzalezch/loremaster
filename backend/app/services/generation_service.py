import logging

from sqlalchemy import func
from sqlmodel import Session, select

from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.exceptions import (
    DatabaseError,
    InvalidCategoryError,
    PendingLimitExceededError,
)
from app.domain.category_rules import validate_category_for_entity
from app.domain.content_guard import check_generated_output, check_user_input
from app.engine.rag_pipeline import invoke_generation_pipeline
from app.models.entities import Entity
from app.models.entity_content import EntityContent, EntityContentResponse
from app.models.generated_texts import GeneratedText
from app.models.enums import ContentCategory, ContentStatus

logger = logging.getLogger(__name__)


def generate(
    session: Session,
    entity: Entity,
    category: ContentCategory,
    query: str,
) -> EntityContentResponse:
    query = query.strip()
    check_user_input(query)

    if not validate_category_for_entity(entity.type, category):
        raise InvalidCategoryError(category.value, entity.type.value)

    pending_count = session.exec(
        select(func.count())
        .select_from(EntityContent)
        .where(
            EntityContent.entity_id == entity.id,
            EntityContent.collection_id == entity.collection_id,
            EntityContent.category == category,
            EntityContent.status == ContentStatus.pending,
            EntityContent.is_deleted == False,
        )
    ).one()
    if pending_count >= settings.max_pending_contents:
        raise PendingLimitExceededError(
            f"La entidad ya tiene {pending_count} contenidos pendientes en la categoría '{category}' "
            f"(máximo {settings.max_pending_contents}). Confirma o descarta alguno antes de generar uno nuevo."
        )

    extra_context = ""
    if entity.description:
        extra_context = (
            f"Información actual de '{entity.name}' ({entity.type}):\n"
            f"{entity.description}\n\n"
        )

    answer, sources_count = invoke_generation_pipeline(
        collection_id=entity.collection_id,
        entity_name=entity.name,
        entity_type=entity.type.value,
        category=category,
        query=query,
        extra_context=extra_context,
    )
    check_generated_output(answer)

    generated_text = GeneratedText(
        entity_id=entity.id,
        collection_id=entity.collection_id,
        category=category.value,
        query=query,
        raw_content=answer,
        sources_count=sources_count,
        token_count=max(1, len(answer) // 4),
    )
    session.add(generated_text)
    session.flush()

    content = EntityContent(
        entity_id=entity.id,
        collection_id=entity.collection_id,
        generated_text_id=generated_text.id,
        category=category,
        content=answer,
        status=ContentStatus.pending,
    )
    try:
        session.add(content)
        session.commit()
        session.refresh(content)
        session.refresh(generated_text)
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(
            "DB commit failed after generation for entity %s: %s", entity.id, e
        )
        raise DatabaseError() from e

    logger.info(
        "GeneratedText %s + EntityContent %s (category=%s) created for entity %s",
        generated_text.id,
        content.id,
        category,
        entity.id,
    )
    return EntityContentResponse(
        id=content.id,
        entity_id=content.entity_id,
        collection_id=content.collection_id,
        generated_text_id=generated_text.id,
        category=content.category,
        content=content.content,
        raw_content=generated_text.raw_content,
        query=generated_text.query,
        sources_count=generated_text.sources_count,
        token_count=generated_text.token_count,
        status=content.status,
        created_at=content.created_at,
        confirmed_at=content.confirmed_at,
        updated_at=content.updated_at,
    )