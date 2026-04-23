from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, File
from sqlmodel import Session

from app.core.deps import get_collection_or_404, get_document_or_404
from app.database import get_session
from app.models.collections import Collection
from app.models.documents import Document, DocumentResponse, DocumentStatus
from app.models.shared import PaginatedResponse
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


@router.get("/{collection_id}/documents", response_model=PaginatedResponse[DocumentResponse])
async def get_documents(
    collection_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    filename: Optional[str] = Query(default=None),
    file_type: Optional[str] = Query(default=None),
    status: Optional[DocumentStatus] = Query(default=None),
    created_after: Optional[datetime] = Query(default=None),
    created_before: Optional[datetime] = Query(default=None),
    _: Collection = Depends(get_collection_or_404),
    session: Session = Depends(get_session),
):
    docs, total = list_documents_service(
        session, collection_id, page, page_size,
        filename=filename, file_type=file_type, status=status,
        created_after=created_after, created_before=created_before,
    )
    return PaginatedResponse.build(docs, total, page, page_size)


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
