"""Servicio de consulta RAG con validación de entrada y salida."""

import logging

from app.core.metrics import cache_hits_total, cache_misses_total, rag_queries_total
from app.domain.content_guard import check_generated_output, check_prompt_length, check_user_input
from app.domain.llama_guard import check_with_llama_guard
from app.engine.rag import embed_query
from app.engine.rag_pipeline import invoke_rag_pipeline
from app.engine.semantic_cache import lookup, store

logger = logging.getLogger(__name__)


async def execute_rag_query(
    collection_id: str,
    query: str,
) -> tuple[str, int, list[str]]:
    """Valida y ejecuta una consulta RAG sobre una colección.

    Consulta el caché semántico antes de invocar el pipeline completo.

    Args:
        collection_id: ID de la colección sobre la que consultar.
        query: Consulta saneada del usuario (stripped).

    Returns:
        Tupla (answer, sources_count, source_doc_ids).
        sources_count=0 y source_doc_ids=[] indican respuesta servida desde caché.

    Raises:
        ContentNotAllowedError: si el prompt viola las reglas de moderación.
        GeneratedContentBlockedError: si la respuesta generada viola las reglas.
        NoContextAvailableError: si no hay documentos indexados.
        RuntimeError: si el motor LLM/pipeline falla.

    """
    check_prompt_length(query)
    check_user_input(query)

    query_vec = embed_query(query)

    cached = lookup(collection_id, query_vec)
    if cached is not None:
        logger.info("Serving RAG response from semantic cache for collection %s", collection_id)
        cache_hits_total.inc()
        rag_queries_total.labels(status="success").inc()
        return cached, 0, []

    cache_misses_total.inc()
    logger.info("Executing RAG query for collection %s, query: '%.50s'", collection_id, query)
    try:
        answer, sources_count, source_doc_ids = await invoke_rag_pipeline(
            collection_id=collection_id,
            query=query,
        )
    except Exception:
        rag_queries_total.labels(status="error").inc()
        raise
    check_generated_output(answer)
    await check_with_llama_guard(query, answer)

    store(collection_id, query_vec, answer)
    rag_queries_total.labels(status="success").inc()
    logger.info("RAG query returned %d context chunks", sources_count)
    return answer, sources_count, source_doc_ids
