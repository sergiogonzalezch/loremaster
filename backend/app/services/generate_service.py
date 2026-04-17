import logging

from app.models.generate import GenerateTextResponse
from app.core.rag_generate import generate_rag_response

logger = logging.getLogger(__name__)


def text_generation_service(query: str, collection_id: str) -> GenerateTextResponse:
    logger.info(
        "Generating text for collection %s, query: '%.50s'", collection_id, query
    )
    answer, sources_count = generate_rag_response(
        collection_id=collection_id,
        query=query,
    )
    logger.info("Generated response using %d context chunks", sources_count)
    return GenerateTextResponse(
        query=query,
        answer=answer,
        sources_count=sources_count,
    )
