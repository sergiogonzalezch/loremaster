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

# Limits concurrent LLM calls to avoid overwhelming Ollama (local, single-threaded).
_llm_semaphore = threading.Semaphore(settings.max_concurrent_llm_calls)

# Plain chain for pre-rendered prompts used by invoke_generation_pipeline.
generation_chain = llm | StrOutputParser()


def invoke_rag_pipeline(
    collection_id: str,
    query: str,
    extra_context: str = "",
    top_k: int | None = None,
    score_threshold: float | None = None,
) -> tuple[str, int]:
    """Search RAG context, build prompt, invoke LLM, return (answer, num_chunks).

    Raises:
        RuntimeError: If Qdrant or the LLM is unavailable.
        NoContextAvailableError: If there is no context at all (no chunks and no extra_context).
    """
    if top_k is None:
        top_k = settings.top_k
    if score_threshold is None:
        score_threshold = settings.rag_score_threshold

    try:
        context_chunks = search_context(
            collection_id=collection_id,
            query=query,
            top_k=top_k,
            score_threshold=score_threshold,
        )
    except Exception as e:
        logger.error("Qdrant search failed for collection %s: %s", collection_id, e)
        raise RuntimeError("Vector search unavailable") from e

    rag_context = "\n\n---\n\n".join(context_chunks) if context_chunks else ""
    parts = [p for p in (extra_context, rag_context) if p]
    context = "\n\n---\n\n".join(parts)

    if not context.strip():
        raise NoContextAvailableError()

    try:
        with _llm_semaphore:
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


def invoke_generation_pipeline(
    collection_id: str,
    entity_name: str,
    entity_type: str,
    category: ContentCategory,
    query: str,
    extra_context: str = "",
    top_k: int | None = None,
    score_threshold: float | None = None,
) -> tuple[str, int]:
    """Entity-aware RAG pipeline using category-specific prompt templates.

    Raises:
        RuntimeError: If Qdrant or the LLM is unavailable.
        NoContextAvailableError: If there is no context at all (no chunks and no extra_context).
    """
    if top_k is None:
        top_k = settings.top_k
    if score_threshold is None:
        score_threshold = settings.rag_score_threshold

    try:
        context_chunks = search_context(
            collection_id=collection_id,
            query=query,
            top_k=top_k,
            score_threshold=score_threshold,
        )
    except Exception as e:
        logger.error("Qdrant search failed for collection %s: %s", collection_id, e)
        raise RuntimeError("Vector search unavailable") from e

    rag_context = "\n\n---\n\n".join(context_chunks) if context_chunks else ""
    parts = [p for p in (extra_context, rag_context) if p]
    context = "\n\n---\n\n".join(parts)

    if not context.strip():
        raise NoContextAvailableError()

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
        len(context_chunks),
    )
    return answer, len(context_chunks)
