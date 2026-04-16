from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File
from sqlmodel import Session

from app.core.valid_collection import get_valid_collection
from app.database import get_session
from app.models.collections import Collection
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
async def ingest(
    collection_id: str,
    file: UploadFile = File(...),
    collection: Collection = Depends(get_valid_collection),
    session: Session = Depends(get_session),
):
    return await ingest_document_service(session, file, collection_id)


@router.get("/{collection_id}/documents", response_model=DocumentListResponse)
async def get_documents(
    collection_id: str,
    collection: Collection = Depends(get_valid_collection),
    session: Session = Depends(get_session),
):
    docs = list_documents_service(session, collection_id)
    return DocumentListResponse(data=docs, count=len(docs))


@router.get("/{collection_id}/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    collection_id: str,
    doc_id: str,
    collection: Collection = Depends(get_valid_collection),
    session: Session = Depends(get_session),
):
    doc = get_document_service(session, collection_id, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{collection_id}/documents/{doc_id}", status_code=204)
async def delete_document(
    collection_id: str,
    doc_id: str,
    collection: Collection = Depends(get_valid_collection),
    session: Session = Depends(get_session),
):
    result = delete_document_service(session, collection_id, doc_id)
    if not result:
        raise HTTPException(status_code=404, detail="Document not found")
    return Response(status_code=204)
