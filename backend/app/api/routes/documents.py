from fastapi import APIRouter, HTTPException, UploadFile, File
import uuid
from app.services.documents_service import ingest_document_result

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/ingest")
async def ingest(request: UploadFile = File(...)):
    response = ingest_document_result(request)
    return {"response": response, "status": "success"}
