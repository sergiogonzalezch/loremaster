from fastapi import APIRouter, HTTPException, UploadFile, File

from app.services.documents_service import (
    ingest_document_service,
    list_documents_service,
    get_document_service,
    delete_document_service,
)

router = APIRouter(prefix="/collections", tags=["documents"])


@router.post("/{collection_id}/documents")
async def ingest(collection_id: str, request: UploadFile = File(...)):
    doc = await ingest_document_service(request, collection_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Collection not found")

    return {"data": doc, "status": "success"}


@router.get("/{collection_id}/documents")
async def get_documents(collection_id: str):
    docs = list_documents_service(collection_id)

    if docs is None:
        raise HTTPException(status_code=404, detail="Collection not found")

    return {"data": docs, "count": len(docs)}


@router.get("/{collection_id}/documents/{doc_id}")
async def get_document(collection_id: str, doc_id: str):
    doc = get_document_service(collection_id, doc_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"data": doc}


@router.delete("/{collection_id}/documents/{doc_id}")
async def delete_document(collection_id: str, doc_id: str):
    result = delete_document_service(collection_id, doc_id)

    if result is None:
        raise HTTPException(status_code=404, detail="Collection not found")

    if result is False:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"message": f"Document {doc_id} deleted successfully"}