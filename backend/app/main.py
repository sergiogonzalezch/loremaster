import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.lifespan import lifespan
from app.api.routes import (
    admin_router,
    auth_clerk_router,
    auth_router,
    collections_router,
    content_router,
    documents_router,
    entities_router,
    image_router,
    metadata_router,
    public_router,
    rag_query_router,
    users_router,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.project_name,
    version=settings.api_version,
    description="API for lore management and knowledge base",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500, content={"detail": "Error interno del servidor."}
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/")
def read_root():
    return {"service": settings.project_name, "version": settings.api_version}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


_media_dir = Path(settings.media_root)
_media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(_media_dir)), name="media")

app.include_router(auth_router, prefix="/api/v1")
app.include_router(auth_clerk_router, prefix="/api/v1")
app.include_router(collections_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(rag_query_router, prefix="/api/v1")
app.include_router(entities_router, prefix="/api/v1")
app.include_router(content_router, prefix="/api/v1")
app.include_router(image_router, prefix="/api/v1")
app.include_router(metadata_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(public_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
