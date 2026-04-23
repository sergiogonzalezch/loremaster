import logging

from app.engine.rag import search_context
from app.engine.llm import chain
from app.core.config import settings

logger = logging.getLogger(__name__)


def invoke_rag_pipeline(
    collection_id: str,
    query: str,
    extra_context: str = "",
    top_k: int | None = None,
) -> tuple[str, int]:
    """Search RAG context, build prompt, invoke LLM, return (answer, num_chunks).

    Raises:
        RuntimeError: If Qdrant or the LLM is unavailable.
        ValueError: If there is no context at all (no chunks and no extra_context).
    """
    if top_k is None:
        top_k = settings.top_k

    try:
        context_chunks = search_context(
            collection_id=collection_id,
            query=query,
            top_k=top_k,
        )
    except Exception as e:
        logger.error("Qdrant search failed for collection %s: %s", collection_id, e)
        raise RuntimeError("Vector search unavailable") from e

    rag_context = "\n\n---\n\n".join(context_chunks) if context_chunks else ""
    parts = [p for p in (extra_context, rag_context) if p]
    context = "\n\n---\n\n".join(parts)

    if not context.strip():
        raise ValueError("No context available")

    try:
        answer = chain.invoke({"context": context, "query": query})
    except Exception as e:
        logger.error("LLM generation failed for collection %s: %s", collection_id, e)
        raise RuntimeError("LLM service unavailable") from e

    logger.info(
        "RAG response generated for collection %s using %d chunk(s)",
        collection_id,
        len(context_chunks),
    )
    return answer, len(context_chunks)