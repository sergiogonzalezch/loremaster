from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.db.document import DocumentStatus


class DocumentResponse(BaseModel):
    """Respuesta con los datos de un documento.

    Attributes:
        id: Identificador único.
        collection_id: Colección a la que pertenece.
        filename: Nombre original del archivo.
        file_type: Tipo o extensión del archivo.
        chunk_count: Número de chunks indexados.
        status: Estado del procesamiento.
        processing_error: Mensaje de error, si falló.
        created_at: Fecha de subida.
    """

    id: str
    collection_id: str
    filename: str
    file_type: str
    chunk_count: int
    status: DocumentStatus
    processing_error: str | None = None
    created_at: datetime
