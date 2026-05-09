from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.db.document import DocumentStatus


class DocumentResponse(BaseModel):
    id: str
    collection_id: str
    filename: str
    file_type: str
    chunk_count: int
    status: DocumentStatus
    processing_error: Optional[str] = None
    created_at: datetime
