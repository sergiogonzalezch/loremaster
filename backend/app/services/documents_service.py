import io
import uuid

from fastapi import HTTPException, UploadFile, File
from pypdf import PdfReader

from app.services.documents_db_mock import documents, collections

ALLOWED_MIME_TYPES = ["text/plain", "application/pdf"]
MAX_BYTES = 50 * 1024 * 1024

def _extract_text(content_bytes: bytes, content_type: str) -> str:
    if content_type == "application/pdf":
        reader = PdfReader(io.BytesIO(content_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return content_bytes.decode("utf-8", errors="ignore")


async def ingest_document_service(
    data: UploadFile = File(...), collection_id: str = None
):
    if data.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    if not data.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    if collection_id not in collections:
        raise HTTPException(status_code=404, detail="Collection not found")

    content_bytes = await data.read()

    if len(content_bytes) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="File too large")

    content = _extract_text(content_bytes, data.content_type)
    doc_id = str(uuid.uuid4())

    if collection_id not in documents:
        documents[collection_id] = {}

    document = {
        "id": doc_id,
        "collection_id": collection_id,
        "filename": data.filename,
        "content": content,
        "status": "completed",
    }

    documents[collection_id][doc_id] = document
    return document


def list_documents_service(collection_id: str):
    if collection_id not in collections:
        return None
    return list(documents.get(collection_id, {}).values())


def get_document_service(collection_id: str, doc_id: str):
    if collection_id not in collections:
        return None
    return documents.get(collection_id, {}).get(doc_id)


def delete_document_service(collection_id: str, doc_id: str):
    if collection_id not in collections:
        return None
    collection_docs = documents.get(collection_id, {})
    if doc_id not in collection_docs:
        return False
    del collection_docs[doc_id]
    return True
