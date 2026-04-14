import io
from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile, File
from pypdf import PdfReader
from sqlmodel import Session, select

from app.database import engine
from app.models.documents import Document, DocumentStatus
from app.services import rag_engine

ALLOWED_MIME_TYPES = ["text/plain", "application/pdf"]
MAX_BYTES = 50 * 1024 * 1024


def _extract_text(content_bytes: bytes, content_type: str) -> str:
    if content_type == "application/pdf":
        reader = PdfReader(io.BytesIO(content_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return content_bytes.decode("utf-8", errors="ignore")


async def ingest_document_service(
    data: UploadFile = File(...), collection_id: str = None
) -> Document:
    if data.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    if not data.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    content_bytes = await data.read()

    if len(content_bytes) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="File too large")

    content = _extract_text(content_bytes, data.content_type)

    with Session(engine) as session:
        document = Document(
            collection_id=collection_id,
            filename=data.filename,
            file_type=data.content_type,
            chunk_count=0,
            status=DocumentStatus.completed,
        )
        session.add(document)
        session.commit()
        session.refresh(document)

        try:
            chunk_count = rag_engine.ingest_chunks(
                doc_id=document.id,
                collection_id=collection_id,
                text=content,
            )
        except Exception as e:
            document.status = DocumentStatus.failed
            document.chunk_count = 0
            session.add(document)
            session.commit()
            raise HTTPException(
                status_code=502,
                detail=f"Failed to ingest document into vector store: {e}",
            )

        document.chunk_count = chunk_count
        session.add(document)
        session.commit()
        session.refresh(document)
        return document


def list_documents_service(collection_id: str) -> list[Document]:
    with Session(engine) as session:
        stmt = select(Document).where(
            Document.collection_id == collection_id,
            Document.is_deleted == False,
        )
        return session.exec(stmt).all()


def get_document_service(collection_id: str, doc_id: str) -> Document | None:
    with Session(engine) as session:
        stmt = select(Document).where(
            Document.id == doc_id,
            Document.collection_id == collection_id,
            Document.is_deleted == False,
        )
        return session.exec(stmt).first()


def delete_document_service(collection_id: str, doc_id: str):
    with Session(engine) as session:
        stmt = select(Document).where(
            Document.id == doc_id,
            Document.collection_id == collection_id,
            Document.is_deleted == False,
        )
        document = session.exec(stmt).first()
        if not document:
            return False
        rag_engine.delete_document_chunks(collection_id, doc_id)
        document.is_deleted = True
        document.deleted_at = datetime.now(timezone.utc)
        session.add(document)
        session.commit()
        return True
