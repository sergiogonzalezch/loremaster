import logging

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.auth import verify_api_key
from app.core.config import settings
from app.core.exceptions import (
    DraftNotEditableError,
    DraftNotFoundError,
    DraftNotPendingError,
    DuplicateNameError,
    FileTooLargeError,
    FilenameRequiredError,
    MaxPendingDraftsError,
    UnsupportedFileTypeError,
)
from app.core.lifespan import lifespan
from app.api.routes import generate, documents, collections, entities, entity_text_draft

logging.basicConfig(level=logging.INFO)

_AUTH_DEP = [Depends(verify_api_key)]
_MAX_UPLOAD_BYTES = 50 * 1024 * 1024 + 65_536  # 50 MB + multipart envelope


class _LimitUploadSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: callable) -> Response:
        if request.method in ("POST", "PUT", "PATCH"):
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > _MAX_UPLOAD_BYTES:
                return Response("Request too large", status_code=413)
        return await call_next(request)


app = FastAPI(
    title=settings.project_name,
    version=settings.api_version,
    description="API for managing lore and knowledge base",
    lifespan=lifespan,
)

app.add_middleware(_LimitUploadSizeMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DuplicateNameError)
async def _duplicate_name_handler(request: Request, exc: DuplicateNameError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(MaxPendingDraftsError)
async def _max_drafts_handler(request: Request, exc: MaxPendingDraftsError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(UnsupportedFileTypeError)
async def _unsupported_file_handler(request: Request, exc: UnsupportedFileTypeError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(FileTooLargeError)
async def _file_too_large_handler(request: Request, exc: FileTooLargeError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(FilenameRequiredError)
async def _filename_required_handler(request: Request, exc: FilenameRequiredError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(DraftNotFoundError)
async def _draft_not_found_handler(request: Request, exc: DraftNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(DraftNotEditableError)
async def _draft_not_editable_handler(request: Request, exc: DraftNotEditableError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(DraftNotPendingError)
async def _draft_not_pending_handler(request: Request, exc: DraftNotPendingError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.get("/")
def read_root():
    return {"service": settings.project_name, "version": settings.api_version}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


app.include_router(collections.router, prefix="/api/v1", dependencies=_AUTH_DEP)
app.include_router(documents.router, prefix="/api/v1", dependencies=_AUTH_DEP)
app.include_router(generate.router, prefix="/api/v1", dependencies=_AUTH_DEP)
app.include_router(entities.router, prefix="/api/v1", dependencies=_AUTH_DEP)
app.include_router(entity_text_draft.router, prefix="/api/v1", dependencies=_AUTH_DEP)