"""Modelo de base de datos para documentos subidos a colecciones."""

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, ForeignKey, String, Text
from sqlmodel import Field, SQLModel

from app.core.database.soft_delete import SoftDeleteMixin


class DocumentStatus(str, Enum):
    """Estados de procesamiento de un documento.

    Attributes:
        processing: Documento siendo extraído y chunkeado.
        completed: Documento procesado exitosamente e indexado en Qdrant.
        failed: Error durante el procesamiento.

    """

    processing = "processing"
    completed = "completed"
    failed = "failed"


class Document(SQLModel, SoftDeleteMixin, table=True):
    """Documento subido a una colección para indexación RAG.

    Attributes:
        id: Identificador único UUID.
        collection_id: Colección a la que pertenece.
        filename: Nombre original del archivo.
        file_type: Tipo MIME o extensión del archivo.
        content_hash: Hash del contenido para detección de duplicados.
        chunk_count: Número de chunks vectorizados.
        status: Estado actual del procesamiento.
        processing_error: Mensaje de error si el procesamiento falló.
        raw_text: Texto extraído completo (almacenado en BD).
        created_at: Fecha y hora de subida (UTC).

    """

    __tablename__ = "documents"

    id: str = Field(
        default_factory=lambda: str(__import__("uuid").uuid4()),
        primary_key=True,
        max_length=36,
    )
    collection_id: str = Field(
        sa_column=Column(
            String(36),
            ForeignKey("collections.id"),
            nullable=False,
            index=True,
        )
    )
    filename: str = Field(max_length=255)
    file_type: str = Field(max_length=100)
    content_hash: str | None = Field(default=None, max_length=64)
    chunk_count: int = Field(default=0)
    status: DocumentStatus = Field(default=DocumentStatus.processing, max_length=50)
    processing_error: str | None = Field(
        sa_column=Column(Text, nullable=True), default=None
    )
    raw_text: str | None = Field(sa_column=Column(Text, nullable=True), default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
