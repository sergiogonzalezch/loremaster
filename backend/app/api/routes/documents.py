from fastapi import APIRouter, HTTPException, UploadFile, File

from app.models.documents import DocumentResponse, DocumentListResponse
from app.services.documents_service import (
    ingest_document_service,
    list_documents_service,
    get_document_service,
    delete_document_service,
)

router = APIRouter(prefix="/collections", tags=["documents"])


@router.post(
    "/{collection_id}/documents", response_model=DocumentResponse, status_code=201
)
async def ingest(collection_id: str, request: UploadFile = File(...)):
    doc = await ingest_document_service(request, collection_id)
    return doc


@router.get("/{collection_id}/documents", response_model=DocumentListResponse)
async def get_documents(collection_id: str):
    docs = list_documents_service(collection_id)
    if docs is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return DocumentListResponse(data=docs, count=len(docs))


@router.get("/{collection_id}/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(collection_id: str, doc_id: str):
    doc = get_document_service(collection_id, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{collection_id}/documents/{doc_id}", status_code=200)
async def delete_document(collection_id: str, doc_id: str):
    result = delete_document_service(collection_id, doc_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    if result is False:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": f"Document {doc_id} deleted successfully"}
