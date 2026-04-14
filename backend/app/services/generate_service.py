from fastapi import HTTPException
from langchain_ollama import OllamaLLM
from config import settings
from langchain_core.prompts import PromptTemplate
from app.services import rag_engine
from app.services.collection_service import collection_exists
from app.services.documents_service import list_documents_service

_llm = OllamaLLM(
    model=settings.ollama_model,
    temperature=settings.temperature,
    num_predict=settings.max_tokens,
)


_PROMPT = PromptTemplate.from_template(
    "Eres un asistente experto en narrativa y worldbuilding.\n"
    "Responde usando ÚNICAMENTE la información del contexto proporcionado.\n"
    "Si el contexto no contiene información suficiente, indícalo claramente.\n\n"
    "CONTEXTO:\n{context}\n\n"
    "PREGUNTA: {query}\n\n"
    "RESPUESTA:"
)

_chain = _PROMPT | _llm


async def text_generation_service(query: str, collection_id: str = None):

    if not collection_exists(collection_id):
        raise HTTPException(status_code=404, detail="Collection not found")

    col_docs = list_documents_service(collection_id)
    if not col_docs:
        raise HTTPException(
            status_code=422, detail="Collection has no ingested documents."
        )

    context_chunks = rag_engine.search_context(
        collection_id=collection_id,
        query=query,
        top_k=4,
    )

    if not context_chunks:
        raise HTTPException(
            status_code=422,
            detail="No relevant context found. Try ingesting documents first.",
        )

    context = "\n\n---\n\n".join(context_chunks)

    answer = _chain.invoke({"context": context, "query": query})

    return {
        "query": query,
        "answer": answer,
        "sources_count": len(context_chunks),
    }
