import logging

from fastapi import HTTPException
from sqlmodel import Session

from app.models.generate import GenerateTextResponse
from app.core.rag_generate import generate_rag_response

logger = logging.getLogger(__name__)


def text_generation_service(session: Session, query: str, collection_id: str):
    logger.info(
        "Generating text for collection %s, query: '%.50s'", collection_id, query
    )

    try:
        answer, sources_count = generate_rag_response(
            collection_id=collection_id,
            query=query,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    logger.info("Generated response using %d context chunks", sources_count)

    return GenerateTextResponse(
        query=query,
        answer=answer,
        sources_count=sources_count,
    )
