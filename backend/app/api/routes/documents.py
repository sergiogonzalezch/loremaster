from fastapi import APIRouter, HTTPException, UploadFile, File
import uuid
from app.services.documents_db_mock import documents
from app.schemas.models import IngestDocumentRequest

router = APIRouter()


@router.post("/ingest")
async def ingest(request: IngestDocumentRequest):
    if not request.filename.endswith((".txt", "pdf")):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    doc_id = str(uuid.uuid4())
    content = await request.content.read()
    documents[doc_id] = {
        "filename": request.filename,
        "content": content.decode("utf-8", errors="ignore"),
    }

    return {"message": f"Documento '{request.filename}' ingestado con ID: {doc_id}"}
