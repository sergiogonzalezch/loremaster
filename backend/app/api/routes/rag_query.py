from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.deps import get_collection_or_404
from app.core.exceptions import (
    ContentNotAllowedError,
    GeneratedContentBlockedError,
    NoContextAvailableError,
)
from app.database import get_session
from app.models.collections import Collection
from app.services.moderation_service import log_moderation_event
from app.services.rag_query_service import execute_rag_query
from app.models.rag_query import RagQueryRequest, RagQueryResponse

router = APIRouter(prefix="/collections", tags=["rag-query"])


@router.post("/{collection_id}/query", response_model=RagQueryResponse)
def rag_query(
    request: RagQueryRequest,
    collection_id: str,
    _: Collection = Depends(get_collection_or_404),
    session: Session = Depends(get_session),
):
    try:
        return execute_rag_query(request.query, collection_id=collection_id)
    except ContentNotAllowedError as e:
        log_moderation_event(session, "input", e.snippet)
        raise HTTPException(status_code=422, detail=str(e))
    except NoContextAvailableError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except GeneratedContentBlockedError as e:
        log_moderation_event(session, "output", e.snippet)
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(
            status_code=503, detail="No fue posible generar el contenido solicitado."
        )
