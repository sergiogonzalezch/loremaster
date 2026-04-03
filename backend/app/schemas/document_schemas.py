from pydantic import BaseModel
from typing import Literal

class IngestDocumentBase(BaseModel):
    doc_id : str
    status: Literal["success", "failed", "pending", "processing"]

class IngestResponse(IngestDocumentBase):
    filename: str
    message: str 
    size_bytes: int 

class DocumentStatusResponse(IngestDocumentBase):
    chunk_count: int | None = None

