from fastapi import APIRouter, HTTPException, UploadFile, File
from app.services.documents_service import ingest_document_service
from app.services.documents_db_mock import documents, collections

router = APIRouter(prefix="/collections", tags=["documents"])


@router.post("/{collection_id}/documents")
async def ingest(collection_id: str, request: UploadFile = File(...)):
    doc = await ingest_document_service(request, collection_id)
    return {"data": doc, "status": "success"}


@router.get("/{collection_id}/documents")
async def get_documents(collection_id: str):
    if collection_id not in collections:
        raise HTTPException(status_code=404, detail="Collection not found")

    collection_docs = documents.get(collection_id, {})

    if not collection_docs:
        raise HTTPException(status_code=404, detail="No documents found")

    return {"data": list(collection_docs.values()), "count": len(collection_docs)}


@router.get("/{collection_id}/documents/{doc_id}")
async def get_document(collection_id: str, doc_id: str):
    if collection_id not in collections:
        raise HTTPException(status_code=404, detail="Collection not found")

    doc = documents.get(collection_id, {}).get(doc_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"data": doc}


@router.delete("/{collection_id}/documents/{doc_id}")
async def delete_document(collection_id: str, doc_id: str):
    if collection_id not in collections:
        raise HTTPException(status_code=404, detail="Collection not found")

    collection_docs = documents.get(collection_id, {})

    if doc_id not in collection_docs:
        raise HTTPException(status_code=404, detail="Document not found")

    del collection_docs[doc_id]

    return {"message": f"Document {doc_id} deleted successfully"}
