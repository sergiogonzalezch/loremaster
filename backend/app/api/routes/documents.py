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
from sqlmodel import Session

from app.core.query_params import DateRangeParams, PaginationParams
from app.core.deps import get_collection_or_404, get_document_or_404
from app.core.exceptions import (
    ContentNotAllowedError,
    DatabaseError,
    DocumentExtractionError,
    FileTooLargeError,
    MissingFilenameError,
    UnsupportedFileTypeError,
    VectorStoreError,
)
from app.database import get_session
from app.models.collections import Collection
from app.models.documents import Document, DocumentResponse, DocumentStatus
from app.models.shared import PaginatedResponse
from app.services.documents_service import (
    ingest_document_service,
    process_ingest_background,
    list_documents_service,
    delete_document_service,
)

router = APIRouter(prefix="/collections", tags=["documents"])


@router.post(
    "/{collection_id}/documents", response_model=DocumentResponse, status_code=202
)
async def ingest(
    collection_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    _: Collection = Depends(get_collection_or_404),
    session: Session = Depends(get_session),
):
    try:
        document, text = await ingest_document_service(session, file, collection_id)
    except UnsupportedFileTypeError:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    except MissingFilenameError:
        raise HTTPException(status_code=422, detail="Filename is required")
    except FileTooLargeError:
        raise HTTPException(status_code=400, detail="File too large")
    except ContentNotAllowedError as e:
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
    session: Session = Depends(get_session),
):
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
):
    return doc


@router.delete("/{collection_id}/documents/{doc_id}", status_code=204)
def delete_document(
    doc: Document = Depends(get_document_or_404),
    session: Session = Depends(get_session),
):
    try:
        delete_document_service(session, doc)
    except VectorStoreError:
        raise HTTPException(
            status_code=503, detail="El almacén de vectores no está disponible."
        )
    return Response(status_code=204)
