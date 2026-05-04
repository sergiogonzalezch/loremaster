import logging
import threading

from langchain_core.output_parsers import StrOutputParser

from app.core.exceptions import NoContextAvailableError
from app.domain.prompt_templates import render_prompt
from app.engine.llm import chain, llm
from app.engine.rag import search_context
from app.core.config import settings
from app.models.enums import ContentCategory

logger = logging.getLogger(__name__)

_llm_semaphore = threading.Semaphore(settings.max_concurrent_llm_calls)

generation_chain = llm | StrOutputParser()


def _retrieve_context(
    collection_id: str,
    query: str,
    extra_context: str = "",
) -> tuple[str, int]:
    """Search Qdrant, merge extra_context, return (context_str, num_chunks).

    Raises:
        RuntimeError: If Qdrant is unavailable.
        NoContextAvailableError: If no context is found from any source.
    """
    try:
        context_chunks = search_context(
            collection_id=collection_id,
            query=query,
            top_k=settings.top_k,
            score_threshold=settings.rag_score_threshold,
        )
    except Exception as e:
        logger.error("Qdrant search failed for collection %s: %s", collection_id, e)
        raise RuntimeError("Vector search unavailable") from e

    rag_context = "\n\n---\n\n".join(context_chunks) if context_chunks else ""
    parts = [p for p in (extra_context, rag_context) if p]
    context = "\n\n---\n\n".join(parts)

    if not context.strip():
        raise NoContextAvailableError()

    return context, len(context_chunks)


def invoke_rag_pipeline(
    collection_id: str,
    query: str,
    extra_context: str = "",
) -> tuple[str, int]:
    """Search RAG context, build prompt, invoke LLM, return (answer, num_chunks).

    Raises:
        RuntimeError: If Qdrant or the LLM is unavailable.
        NoContextAvailableError: If there is no context at all (no chunks and no extra_context).
    """
    logger.debug(
        "invoke_rag_pipeline: collection=%s threshold=%.2f top_k=%d query='%.80s'",
        collection_id,
        settings.rag_score_threshold,
        settings.top_k,
        query,
    )

    context, num_chunks = _retrieve_context(collection_id, query, extra_context)

    try:
        with _llm_semaphore:
            answer = chain.invoke({"context": context, "query": query})
    except Exception as e:
        logger.error("LLM generation failed for collection %s: %s", collection_id, e)
        raise RuntimeError("LLM service unavailable") from e

    logger.info(
        "RAG response generated for collection %s using %d chunk(s)",
        collection_id,
        num_chunks,
    )
    return answer, num_chunks


def invoke_generation_pipeline(
    collection_id: str,
    entity_name: str,
    entity_type: str,
    category: ContentCategory,
    query: str,
    extra_context: str = "",
) -> tuple[str, int]:
    """Entity-aware RAG pipeline using category-specific prompt templates.

    Raises:
        RuntimeError: If Qdrant or the LLM is unavailable.
        NoContextAvailableError: If there is no context at all (no chunks and no extra_context).
    """
    logger.debug(
        "invoke_generation_pipeline: collection=%s entity='%s' category=%s threshold=%.2f top_k=%d query='%.80s'",
        collection_id,
        entity_name,
        category,
        settings.rag_score_threshold,
        settings.top_k,
        query,
    )

    context, num_chunks = _retrieve_context(collection_id, query, extra_context)

    rendered_prompt = render_prompt(
        category=category,
        entity_name=entity_name,
        entity_type=entity_type,
        context=context,
        query=query,
    )

    try:
        with _llm_semaphore:
            answer = generation_chain.invoke(rendered_prompt)
    except Exception as e:
        logger.error(
            "LLM generation failed for entity '%s' collection %s: %s",
            entity_name,
            collection_id,
            e,
        )
        raise RuntimeError("LLM service unavailable") from e

    logger.info(
        "Generation pipeline completed for entity '%s' (category=%s) using %d chunk(s)",
        entity_name,
        category,
        num_chunks,
    )
    return answer, num_chunks
