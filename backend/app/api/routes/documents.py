from datetime import datetime
from typing import Literal, Optional

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

from app.core.deps import get_collection_or_404, get_document_or_404
from app.core.exceptions import (
    ContentNotAllowedError,
    DatabaseError,
    DocumentExtractionError,
    FileTooLargeError,
    MissingFilenameError,
    UnsupportedFileTypeError,
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
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    filename: Optional[str] = Query(default=None),
    file_type: Optional[str] = Query(default=None),
    status: Optional[DocumentStatus] = Query(default=None),
    created_after: Optional[datetime] = Query(default=None),
    created_before: Optional[datetime] = Query(default=None),
    order: Literal["asc", "desc"] = Query(default="desc"),
    _: Collection = Depends(get_collection_or_404),
    session: Session = Depends(get_session),
):
    docs, total = list_documents_service(
        session,
        collection_id,
        page,
        page_size,
        filename=filename,
        file_type=file_type,
        status=status,
        created_after=created_after,
        created_before=created_before,
        order=order,
    )
    return PaginatedResponse.build(docs, total, page, page_size)


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
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return Response(status_code=204)
