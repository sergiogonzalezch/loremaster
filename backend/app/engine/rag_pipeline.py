"""Pipeline RAG para consultas y generación de contenido con contexto vectorial."""

import logging
import threading
from dataclasses import dataclass

import httpx
from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings
from app.domain.prompt_templates import render_prompt
from app.engine.llm import chain, llm
from app.engine.rag import retrieve_context
from app.models.enums import ContentCategory

logger = logging.getLogger(__name__)

_llm_semaphore = threading.Semaphore(settings.max_concurrent_llm_calls)

generation_chain = llm | StrOutputParser()

# Errores transitorios de red/transporte que indican un servicio caído (Qdrant, Ollama).
# Errores de programación (TypeError, ValueError de validación) deben burbujear sin capturar.
_TRANSPORT_ERRORS = (httpx.HTTPError, ConnectionError, OSError)


@dataclass
class EntityContext:
    name: str
    entity_type: str
    category: ContentCategory


def invoke_rag_pipeline(
    collection_id: str,
    query: str,
    extra_context: str = "",
) -> tuple[str, int]:
    """Ejecuta el pipeline RAG: busca contexto, construye prompt e invoca el LLM.

    Retorna una tupla (respuesta, num_chunks).

    Raises:
        RuntimeError: Si Qdrant o el LLM no están disponibles.
        NoContextAvailableError: Si no hay contexto ni chunks ni extra_context.

    """
    logger.debug(
        "invoke_rag_pipeline: collection=%s threshold=%.2f top_k=%d query='%.80s'",
        collection_id,
        settings.rag_score_threshold,
        settings.top_k,
        query,
    )

    try:
        context, num_chunks = retrieve_context(collection_id, query, extra_context)
    except _TRANSPORT_ERRORS as e:
        logger.exception("Vector store unavailable for collection %s", collection_id)
        raise RuntimeError("Vector store unavailable") from e

    try:
        with _llm_semaphore:
            answer = chain.invoke({"context": context, "query": query})
    except _TRANSPORT_ERRORS as e:
        logger.exception("LLM generation failed for collection %s", collection_id)
        raise RuntimeError("LLM service unavailable") from e

    logger.info(
        "RAG response generated for collection %s using %d chunk(s)",
        collection_id,
        num_chunks,
    )
    return answer, num_chunks


def invoke_generation_pipeline(
    collection_id: str,
    entity_ctx: EntityContext,
    query: str,
    extra_context: str = "",
) -> tuple[str, int]:
    """Pipeline RAG consciente de entidades usando plantillas de prompt específicas por categoría.

    Retorna una tupla (respuesta, num_chunks).

    Raises:
        RuntimeError: Si Qdrant o el LLM no están disponibles.
        NoContextAvailableError: Si no hay contexto ni chunks ni extra_context.

    """
    logger.debug(
        "invoke_generation_pipeline: collection=%s entity='%s' category=%s threshold=%.2f top_k=%d query='%.80s'",
        collection_id,
        entity_ctx.name,
        entity_ctx.category,
        settings.rag_score_threshold,
        settings.top_k,
        query,
    )

    try:
        context, num_chunks = retrieve_context(collection_id, query, extra_context)
    except _TRANSPORT_ERRORS as e:
        logger.exception("Vector store unavailable for collection %s", collection_id)
        raise RuntimeError("Vector store unavailable") from e

    rendered_prompt = render_prompt(
        category=entity_ctx.category,
        entity_name=entity_ctx.name,
        entity_type=entity_ctx.entity_type,
        context=context,
        query=query,
    )

    try:
        with _llm_semaphore:
            answer = generation_chain.invoke(rendered_prompt)
    except _TRANSPORT_ERRORS as e:
        logger.exception(
            "LLM generation failed for entity '%s' collection %s",
            entity_ctx.name,
            collection_id,
        )
        raise RuntimeError("LLM service unavailable") from e

    logger.info(
        "Generation pipeline completed for entity '%s' (category=%s) using %d chunk(s)",
        entity_ctx.name,
        entity_ctx.category,
        num_chunks,
    )
    return answer, num_chunks
