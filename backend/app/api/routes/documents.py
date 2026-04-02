from fastapi import APIRouter, HTTPException, UploadFile, File
import uuid
from app.services.documents_db_mock import documents
from app.services.documents_service import ingest_document_result
# from app.schemas.models import IngestDocumentRequest

router = APIRouter()


@router.post("/ingest")
async def ingest(request: UploadFile = File(...)):
    # if not request.filename.endswith((".txt", "pdf")):
    #     raise HTTPException(status_code=400, detail="Unsupported file type")

    # doc_id = str(uuid.uuid4())
    # content = await request.read()
    # documents[doc_id] = {
    #     "filename": request.filename,
    #     "content": content.decode("utf-8", errors="ignore"),
    # }

    # return {f"Documento '{request.filename}' ingestado con ID: {doc_id}"}
    response = ingest_document_result(request)
    return {"message": response, "status": "success"}