from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File
from sqlmodel import Session

from app.core.valid_collection import get_collection_or_404, get_document_or_404
from app.database import get_session
from app.models.collections import Collection
from app.models.documents import Document, DocumentResponse, DocumentListResponse
from app.services.documents_service import (
    ingest_document_service,
    list_documents_service,
    delete_document_service,
)

router = APIRouter(prefix="/collections", tags=["documents"])


@router.post(
    "/{collection_id}/documents", response_model=DocumentResponse, status_code=201
)
async def ingest(
    collection_id: str,
    file: UploadFile = File(...),
    _: Collection = Depends(get_collection_or_404),
    session: Session = Depends(get_session),
):
    try:
        return await ingest_document_service(session, file, collection_id)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{collection_id}/documents", response_model=DocumentListResponse)
async def get_documents(
    collection_id: str,
    _: Collection = Depends(get_collection_or_404),
    session: Session = Depends(get_session),
):
    docs = list_documents_service(session, collection_id)
    return DocumentListResponse(data=docs, count=len(docs))


@router.get("/{collection_id}/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc: Document = Depends(get_document_or_404),
):
    return doc


@router.delete("/{collection_id}/documents/{doc_id}", status_code=204)
async def delete_document(
    doc: Document = Depends(get_document_or_404),
    session: Session = Depends(get_session),
):
    delete_document_service(session, doc)
    return Response(status_code=204)
