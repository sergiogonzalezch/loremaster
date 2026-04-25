import logging

from sqlalchemy import func
from sqlmodel import Session, select

from app.domain.category_rules import validate_category_for_entity
from app.domain.content_guard import check_generated_output, check_user_input
from app.engine.rag_pipeline import invoke_generation_pipeline
from app.models.entities import Entity
from app.models.entity_content import EntityContent
from app.models.enums import ContentCategory, ContentStatus

logger = logging.getLogger(__name__)

MAX_PENDING_CONTENTS = 5


class PendingLimitExceededError(Exception):
    pass


def generate(
    session: Session,
    entity: Entity,
    category: ContentCategory,
    query: str,
) -> EntityContent:
    query = query.strip()
    check_user_input(query)

    if not validate_category_for_entity(entity.type, category):
        raise ValueError(
            f"Category '{category}' is not valid for entity type '{entity.type}'."
        )

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
    if pending_count >= MAX_PENDING_CONTENTS:
        raise PendingLimitExceededError(
            f"La entidad ya tiene {pending_count} contenidos pendientes en la categoría '{category}' "
            f"(máximo {MAX_PENDING_CONTENTS}). Confirma o descarta alguno antes de generar uno nuevo."
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

    content = EntityContent(
        entity_id=entity.id,
        collection_id=entity.collection_id,
        category=category,
        query=query,
        sources_count=sources_count,
        content=answer,
        status=ContentStatus.pending,
    )
    session.add(content)
    session.commit()
    session.refresh(content)

    logger.info(
        "EntityContent %s (category=%s) created for entity %s",
        content.id,
        category,
        entity.id,
    )
    return content
