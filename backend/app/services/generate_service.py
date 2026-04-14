import logging

from fastapi import HTTPException
from sqlmodel import Session

from config import settings
from app.models.generate import GenerateTextResponse
from app.models.documents import Document
from app.core.common import list_active_by_collection
from app.core.rag_engine import search_context
from app.core.llm_client import get_chain

logger = logging.getLogger(__name__)


async def text_generation_service(
    session: Session, query: str, collection_id: str = None
):
    logger.info(
        "Generating text for collection %s, query: '%.50s...'", collection_id, query
    )

    col_docs = list_active_by_collection(session, Document, collection_id)
    if not col_docs:
        raise HTTPException(
            status_code=422, detail="Collection has no ingested documents."
        )

    try:
        context_chunks = search_context(
            collection_id=collection_id,
            query=query,
            top_k=settings.top_k,
        )
    except Exception as e:
        logger.error("Qdrant search failed for collection %s: %s", collection_id, e)
        raise HTTPException(status_code=503, detail="Vector search service unavailable")

    if not context_chunks:
        raise HTTPException(
            status_code=422,
            detail="No relevant context found. Try ingesting documents first.",
        )

    context = "\n\n---\n\n".join(context_chunks)
    answer = get_chain().invoke({"context": context, "query": query})
    logger.info("Generated response using %d context chunks", len(context_chunks))

    return GenerateTextResponse(
        query=query,
        answer=answer,
        sources_count=len(context_chunks),
    )
