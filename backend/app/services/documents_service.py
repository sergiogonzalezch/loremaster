from fastapi import HTTPException, UploadFile, File
import uuid
from app.services.documents_db_mock import documents


def ingest_document_result(data: UploadFile = File(...)):
    if not data.filename.endswith((".txt", "pdf")):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    doc_id = str(uuid.uuid4())
    content =  data.file.read().decode("utf-8", errors="ignore")
    documents[doc_id] = {
        "filename": data.filename,
        "content": content
    }

    # return {f"Documento '{data.filename}' ingestado con ID: {doc_id}"}

    print("Documents:", documents)

    return {
        f"Documento '{data.filename}' ingestado con ID: {doc_id}, con contenido: {content} "
    }
