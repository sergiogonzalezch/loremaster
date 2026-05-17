"""Rutas de consulta RAG sobre documentos de una colección."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.database.dependencies import get_collection_or_404_owned
from app.core.exceptions import (
    ContentNotAllowedError,
    GeneratedContentBlockedError,
    NoContextAvailableError,
)
from app.database import get_session
from app.domain.content_guard import check_generated_output, check_prompt_length, check_user_input
from app.engine.rag_pipeline import invoke_rag_pipeline
from app.models.db.collection import Collection
from app.models.schemas.rag_query import RagQueryRequest, RagQueryResponse
from app.services.moderation.moderation_service import log_moderation_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collections", tags=["rag-query"])


@router.post("/{collection_id}/query", response_model=RagQueryResponse)
def rag_query(
    request: RagQueryRequest,
    collection_id: str,
    _: Annotated[Collection, Depends(get_collection_or_404_owned)],
    session: Annotated[Session, Depends(get_session)],
):
    """Ejecuta una consulta RAG sobre los documentos de la colección.

    Busca fragmentos similares, construye un prompt con contexto y devuelve
    la respuesta generada por el LLM.
    """
    try:
        query = request.query.strip()
        check_prompt_length(query)
        check_user_input(query)

        logger.info(
            "Executing RAG query for collection %s, query: '%.50s'",
            collection_id,
            query,
        )
        answer, sources_count, source_doc_ids = invoke_rag_pipeline(
            collection_id=collection_id,
            query=query,
        )
        check_generated_output(answer)
        logger.info("RAG query returned %d context chunks", sources_count)
        return RagQueryResponse(
            query=query,
            answer=answer,
            sources_count=sources_count,
            source_doc_ids=source_doc_ids,
        )
    except ContentNotAllowedError as e:
        log_moderation_event(session, "input", e.snippet)
        raise HTTPException(status_code=422, detail=str(e)) from e
    except NoContextAvailableError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except GeneratedContentBlockedError as e:
        log_moderation_event(session, "output", e.snippet)
        raise HTTPException(status_code=422, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail="No fue posible generar el contenido solicitado.",
        ) from e
