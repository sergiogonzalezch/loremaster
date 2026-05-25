"""Pipeline RAG para consultas y generación de contenido con contexto vectorial."""

import asyncio
import logging
from dataclasses import dataclass

import httpx
from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings
from app.core.exceptions import LLMBusyError
from app.domain.prompt_templates import render_prompt
from app.engine.llm import chain, get_llm
from app.engine.rag import ChunkInfo, retrieve_context
from app.models.enums import ContentCategory

logger = logging.getLogger(__name__)

# Semáforo async: la espera no bloquea el event loop ni consume un hilo del pool.
_llm_semaphore = asyncio.Semaphore(settings.max_concurrent_llm_calls)

# Cadena por defecto — usada cuando no se especifica modelo en la request
generation_chain = get_llm(settings.ollama_model) | StrOutputParser()

# Errores transitorios de red/transporte que indican un servicio caído (Qdrant, Ollama).
# Errores de programación (TypeError, ValueError de validación) deben burbujear sin capturar.
_TRANSPORT_ERRORS = (httpx.HTTPError, ConnectionError, OSError)


@dataclass
class EntityContext:
    """Contexto de entidad usado al generar contenido enriquecido."""

    name: str
    entity_type: str
    category: ContentCategory


async def invoke_rag_pipeline(
    collection_id: str,
    query: str,
    extra_context: str = "",
) -> tuple[str, int, list[str]]:
    """Ejecuta el pipeline RAG: busca contexto, construye prompt e invoca el LLM.

    Retorna (respuesta, num_chunks, source_doc_ids).

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
        context, num_chunks, source_doc_ids, _ = retrieve_context(collection_id, query, extra_context)
    except _TRANSPORT_ERRORS as e:
        logger.exception("Vector store unavailable for collection %s", collection_id)
        msg = "Vector store unavailable"
        raise RuntimeError(msg) from e

    if _llm_semaphore.locked():
        raise LLMBusyError()

    try:
        loop = asyncio.get_running_loop()
        async with _llm_semaphore:
            answer = await loop.run_in_executor(
                None, lambda: chain.invoke({"context": context, "query": query})
            )
    except _TRANSPORT_ERRORS as e:
        logger.exception("LLM generation failed for collection %s", collection_id)
        msg = "LLM service unavailable"
        raise RuntimeError(msg) from e

    logger.info(
        "RAG response generated for collection %s using %d chunk(s)",
        collection_id,
        num_chunks,
    )
    return answer, num_chunks, source_doc_ids


async def invoke_generation_pipeline(
    collection_id: str,
    entity_ctx: EntityContext,
    query: str,
    extra_context: str = "",
    model: str | None = None,
) -> tuple[str, list[ChunkInfo]]:
    """Pipeline RAG consciente de entidades usando plantillas de prompt específicas por categoría.

    Retorna (respuesta, chunks) donde chunks son los fragmentos RAG usados como contexto.

    Raises:
        RuntimeError: Si Qdrant o el LLM no están disponibles.
        NoContextAvailableError: Si no hay contexto ni chunks ni extra_context.

    """
    effective_model = model or settings.ollama_model
    logger.debug(
        "invoke_generation_pipeline: collection=%s entity='%s' category=%s model=%s threshold=%.2f top_k=%d query='%.80s'",
        collection_id,
        entity_ctx.name,
        entity_ctx.category,
        effective_model,
        settings.rag_score_threshold,
        settings.top_k,
        query,
    )

    try:
        context, num_chunks, _, chunks = retrieve_context(collection_id, query, extra_context)
    except _TRANSPORT_ERRORS as e:
        logger.exception("Vector store unavailable for collection %s", collection_id)
        msg = "Vector store unavailable"
        raise RuntimeError(msg) from e

    rendered_prompt = render_prompt(
        category=entity_ctx.category,
        entity_name=entity_ctx.name,
        entity_type=entity_ctx.entity_type,
        context=context,
        query=query,
    )

    active_chain = get_llm(effective_model) | StrOutputParser() if model else generation_chain

    if _llm_semaphore.locked():
        raise LLMBusyError()

    try:
        loop = asyncio.get_running_loop()
        async with _llm_semaphore:
            answer = await loop.run_in_executor(None, lambda: active_chain.invoke(rendered_prompt))
    except _TRANSPORT_ERRORS as e:
        logger.exception(
            "LLM generation failed for entity '%s' collection %s",
            entity_ctx.name,
            collection_id,
        )
        msg = "LLM service unavailable"
        raise RuntimeError(msg) from e

    logger.info(
        "Generation pipeline completed for entity '%s' (category=%s, model=%s) using %d chunk(s)",
        entity_ctx.name,
        entity_ctx.category,
        effective_model,
        num_chunks,
    )
    return answer, chunks
