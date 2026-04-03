from fastapi import HTTPException, UploadFile, File
import uuid
from app.services.documents_db_mock import documents

ALLOWED_MIME_TYPES = ["text/plain", "application/pdf"]
MAX_BYTES = 50 * 1024 * 1024  # 50 MB


async def ingest_document_service(
    data: UploadFile = File(...), collection_id: str = None
):

    if data.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    content_bytes = await data.read()

    if len(content_bytes) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="File too large")

    if collection_id not in documents:
        raise HTTPException(status_code=404, detail="Collection not found")

    content = content_bytes.decode("utf-8", errors="ignore")
    doc_id = str(uuid.uuid4())

    documents[collection_id][doc_id] = {
        "filename": data.filename,
        "content": content,
        "status": "completed",
    }

    return doc_id