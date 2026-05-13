"""Rutas de documentos para ingestión, listado y eliminación."""

import logging
import time
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from app.core.api.params import DateRangeParams, PaginationParams
from app.core.auth.dependencies import get_current_user
from app.core.database.dependencies import (
    get_collection_or_404_owned,
    get_document_or_404_owned,
)
from app.core.exceptions import (
    ContentNotAllowedError,
    DatabaseError,
    DocumentExtractionError,
    DocumentNotRetryableError,
    DuplicateDocumentError,
    FileTooLargeError,
    MissingFilenameError,
    UnsupportedFileTypeError,
    VectorStoreError,
)
from app.database import get_session
from app.models.db.collection import Collection
from app.models.db.document import Document, DocumentStatus
from app.models.schemas.document import DocumentResponse
from app.models.shared import PaginatedResponse
from app.services.document.documents_service import (
    delete_document_service,
    ingest_document_service,
    list_documents_service,
    process_ingest_background,
    retry_document_service,
)
from app.services.moderation.moderation_service import log_moderation_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collections", tags=["documents"])


@router.post(
    "/{collection_id}/documents", response_model=DocumentResponse, status_code=202,
)
async def ingest(
    collection_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    _: Collection = Depends(get_collection_or_404_owned),
    __: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Ingesta un documento en la colección y dispara el procesamiento en segundo plano.

    El documento se registra en estado 'processing' y la indexación vectorial
    se ejecuta de forma asíncrona.
    """
    try:
        document, text = await ingest_document_service(session, file, collection_id)
    except UnsupportedFileTypeError as e:
        raise HTTPException(status_code=400, detail="Unsupported file type") from e
    except MissingFilenameError as e:
        raise HTTPException(status_code=422, detail="Filename is required") from e
    except FileTooLargeError as e:
        raise HTTPException(status_code=400, detail="File too large") from e
    except ContentNotAllowedError as e:
        log_moderation_event(session, "document", e.snippet)
        raise HTTPException(status_code=422, detail=str(e)) from e
    except DocumentExtractionError as e:
        raise HTTPException(
            status_code=422, detail="No se pudo extraer el texto del archivo.",
        ) from e
    except DuplicateDocumentError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except DatabaseError as e:
        raise HTTPException(
            status_code=500, detail="Error interno del servidor.",
        ) from e
    background_tasks.add_task(process_ingest_background, session, document, text)
    return document


@router.get(
    "/{collection_id}/documents", response_model=PaginatedResponse[DocumentResponse],
)
def get_documents(
    collection_id: str,
    pagination: Annotated[PaginationParams, Depends()],
    dates: Annotated[DateRangeParams, Depends()],
    filename: str | None = Query(default=None),
    file_type: str | None = Query(default=None),
    status: DocumentStatus | None = Query(default=None),
    _: Collection = Depends(get_collection_or_404_owned),
    __: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Lista los documentos de una colección con filtros y paginación.

    Excluye documentos en estado 'processing'.
    """
    if status == DocumentStatus.processing:
        raise HTTPException(
            status_code=422,
            detail="Los documentos en estado 'processing' no son visibles en el listado.",
        )
    docs, total = list_documents_service(
        session,
        collection_id,
        pagination.page,
        pagination.page_size,
        filename=filename,
        file_type=file_type,
        status=status,
        created_after=dates.created_after,
        created_before=dates.created_before,
        order=pagination.order,
    )
    return PaginatedResponse.build(docs, total, pagination.page, pagination.page_size)


@router.get("/{collection_id}/documents/{doc_id}", response_model=DocumentResponse)
def get_document(
    doc: Document = Depends(get_document_or_404_owned),
    _: dict = Depends(get_current_user),
):
    """Obtiene los datos de un documento específico."""
    return doc


@router.post(
    "/{collection_id}/documents/{doc_id}/retry",
    response_model=DocumentResponse,
    status_code=202,
)
async def retry_ingest(
    background_tasks: BackgroundTasks,
    doc: Document = Depends(get_document_or_404_owned),
    _: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Reinicia el procesamiento de un documento que falló."""
    try:
        document, text = retry_document_service(session, doc)
    except DocumentNotRetryableError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except DatabaseError as e:
        raise HTTPException(
            status_code=500, detail="Error interno del servidor.",
        ) from e
    background_tasks.add_task(process_ingest_background, session, document, text)
    return document


@router.delete("/{collection_id}/documents/{doc_id}", status_code=204)
def delete_document(
    doc: Document = Depends(get_document_or_404_owned),
    _: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Elimina un documento: vectores en Qdrant y soft-delete en BD."""
    try:
        delete_document_service(session, doc)
    except VectorStoreError as e:
        raise HTTPException(
            status_code=503, detail="El almacén de vectores no está disponible.",
        ) from e
    return Response(status_code=204)


@router.get("/{collection_id}/documents/events")
def document_events(
    collection_id: str,
    _: Collection = Depends(get_collection_or_404_owned),
    __: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Stream de eventos SSE para notificaciones de cambio de estado de documentos.

    Emite 'processing' mientras haya documentos en procesamiento,
    y 'completed' cuando todos terminen (exitosamente o con error).
    El cliente debe reconnectar tras recibir 'completed'.
    """

    def event_stream():
        seen_processing: dict[str, DocumentStatus] = {}
        check_interval = 2

        while True:
            time.sleep(check_interval)

            try:
                stmt = select(Document).where(
                    Document.collection_id == collection_id,
                    Document.is_deleted.is_(False),
                )
                docs = session.exec(stmt).all()

                current_processing = {
                    d.id: d.status
                    for d in docs
                    if d.status == DocumentStatus.processing
                }

                if current_processing != seen_processing:
                    seen_processing.clear()
                    seen_processing.update(current_processing)

                    event_data = "completed" if not current_processing else "processing"
                    yield f"data: {event_data}\n\n"

                    if not current_processing:
                        break

                if not docs:
                    break

            except Exception:
                logger.exception("Error in SSE document events")
                break

        yield "data: done\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
