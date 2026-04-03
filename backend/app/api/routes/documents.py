from fastapi import APIRouter, HTTPException, UploadFile, File
from app.services.documents_service import ingest_document_service

from app.services.documents_db_mock import documents

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/ingest/{collection_id}")
async def ingest(collection_id: str, request: UploadFile = File(...)):
    response = await ingest_document_service(request, collection_id)
    return {"response": response, "status": "success"}


@router.get("/{doc_id}/status")
async def get_document(doc_id: str):
    for col_doc in documents.values():
        if doc_id in col_doc:
            return {"doc_id": doc_id, "status": col_doc[doc_id]["status"]}
    raise HTTPException(status_code=404, detail="Document not found")


@router.get("/list")
async def get_documents():
    all_docs = []
    for col_doc in documents.values():
        all_docs.extend(col_doc.values())
    return all_docs


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    for col_doc in documents.values():
        if doc_id in col_doc:
            del col_doc[doc_id]
            return {"message": f"Document {doc_id} deleted successfully"}
    raise HTTPException(status_code=404, detail="Document not found")
