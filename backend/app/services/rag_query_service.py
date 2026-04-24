import logging

from app.models.rag_query import RagQueryResponse
from app.engine.rag_pipeline import invoke_rag_pipeline

logger = logging.getLogger(__name__)


def execute_rag_query(query: str, collection_id: str) -> RagQueryResponse:
    logger.info(
        "Executing RAG query for collection %s, query: '%.50s'", collection_id, query
    )
    answer, sources_count = invoke_rag_pipeline(
        collection_id=collection_id,
        query=query,
    )
    logger.info("RAG query returned %d context chunks", sources_count)
    return RagQueryResponse(
        query=query,
        answer=answer,
        sources_count=sources_count,
    )
