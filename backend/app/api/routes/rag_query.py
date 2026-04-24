from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import get_collection_or_404
from app.models.collections import Collection
from app.services.rag_query_service import execute_rag_query
from app.models.rag_query import RagQueryRequest, RagQueryResponse

router = APIRouter(prefix="/collections", tags=["rag-query"])


@router.post("/{collection_id}/query", response_model=RagQueryResponse)
async def rag_query(
    request: RagQueryRequest,
    collection_id: str,
    _: Collection = Depends(get_collection_or_404),
):
    try:
        return execute_rag_query(request.query, collection_id=collection_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))