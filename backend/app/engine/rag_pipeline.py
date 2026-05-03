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

_llm_instruction_by_category = {
    ContentCategory.extended_description: (
        "Del siguiente texto que describe rasgos físicos y apariencia de una entidad, "
        "extrae solo los descriptores visuales (color, forma, textura, material, detalles distintivos). "
        "Formato: lista de adjetivos y sustantivos separados por coma. "
        "Máximo 15 palabras. Ignora narrativa, motivaciones o emociones."
    ),
    ContentCategory.backstory: (
        "Del siguiente texto narrativo de trasfondo, extrae solo: "
        "- El lugar o entorno visual donde происходят los eventos formativos "
        "- Rasgos físicos del personaje en esa época si se mencionan "
        "- Atmósfera o mood visual (oscuro, iluminado, peligroso, pacífico) "
        "Máximo 10 palabras visuales. Ignora nombres de personajes y eventos."
    ),
    ContentCategory.scene: (
        "De la siguiente escena o diálogo, extrae solo: "
        "- El setting visual (lugar, iluminación, tiempo) "
        "- Postura y acción de los personajes "
        "- Elementos visuales importantes en primer plano "
        "Máximo 12 palabras. Ignora diálogo y pensamientos."
    ),
    ContentCategory.chapter: (
        "Del siguiente capítulo, extrae solo la descripción visual de la escena de apertura: "
        "- Lugar y ambientación "
        "- Iluminación y atmósfera "
        "- Elementos visuales principales "
        "Máximo 10 palabras. Ignora desarrollo y cierre de la trama."
    ),
}

# Limits concurrent LLM calls to avoid overwhelming Ollama (local, single-threaded).
_llm_semaphore = threading.Semaphore(settings.max_concurrent_llm_calls)

# Plain chain for pre-rendered prompts used by invoke_generation_pipeline.
generation_chain = llm | StrOutputParser()


def _estimate_tokens(text: str) -> int:
    """~4 chars por token."""
    return max(0, len(text) // 4)


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Trunca a max_tokens preservando palabras completas."""
    if _estimate_tokens(text) <= max_tokens:
        return text
    words = text.split()
    result: list[str] = []
    for word in words:
        candidate = " ".join(result + [word])
        if _estimate_tokens(candidate) > max_tokens:
            break
        result.append(word)
    return " ".join(result)


def invoke_prompt_extraction_pipeline(
    content_text: str,
    category: ContentCategory,
    target_tokens: int = 75,
) -> str:
    """Usa el LLM para extraer descriptores visuales de un texto.

    Args:
        content_text: Texto del EntityContent confirmado
        category: Categoría del contenido (determina la instrucción)
        target_tokens: Límite de tokens para el resultado

    Returns:
        Descriptores visuales extraídos por el LLM

    Raises:
        RuntimeError: Si el LLM no está disponible
    """
    llm_instruction = _llm_instruction_by_category.get(
        category,
        _llm_instruction_by_category[ContentCategory.extended_description],
    )

    full_prompt = f"""{llm_instruction}

TEXTO A ANALIZAR:
---
{content_text}
---

Responde únicamente con la lista de descriptores, sin explicación."""

    logger.debug(
        "invoke_prompt_extraction_pipeline: category=%s target_tokens=%d text_len=%d",
        category,
        target_tokens,
        len(content_text),
    )

    try:
        with _llm_semaphore:
            result = generation_chain.invoke(full_prompt)
    except Exception as e:
        logger.error("LLM extraction failed: %s", e)
        raise RuntimeError("LLM service unavailable") from e

    if not result or not result.strip():
        logger.warning("LLM returned empty result for category %s", category)
        return ""

    truncated = _truncate_to_tokens(result.strip(), target_tokens)
    logger.info("Extracted %d tokens for category %s", _estimate_tokens(truncated), category)

    return truncated


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