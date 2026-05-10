import asyncio
import logging
import time
from typing import Annotated, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Response,
    UploadFile,
    File,
)
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select, func

from app.core.api.params import DateRangeParams, PaginationParams
from app.core.database.dependencies import get_collection_or_404, get_document_or_404
from app.core.auth.dependencies import get_current_user
from app.core.exceptions import (
    ContentNotAllowedError,
    DatabaseError,
    DocumentExtractionError,
    DocumentNotRetryableError,
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
    ingest_document_service,
    process_ingest_background,
    list_documents_service,
    retry_document_service,
    delete_document_service,
)
from app.services.moderation.moderation_service import log_moderation_event

router = APIRouter(prefix="/collections", tags=["documents"])


@router.post(
    "/{collection_id}/documents", response_model=DocumentResponse, status_code=202
)
async def ingest(
    collection_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    _: Collection = Depends(get_collection_or_404),
    __: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Ingesta un documento en la colección y dispara el procesamiento en segundo plano.

    El documento se registra en estado 'processing' y la indexación vectorial
    se ejecuta de forma asíncrona.
    """
    try:
        document, text = await ingest_document_service(session, file, collection_id)
    except UnsupportedFileTypeError:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    except MissingFilenameError:
        raise HTTPException(status_code=422, detail="Filename is required")
    except FileTooLargeError:
        raise HTTPException(status_code=400, detail="File too large")
    except ContentNotAllowedError as e:
        log_moderation_event(session, "document", e.snippet)
        raise HTTPException(status_code=422, detail=str(e))
    except DocumentExtractionError:
        raise HTTPException(
            status_code=422, detail="No se pudo extraer el texto del archivo."
        )
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Error interno del servidor.")
    background_tasks.add_task(process_ingest_background, session, document, text)
    return document


@router.get(
    "/{collection_id}/documents", response_model=PaginatedResponse[DocumentResponse]
)
def get_documents(
    collection_id: str,
    pagination: Annotated[PaginationParams, Depends()],
    dates: Annotated[DateRangeParams, Depends()],
    filename: Optional[str] = Query(default=None),
    file_type: Optional[str] = Query(default=None),
    status: Optional[DocumentStatus] = Query(default=None),
    _: Collection = Depends(get_collection_or_404),
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
    doc: Document = Depends(get_document_or_404),
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
    doc: Document = Depends(get_document_or_404),
    _: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Reinicia el procesamiento de un documento que falló."""
    try:
        document, text = retry_document_service(session, doc)
    except DocumentNotRetryableError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Error interno del servidor.")
    background_tasks.add_task(process_ingest_background, session, document, text)
    return document


@router.delete("/{collection_id}/documents/{doc_id}", status_code=204)
def delete_document(
    doc: Document = Depends(get_document_or_404),
    _: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Elimina un documento: vectores en Qdrant y soft-delete en BD."""
    try:
        delete_document_service(session, doc)
    except VectorStoreError:
        raise HTTPException(
            status_code=503, detail="El almacén de vectores no está disponible."
        )
    return Response(status_code=204)


@router.get("/{collection_id}/documents/events")
def document_events(
    collection_id: str,
    _: Collection = Depends(get_collection_or_404),
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
                    Document.is_deleted == False,
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
                logging.exception("Error in SSE document events")
                break

        yield f"data: done\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
