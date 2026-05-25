"""Rutas de consulta RAG sobre documentos de una colección."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.database.dependencies import get_collection_or_404_owned
from app.core.exceptions import (
    ContentNotAllowedError,
    GeneratedContentBlockedError,
    LLMBusyError,
    NoContextAvailableError,
)
from app.database import get_session
from app.models.db.collection import Collection
from app.models.schemas.rag_query import RagQueryRequest, RagQueryResponse
from app.services.collection.rag_query_service import execute_rag_query
from app.services.moderation.moderation_service import log_moderation_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collections", tags=["rag-query"])


@router.post("/{collection_id}/query", response_model=RagQueryResponse)
async def rag_query(
    request: RagQueryRequest,
    collection_id: str,
    _: Annotated[Collection, Depends(get_collection_or_404_owned)],
    session: Annotated[Session, Depends(get_session)],
):
    """Ejecuta una consulta RAG sobre los documentos de la colección."""
    query = request.query.strip()
    try:
        answer, sources_count, source_doc_ids = await execute_rag_query(collection_id, query)
    except ContentNotAllowedError as e:
        log_moderation_event(
            session, "input", e.snippet,
            collection_id=collection_id, operation="query",
            pattern_matched=getattr(e, "pattern", None),
        )
        raise HTTPException(status_code=422, detail=str(e)) from e
    except NoContextAvailableError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except GeneratedContentBlockedError as e:
        log_moderation_event(
            session, "output", e.snippet,
            collection_id=collection_id, operation="query",
            pattern_matched=getattr(e, "pattern", None),
        )
        raise HTTPException(status_code=422, detail=str(e)) from e
    except LLMBusyError as e:
        raise HTTPException(
            status_code=429,
            headers={"Retry-After": "30"},
            detail=str(e),
        ) from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail="No fue posible generar el contenido solicitado.") from e
    return RagQueryResponse(query=query, answer=answer, sources_count=sources_count, source_doc_ids=source_doc_ids)
