"""Servicios de lógica de negocio para documentos."""

import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass

from fastapi import UploadFile
from sqlalchemy import Engine
from sqlmodel import Session, select

from app.core.api.params import DateRangeParams, PaginationParams
from app.core.config import settings
from app.core.database.soft_delete import soft_delete
from app.core.database.utils import db_commit, paginate_with_sort
from app.core.exceptions import (
    DocumentExtractionError,
    DocumentNotRetryableError,
    DuplicateDocumentError,
    FileTooLargeError,
    MissingFilenameError,
    UnsupportedFileTypeError,
    VectorStoreError,
)
from app.core.storage.validator import DOCUMENT_MIME_TYPES, FileValidator
from app.domain.content_guard import check_document_content
from app.engine.extractor import extract_text
from app.engine.rag import delete_document_chunks, ingest_chunks
from app.models.db.document import Document, DocumentStatus


@dataclass
class DocumentFilters:
    """Filtros opcionales para listar documentos."""

    filename: str | None = None
    file_type: str | None = None
    status: DocumentStatus | None = None


def _sanitize_for_log(filename: str) -> str:
    """Elimina caracteres de control (CR/LF) que permiten log injection."""
    return re.sub(r"[\r\n]", "", filename)


logger = logging.getLogger(__name__)


async def ingest_document_service(
    session: Session,
    data: UploadFile,
    collection_id: str,
) -> tuple[Document, str]:
    """Ingesta un documento en una colección: validación, extracción y registro.

    Valida tipo y tamaño del archivo, extrae el texto, lo almacena en la BD
    y retorna el documento para que el caller dispare la indexación en background.

    Args:
        session: Sesión de base de datos activa.
        data: Archivo subido por el usuario.
        collection_id: Colección destino.

    Returns:
        Tupla de (Documento creado, texto extraído).

    Raises:
        UnsupportedFileTypeError: Si el tipo de archivo no es soportado.
        FileTooLargeError: Si el archivo supera el límite.
        MissingFilenameError: Si el archivo no tiene nombre.
        DocumentExtractionError: Si falla la extracción de texto.

    """
    try:
        content = FileValidator.validate_document(
            data,
            allowed_types=DOCUMENT_MIME_TYPES,
            max_bytes=settings.document_max_upload_mb * 1024 * 1024,
        )
    except ValueError as e:
        msg = str(e)
        if "Tipo de archivo" in msg:
            raise UnsupportedFileTypeError from e
        if "tamaño máximo" in msg:
            raise FileTooLargeError from e
        raise

    if not data.filename or not data.filename.strip():
        raise MissingFilenameError
    if len(data.filename) > 255:
        raise MissingFilenameError

    logger.info(
        "Ingesting document '%s' into collection %s",
        _sanitize_for_log(data.filename),
        collection_id,
    )
    loop = asyncio.get_running_loop()
    try:
        extracted_text = await asyncio.wait_for(
            loop.run_in_executor(None, extract_text, content, data.content_type),
            timeout=settings.document_extraction_timeout_seconds,
        )
    except TimeoutError:
        logger.exception(
            "Text extraction timed out for '%s'",
            _sanitize_for_log(data.filename),
        )
        raise DocumentExtractionError from None
    except Exception as e:
        logger.exception(
            "Text extraction failed for '%s'",
            _sanitize_for_log(data.filename),
        )
        raise DocumentExtractionError from e
    check_document_content(extracted_text)

    content_hash = hashlib.sha256(extracted_text.encode()).hexdigest()
    if settings.environment != "test":
        existing = session.exec(
            select(Document).where(
                Document.collection_id == collection_id,
                Document.content_hash == content_hash,
                Document.is_deleted.is_(False),
            ),
        ).first()
        if existing:
            logger.warning(
                "Duplicate document detected in collection %s: '%s' (existing: %s)",
                collection_id,
                _sanitize_for_log(data.filename),
                existing.id,
            )
            raise DuplicateDocumentError(existing.id)

    document = Document(
        collection_id=collection_id,
        filename=data.filename,
        file_type=data.content_type,
        content_hash=content_hash,
        chunk_count=0,
        status=DocumentStatus.processing,
        raw_text=extracted_text,
    )
    session.add(document)
    db_commit(session, f"ingest_document({_sanitize_for_log(data.filename)})")
    session.refresh(document)
    return document, extracted_text


def process_ingest_background(engine: Engine, document_id: str, text: str) -> None:
    """Procesa la indexación vectorial de un documento en segundo plano.

    Abre una sesión propia para evitar compartir la sesión del request HTTP
    que ya puede haber cerrado al regresar 202 Accepted.

    Divide el texto en chunks, los embeddea y los almacena en Qdrant.
    Actualiza el estado del documento a 'completed' o 'failed'.

    Args:
        engine: Motor SQLAlchemy desde el que abrir la sesión.
        document_id: ID del documento a indexar.
        text: Texto extraído del documento.

    """
    with Session(engine) as session:
        document = session.get(Document, document_id)
        if not document:
            logger.error("Background ingest: document %s not found", document_id)
            return
        try:
            chunk_count = ingest_chunks(
                doc_id=document.id,
                collection_id=document.collection_id,
                text=text,
            )
            document.status = DocumentStatus.completed
            document.chunk_count = chunk_count
            document.processing_error = None
        except Exception as e:  # noqa: BLE001
            logger.exception(
                "Background ingest failed for '%s'",
                _sanitize_for_log(document.filename),
            )
            document.status = DocumentStatus.failed
            document.processing_error = str(e)
        session.add(document)
        db_commit(session, f"process_ingest_background({document.id})")
        logger.info("Document %s finished with status=%s", document.id, document.status)


def list_documents_service(
    session: Session,
    collection_id: str,
    pagination: PaginationParams,
    dates: DateRangeParams,
    filters: DocumentFilters | None = None,
) -> tuple[list[Document], int]:
    """Lista los documentos de una colección con paginación y filtros.

    Excluye automáticamente los documentos en estado 'processing'.

    Args:
        session: Sesión de base de datos activa.
        collection_id: Identificador de la colección.
        pagination: Parámetros de paginación y orden.
        dates: Rango de fechas de creación.
        filters: Filtros opcionales de dominio (filename, file_type, status).

    Returns:
        Tupla de (lista de documentos, total de resultados).

    """
    f = filters or DocumentFilters()
    conditions = [
        Document.collection_id == collection_id,
        Document.is_deleted.is_(False),
        Document.status != DocumentStatus.processing,
    ]
    if f.filename:
        conditions.append(Document.filename.ilike(f"%{f.filename}%"))
    if f.file_type:
        conditions.append(Document.file_type == f.file_type)
    if f.status:
        conditions.append(Document.status == f.status)
    if dates.created_after:
        conditions.append(Document.created_at >= dates.created_after)
    if dates.created_before:
        conditions.append(Document.created_at <= dates.created_before)

    return paginate_with_sort(
        session,
        Document,
        conditions,
        page=pagination.page,
        page_size=pagination.page_size,
        order_col=Document.created_at,
        order=pagination.order,
    )


def retry_document_service(
    session: Session,
    document: Document,
) -> tuple[Document, str]:
    """Reinicia el procesamiento de un documento que falló.

    Solo permite reintentar documentos en estado 'failed' con texto extraído.

    Args:
        session: Sesión de base de datos activa.
        document: Instancia del documento a reintentar.

    Returns:
        Tupla de (documento actualizado, texto a reprocesar).

    Raises:
        DocumentNotRetryableError: Si el documento no es reintentable.

    """
    if document.status != DocumentStatus.failed or not document.raw_text:
        raise DocumentNotRetryableError

    raw_text = document.raw_text
    document.status = DocumentStatus.processing
    document.processing_error = None
    session.add(document)
    db_commit(session, f"retry_document({document.id})")
    session.refresh(document)
    return document, raw_text


def delete_document_service(session: Session, document: Document) -> bool:
    """Elimina un documento: vectores en Qdrant y soft-delete en BD.

    Args:
        session: Sesión de base de datos activa.
        document: Instancia del documento a eliminar.

    Returns:
        True si la eliminación fue exitosa.

    Raises:
        VectorStoreError: Si falla la eliminación de vectores en Qdrant.

    """
    try:
        delete_document_chunks(document.collection_id, document.id)
    except Exception as e:
        logger.exception("Failed to delete vector chunks for doc %s", document.id)
        raise VectorStoreError from e

    soft_delete(session, document)
    logger.info(
        "Document %s soft-deleted from collection %s",
        document.id,
        document.collection_id,
    )
    return True
