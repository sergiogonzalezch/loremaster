from app.services.documents_db_mock import documents, collections
from fastapi import HTTPException


async def generate_response(query: str, collection_id: str = None):

    if not documents or not any(documents.values()):
        raise HTTPException(
            status_code=422,
            detail="No documents available to process the query.",
        )

    if collection_id:
        if collection_id not in collections:
            raise HTTPException(status_code=404, detail="Collection not found")
        col_meta = collections[collection_id]
        col_docs = documents[collection_id]
    else:
        col_meta = None
        col_docs = None
        for cid, docs in documents.items():
            if docs:
                col_meta = collections[cid]
                col_docs = docs
                break

    if not col_docs:
        raise HTTPException(
            status_code=422, detail="Collection has no ingested documents."
        )

    return {
        "query": query,
        "sources": [{"filename": d["filename"]} for d in col_docs.values()],
        "message": f"Respuesta para '{query}' usando colección '{col_meta['name']}'",
    }
