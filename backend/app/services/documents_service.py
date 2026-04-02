from fastapi import HTTPException, UploadFile, File
import uuid
from app.services.documents_db_mock import documents

ALLOWED_MIME_TYPES = ["text/plain", "application/pdf"]
MAX_BYTES = 50 * 1024 * 1024  # 50 MB


def ingest_document_result(data: UploadFile = File(...)):
    if data.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    if len(data.file.read()) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds limit")

    doc_id = str(uuid.uuid4())
    content =  data.file.read().decode("utf-8", errors="ignore")
    documents[doc_id] = {
        "filename": data.filename,
        "content": content
    }

    print("Documents:", documents)

    return {
        f"Documento '{data.filename}' ingestado con ID: {doc_id}, con contenido: {content} "
    }
