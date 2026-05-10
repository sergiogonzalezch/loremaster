import asyncio
import hashlib
import logging
from datetime import datetime
from typing import Literal, Optional

from fastapi import UploadFile
from sqlalchemy import func
from sqlmodel import Session, select

from app.core.exceptions import (
    DocumentExtractionError,
    DocumentNotRetryableError,
    FileTooLargeError,
    MissingFilenameError,
    UnsupportedFileTypeError,
    VectorStoreError,
)
from app.core.config import settings
from app.models.db.document import Document, DocumentStatus
from app.core.database.utils import soft_delete, paginate_with_sort, db_commit
from app.core.storage.validator import FileValidator, DOCUMENT_MIME_TYPES
from app.domain.content_guard import check_document_content
from app.engine.extractor import extract_text
from app.engine.rag import ingest_chunks, delete_document_chunks

logger = logging.getLogger(__name__)

MAX_BYTES = 50 * 1024 * 1024
_EXTRACTION_TIMEOUT_SECONDS = 30


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
            max_bytes=MAX_BYTES,
        )
    except ValueError as e:
        msg = str(e)
        if "Tipo de archivo" in msg:
            raise UnsupportedFileTypeError()
        if "tamaño máximo" in msg:
            raise FileTooLargeError()
        raise

    if not data.filename or not data.filename.strip():
        raise MissingFilenameError()

    logger.info(
        "Ingesting document '%s' into collection %s", data.filename, collection_id
    )
    loop = asyncio.get_running_loop()
    try:
        extracted_text = await asyncio.wait_for(
            loop.run_in_executor(None, extract_text, content, data.content_type),
            timeout=_EXTRACTION_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.error("Text extraction timed out for '%s'", data.filename)
        raise DocumentExtractionError() from None
    except Exception as e:
        logger.error("Text extraction failed for '%s': %s", data.filename, e)
        raise DocumentExtractionError() from e
    check_document_content(extracted_text)

    content_hash = hashlib.sha256(extracted_text.encode()).hexdigest()
    if settings.environment != "test":
        existing = session.exec(
            select(Document).where(
                Document.collection_id == collection_id,
                Document.content_hash == content_hash,
                Document.is_deleted == False,
            )
        ).first()
        if existing:
            logger.warning(
                "Duplicate document detected in collection %s: '%s' (existing: %s)",
                collection_id,
                data.filename,
                existing.id,
            )
            from app.core.exceptions import DuplicateDocumentError
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
    db_commit(session, f"ingest_document({data.filename})")
    session.refresh(document)
    return document, extracted_text


def process_ingest_background(session: Session, document: Document, text: str) -> None:
    """Procesa la indexación vectorial de un documento en segundo plano.

    Divide el texto en chunks, los embeddea y los almacena en Qdrant.
    Actualiza el estado del documento a 'completed' o 'failed'.

    Args:
        session: Sesión de base de datos activa.
        document: Instancia del documento a indexar.
        text: Texto extraído del documento.
    """
    try:
        chunk_count = ingest_chunks(
            doc_id=document.id,
            collection_id=document.collection_id,
            text=text,
        )
        document.status = DocumentStatus.completed
        document.chunk_count = chunk_count
        document.processing_error = None
    except Exception as e:
        logger.error("Background ingest failed for '%s': %s", document.filename, e)
        document.status = DocumentStatus.failed
        document.processing_error = str(e)
    session.add(document)
    session.commit()
    logger.info("Document %s finished with status=%s", document.id, document.status)


def list_documents_service(
    session: Session,
    collection_id: str,
    page: int = 1,
    page_size: int = 20,
    filename: Optional[str] = None,
    file_type: Optional[str] = None,
    status: Optional[DocumentStatus] = None,
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None,
    order: Literal["asc", "desc"] = "desc",
) -> tuple[list[Document], int]:
    """Lista los documentos de una colección con paginación y filtros.

    Excluye automáticamente los documentos en estado 'processing'.

    Args:
        session: Sesión de base de datos activa.
        collection_id: Identificador de la colección.
        page: Número de página.
        page_size: Elementos por página.
        filename: Filtrar por nombre (búsqueda parcial).
        file_type: Filtrar por tipo/extension.
        status: Filtrar por estado de procesamiento.
        created_after: Filtrar por fecha de creación mínima.
        created_before: Filtrar por fecha de creación máxima.
        order: Orden ascendente o descendente.

    Returns:
        Tupla de (lista de documentos, total de resultados).
    """
    conditions = [
        Document.collection_id == collection_id,
        Document.is_deleted == False,
        Document.status != DocumentStatus.processing,
    ]
    if filename:
        conditions.append(Document.filename.ilike(f"%{filename}%"))
    if file_type:
        conditions.append(Document.file_type == file_type)
    if status:
        conditions.append(Document.status == status)
    if created_after:
        conditions.append(Document.created_at >= created_after)
    if created_before:
        conditions.append(Document.created_at <= created_before)

    return paginate_with_sort(
        session,
        Document,
        conditions,
        page=page,
        page_size=page_size,
        order_col=Document.created_at,
        order=order,
    )


def retry_document_service(
    session: Session, document: Document
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
        raise DocumentNotRetryableError()

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
        logger.error("Failed to delete vector chunks for doc %s: %s", document.id, e)
        raise VectorStoreError() from e

    soft_delete(session, document)
    db_commit(session, f"delete_document({document.id})")
    logger.info(
        "Document %s soft-deleted from collection %s",
        document.id,
        document.collection_id,
    )
    return True
