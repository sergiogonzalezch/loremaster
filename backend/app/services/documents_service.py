import logging
from datetime import datetime
from typing import Literal, Optional

from fastapi import UploadFile
from sqlalchemy import func
from sqlmodel import Session, select

from app.core.exceptions import (
    ContentNotAllowedError,
    DatabaseError,
    DocumentExtractionError,
    FileTooLargeError,
    MissingFilenameError,
    UnsupportedFileTypeError,
)
from app.models.documents import Document, DocumentStatus
from app.core.common import soft_delete
from app.domain.content_guard import check_document_content
from app.engine.extractor import extract_text
from app.engine.rag import ingest_chunks, delete_document_chunks

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = ["text/plain", "application/pdf"]
MAX_BYTES = 50 * 1024 * 1024


async def ingest_document_service(
    session: Session,
    data: UploadFile,
    collection_id: str,
) -> tuple[Document, str]:
    """Fast path: validate, read bytes, extract text, create DB record with
    status=processing. Returns (document, text) for process_ingest_background."""
    if data.content_type not in ALLOWED_MIME_TYPES:
        raise UnsupportedFileTypeError()
    if not data.filename or not data.filename.strip():
        raise MissingFilenameError()

    content_bytes = await data.read()
    if len(content_bytes) > MAX_BYTES:
        raise FileTooLargeError()

    logger.info(
        "Ingesting document '%s' into collection %s", data.filename, collection_id
    )
    try:
        content = extract_text(content_bytes, data.content_type)
    except Exception as e:
        logger.error("Text extraction failed for '%s': %s", data.filename, e)
        raise DocumentExtractionError() from e
    check_document_content(content)

    document = Document(
        collection_id=collection_id,
        filename=data.filename,
        file_type=data.content_type,
        chunk_count=0,
        status=DocumentStatus.processing,
    )
    session.add(document)
    try:
        session.commit()
        session.refresh(document)
    except Exception as e:
        session.rollback()
        logger.error(
            "DB commit failed during document ingest for '%s': %s", data.filename, e
        )
        raise DatabaseError() from e
    return document, content


def process_ingest_background(session: Session, document: Document, text: str) -> None:
    """Slow path: run ingest_chunks and update document status to completed/failed.
    Executed as a BackgroundTask after the 202 response is sent to the client."""
    try:
        chunk_count = ingest_chunks(
            doc_id=document.id,
            collection_id=document.collection_id,
            text=text,
        )
        document.status = DocumentStatus.completed
        document.chunk_count = chunk_count
    except Exception as e:
        logger.error("Background ingest failed for '%s': %s", document.filename, e)
        document.status = DocumentStatus.failed
    session.add(document)
    session.commit()
    logger.info("Document %s finished with status=%s", document.id, document.status)


def list_documents_service(
    session: Session,
    collection_id: str,
    page: int = 1,
    page_size: int = 20,
    filename: Optional[str] = None,
    file_type: Optional[str] = None,
    status: Optional[DocumentStatus] = None,
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None,
    order: Literal["asc", "desc"] = "desc",
) -> tuple[list[Document], int]:
    conditions = [
        Document.collection_id == collection_id,
        Document.is_deleted == False,
        Document.status != DocumentStatus.processing,
    ]
    if filename:
        conditions.append(Document.filename.ilike(f"%{filename}%"))
    if file_type:
        conditions.append(Document.file_type == file_type)
    if status:
        conditions.append(Document.status == status)
    if created_after:
        conditions.append(Document.created_at >= created_after)
    if created_before:
        conditions.append(Document.created_at <= created_before)

    total = session.exec(
        select(func.count()).select_from(select(Document).where(*conditions).subquery())
    ).one()
    sort_col = (
        Document.created_at.asc() if order == "asc" else Document.created_at.desc()
    )
    skip = (page - 1) * page_size
    items = session.exec(
        select(Document)
        .where(*conditions)
        .order_by(sort_col)
        .offset(skip)
        .limit(page_size)
    ).all()
    return list(items), total


def delete_document_service(session: Session, document: Document) -> bool:
    try:
        delete_document_chunks(document.collection_id, document.id)
    except Exception as e:
        logger.error("Failed to delete vector chunks for doc %s: %s", document.id, e)
        raise RuntimeError("Vector store unavailable") from e

    soft_delete(session, document)
    session.commit()
    logger.info(
        "Document %s soft-deleted from collection %s",
        document.id,
        document.collection_id,
    )
    return True
