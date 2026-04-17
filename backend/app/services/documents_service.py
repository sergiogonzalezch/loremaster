import logging

from fastapi import HTTPException, UploadFile
from sqlmodel import Session, select

from app.models.documents import Document, DocumentStatus
from app.core.common import get_active_by_id, soft_delete
from app.core.text_extractor import extract_text
from app.core.rag_engine import ingest_chunks, delete_document_chunks

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = ["text/plain", "application/pdf"]
MAX_BYTES = 50 * 1024 * 1024


async def ingest_document_service(
    session: Session,
    data: UploadFile,
    collection_id: str,
) -> Document:
    if data.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    if not data.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    content_bytes = await data.read()
    if len(content_bytes) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="File too large")

    logger.info(
        "Ingesting document '%s' into collection %s", data.filename, collection_id
    )
    content = extract_text(content_bytes, data.content_type)

    document = Document(
        collection_id=collection_id,
        filename=data.filename,
        file_type=data.content_type,
        chunk_count=0,
        status=DocumentStatus.processing,
    )
    session.add(document)
    session.commit()
    session.refresh(document)

    try:
        chunk_count = ingest_chunks(
            doc_id=document.id,
            collection_id=collection_id,
            text=content,
        )
    except Exception as e:
        logger.error("Ingestion failed for '%s': %s", data.filename, e)
        document.status = DocumentStatus.failed
        session.add(document)
        session.commit()
        raise HTTPException(
            status_code=502,
            detail=f"Failed to ingest document into vector store: {e}",
        )

    document.status = DocumentStatus.completed
    document.chunk_count = chunk_count
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


def list_documents_service(session: Session, collection_id: str) -> list[Document]:
    stmt = select(Document).where(
        Document.collection_id == collection_id,
        Document.is_deleted == False,
        Document.status != DocumentStatus.processing,
    )
    return session.exec(stmt).all()


def get_document_service(
    session: Session, collection_id: str, doc_id: str
) -> Document | None:
    return get_active_by_id(session, Document, doc_id, collection_id)


def delete_document_service(session: Session, document: Document) -> bool:
    try:
        delete_document_chunks(document.collection_id, document.id)
    except Exception as e:
        logger.error("Failed to delete vector chunks for doc %s: %s", document.id, e)
    soft_delete(session, document)
    session.commit()
    logger.info(
        "Document %s soft-deleted from collection %s",
        document.id,
        document.collection_id,
    )
    return True
