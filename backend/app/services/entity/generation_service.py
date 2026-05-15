"""Servicio de generación de contenido RAG para entidades."""

import logging

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.core.config import settings
from app.core.exceptions import (
    DatabaseError,
    InvalidCategoryError,
    PendingLimitExceededError,
)
from app.domain.category_rules import validate_category_for_entity
from app.domain.content_guard import check_generated_output, check_prompt_length, check_user_input
from app.engine.rag_pipeline import EntityContext, invoke_generation_pipeline
from app.models.db.entity import Entity
from app.models.db.entity_content import EntityContent
from app.models.db.generated_text import GeneratedText
from app.models.enums import ContentCategory, ContentStatus
from app.models.schemas.entity_content import EntityContentResponse

logger = logging.getLogger(__name__)


def generate(
    session: Session,
    entity: Entity,
    category: ContentCategory,
    query: str,
    model: str | None = None,
) -> EntityContentResponse:
    """Genera contenido RAG para una entidad mediante el pipeline LLM.

    Versión activa del servicio. Valida la entrada del usuario, verifica
    límites de contenidos pendientes, invoca el pipeline de generación con
    contexto vectorial, y crea un EntityContent en estado 'pending' junto
    con su GeneratedText. Realiza una doble verificación del límite después
    del flush para detectar inserciones concurrentes.

    Args:
        session: Sesión de base de datos activa.
        entity: Entidad destino para la que se genera el contenido.
        category: Categoría del contenido a generar.
        query: Consulta/prompt del usuario.
        model: Modelo Ollama a usar. Si es None usa el modelo por defecto del servidor.

    Returns:
        EntityContentResponse con el contenido generado y sus metadatos.

    Raises:
        InvalidCategoryError: Si la categoría no es válida para el tipo de entidad.
        PendingLimitExceededError: Si se alcanza el límite de contenidos pendientes.
        DatabaseError: Si falla el commit en base de datos.

    """
    query = query.strip()
    check_prompt_length(query)
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
            EntityContent.is_deleted.is_(False),
        ),
    ).one()
    if pending_count >= settings.max_pending_contents:
        msg = (
            f"La entidad ya tiene {pending_count} contenidos pendientes en la categoría '{category}' "
            f"(máximo {settings.max_pending_contents}). Confirma o descarta alguno antes de generar uno nuevo."
        )
        raise PendingLimitExceededError(
            msg,
        )

    extra_context = ""
    if entity.description:
        extra_context = f"Información actual de '{entity.name}' ({entity.type}):\n{entity.description}\n\n"

    answer, sources_count = invoke_generation_pipeline(
        collection_id=entity.collection_id,
        entity_ctx=EntityContext(
            name=entity.name,
            entity_type=entity.type.value,
            category=category,
        ),
        query=query,
        extra_context=extra_context,
        model=model,
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
        model_used=model or settings.ollama_model,
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
        session.flush()
        recount = session.exec(
            select(func.count())
            .select_from(EntityContent)
            .where(
                EntityContent.entity_id == entity.id,
                EntityContent.collection_id == entity.collection_id,
                EntityContent.category == category,
                EntityContent.status == ContentStatus.pending,
                EntityContent.is_deleted.is_(False),
            ),
        ).one()
        if recount > settings.max_pending_contents:
            session.rollback()
            msg = (
                f"La entidad ya tiene {recount - 1} contenidos pendientes en la categoría '{category}' "
                f"(máximo {settings.max_pending_contents}). Confirma o descarta alguno antes de generar uno nuevo."
            )
            raise PendingLimitExceededError(
                msg,
            )
        session.commit()
        session.refresh(content)
        session.refresh(generated_text)
    except SQLAlchemyError as e:
        session.rollback()
        logger.exception("DB commit failed after generation for entity %s", entity.id)
        raise DatabaseError from e

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
        generated_text_id=content.generated_text_id,
        category=content.category,
        content=content.content,
        raw_content=generated_text.raw_content,
        query=generated_text.query,
        sources_count=generated_text.sources_count,
        token_count=generated_text.token_count,
        model_used=generated_text.model_used,
        status=content.status,
        created_at=content.created_at,
        confirmed_at=content.confirmed_at,
        updated_at=content.updated_at,
    )
