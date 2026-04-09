from app.services.documents_db_mock import documents, collections
from fastapi import HTTPException
from langchain_ollama import OllamaLLM
from config import settings
from langchain_core.prompts import PromptTemplate
from app.services import rag_engine

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


async def generate_response(query: str, collection_id: str = None):

    if not documents or not any(documents.values()):
        raise HTTPException(
            status_code=422,
            detail="No documents available to process the query.",
        )

    if collection_id:
        if collection_id not in collections:
            raise HTTPException(status_code=404, detail="Collection not found")
        col_docs = documents[collection_id]
    else:
        col_docs = None
        for _, docs in documents.items():
            if docs:
                col_docs = docs
                break

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
