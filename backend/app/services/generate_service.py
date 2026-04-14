from fastapi import HTTPException
from config import settings
from app.models.generate import GenerateTextResponse
from app.services.rag_engine import search_context
from app.services.llm_client import get_chain
from app.services.documents_service import list_documents_service


async def text_generation_service(query: str, collection_id: str = None):

    col_docs = list_documents_service(collection_id)
    if not col_docs:
        raise HTTPException(
            status_code=422, detail="Collection has no ingested documents."
        )

    context_chunks = search_context(
        collection_id=collection_id,
        query=query,
        top_k=settings.top_k,
    )

    if not context_chunks:
        raise HTTPException(
            status_code=422,
            detail="No relevant context found. Try ingesting documents first.",
        )

    context = "\n\n---\n\n".join(context_chunks)

    answer = get_chain().invoke({"context": context, "query": query})

    return GenerateTextResponse(
        query=query,
        answer=answer,
        sources_count=len(context_chunks),
    )
