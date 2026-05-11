"""Punto de entrada principal de la aplicación FastAPI.

Configura la aplicación, middleware CORS, manejador de excepciones,
servicio de archivos estáticos e incluye todos los routers de la API.
"""

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
    health_router,
    image_router,
    metadata_router,
    public_router,
    rag_query_router,
    users_router,
)
from app.api.routes.media import router as media_router
from app.api.middlewares import RateLimitMiddleware, SecurityHeadersMiddleware

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.project_name,
    version=settings.api_version,
    description="API for lore management and knowledge base",
    lifespan=lifespan,
    docs_url=None if settings.environment == "production" else "/docs",
    redoc_url=None if settings.environment == "production" else "/redoc",
    openapi_url=None if settings.environment == "production" else "/openapi.json",
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Maneja excepciones no capturadas retornando error 500 genérico."""
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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Maneja errores de validación sin repetir el input del cliente (evita info leak)."""
    logger.warning("Validation error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=422, content={"detail": "Error de validación en la solicitud."}
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.rate_limit_per_minute)
app.add_middleware(SecurityHeadersMiddleware)


@app.get("/")
def read_root():
    """Retorna información básica del servicio."""
    return {"service": settings.project_name, "version": settings.api_version}


_media_dir = Path(settings.media_root)
_media_dir.mkdir(parents=True, exist_ok=True)

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
app.include_router(media_router, tags=["media"])
app.include_router(health_router)
