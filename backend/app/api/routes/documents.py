from fastapi import APIRouter, HTTPException, UploadFile, File
import uuid
from app.services.documents_db_mock import documents

router = APIRouter()


@router.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    if not file.filename.endswith((".txt", "pdf")):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    doc_id = str(uuid.uuid4())
    # content = await file.read()
    documents[doc_id] = {
        "filename": file.filename,
    }

    return {"message": f"Documento '{file.filename}' ingestado con ID: {doc_id}"}
