# backend/app/services/entity_draft_service.py

import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.entity_text_draft import EntityTextDraft, GenerateEntityTextDraftRequest
from app.models.entities import Entity
from app.core.rag_engine import search_context
from app.core.llm_client import get_chain
from app.core.common import get_active_by_id
from config import settings

logger = logging.getLogger(__name__)


async def generate_draft_service(
    session: Session,
    entity_id: str,
    collection_id: str,
    request: GenerateEntityTextDraftRequest,
) -> EntityTextDraft:
    # 1. Obtener entidad
    entity = get_active_by_id(session, Entity, entity_id, collection_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    # 2. Buscar contexto RAG
    try:
        context_chunks = search_context(
            collection_id=collection_id,
            query=request.query,
            top_k=settings.top_k,
        )
    except Exception as e:
        logger.error("Qdrant search failed: %s", e)
        raise HTTPException(status_code=503, detail="Vector search unavailable")

    # 3. Enriquecer contexto con descripción actual de la entidad
    entity_context = ""
    if entity.description:
        entity_context = (
            f"Información actual de '{entity.name}' ({entity.type}):\n"
            f"{entity.description}\n\n"
        )

    rag_context = "\n\n---\n\n".join(context_chunks) if context_chunks else ""
    context = entity_context + rag_context

    if not context.strip():
        raise HTTPException(
            status_code=422,
            detail="No context available. Ingest documents first.",
        )

    # 4. Generar texto con LLM
    try:
        answer = get_chain().invoke({"context": context, "query": request.query})
    except Exception as e:
        logger.error("LLM generation failed: %s", e)
        raise HTTPException(status_code=503, detail="LLM service unavailable")

    # 5. Guardar borrador
    draft = EntityTextDraft(
        entity_id=entity_id,
        collection_id=collection_id,
        query=request.query,
        content=answer,
        sources_count=len(context_chunks),
    )
    session.add(draft)
    session.commit()
    session.refresh(draft)
    logger.info("Draft %s created for entity %s", draft.id, entity_id)
    return draft


def list_drafts_service(
    session: Session,
    entity_id: str,
    collection_id: str,
) -> list[EntityTextDraft]:
    stmt = (
        select(EntityTextDraft)
        .where(
            EntityTextDraft.entity_id == entity_id,
            EntityTextDraft.collection_id == collection_id,
            EntityTextDraft.is_discarded == False,
        )
        .order_by(EntityTextDraft.created_at.desc())
    )
    return session.exec(stmt).all()


def update_draft_content_service(
    session: Session,
    draft_id: str,
    entity_id: str,
    content: str,
) -> EntityTextDraft | None:
    draft = _get_active_draft(session, draft_id, entity_id)
    if not draft:
        return None
    draft.content = content
    session.add(draft)
    session.commit()
    session.refresh(draft)
    return draft


def confirm_draft_service(
    session: Session,
    draft_id: str,
    entity_id: str,
    collection_id: str,
) -> Entity | None:
    draft = _get_active_draft(session, draft_id, entity_id)
    if not draft:
        return None

    # 1. Confirmar el borrador
    draft.is_confirmed = True
    draft.confirmed_at = datetime.now(timezone.utc)
    session.add(draft)

    # 2. Persistir en entity.description
    entity = get_active_by_id(session, Entity, entity_id, collection_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    entity.description = draft.content
    entity.updated_at = datetime.now(timezone.utc)
    session.add(entity)

    session.commit()
    session.refresh(entity)
    logger.info(
        "Draft %s confirmed → entity %s description updated", draft_id, entity_id
    )
    return entity


def discard_draft_service(
    session: Session,
    draft_id: str,
    entity_id: str,
) -> bool:
    draft = _get_active_draft(session, draft_id, entity_id)
    if not draft:
        return False
    draft.is_discarded = True
    session.add(draft)
    session.commit()
    logger.info("Draft %s discarded", draft_id)
    return True


def _get_active_draft(
    session: Session,
    draft_id: str,
    entity_id: str,
) -> EntityTextDraft | None:
    stmt = select(EntityTextDraft).where(
        EntityTextDraft.id == draft_id,
        EntityTextDraft.entity_id == entity_id,
        EntityTextDraft.is_discarded == False,
    )
    return session.exec(stmt).first()
