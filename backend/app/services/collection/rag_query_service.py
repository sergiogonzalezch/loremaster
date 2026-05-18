"""Servicio de consulta RAG con validación de entrada y salida."""

import logging

from app.domain.content_guard import check_generated_output, check_prompt_length, check_user_input
from app.engine.rag_pipeline import invoke_rag_pipeline

logger = logging.getLogger(__name__)


async def execute_rag_query(
    collection_id: str,
    query: str,
) -> tuple[str, int, list[str]]:
    """Valida y ejecuta una consulta RAG sobre una colección.

    Args:
        collection_id: ID de la colección sobre la que consultar.
        query: Consulta saneada del usuario (stripped).

    Returns:
        Tupla (answer, sources_count, source_doc_ids).

    Raises:
        ContentNotAllowedError: si el prompt viola las reglas de moderación.
        GeneratedContentBlockedError: si la respuesta generada viola las reglas.
        NoContextAvailableError: si no hay documentos indexados.
        RuntimeError: si el motor LLM/pipeline falla.

    """
    check_prompt_length(query)
    check_user_input(query)
    logger.info("Executing RAG query for collection %s, query: '%.50s'", collection_id, query)
    answer, sources_count, source_doc_ids = await invoke_rag_pipeline(
        collection_id=collection_id,
        query=query,
    )
    check_generated_output(answer)
    logger.info("RAG query returned %d context chunks", sources_count)
    return answer, sources_count, source_doc_ids
