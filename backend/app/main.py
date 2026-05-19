"""Punto de entrada principal de la aplicación FastAPI.

Configura la aplicación, middleware CORS, manejador de excepciones,
servicio de archivos estáticos e incluye todos los routers de la API.
"""

import logging
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api.middlewares import RateLimitMiddleware, SecurityHeadersMiddleware
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
    media_router,
    metadata_router,
    models_router,
    public_router,
    rag_query_router,
    users_router,
)
from app.core.auth.csrf import validate_csrf
from app.core.config import settings
from app.core.lifespan import lifespan
from app.core.logging import configure_logging

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

if settings.environment == "local":
    logger.warning(
        "WARNING: Ejecutando en entorno 'local'. "
        "Guardas de seguridad relajadas (CSP, HTTPS, validaciones estrictas). "
        "Para produccion: definir ENVIRONMENT=production en .env.",
    )


def _csrf_for_unsafe(request: Request) -> None:
    """Valida CSRF solo para métodos mutantes (POST, PUT, PATCH, DELETE).

    Exime:
    - /api/v1/auth/*: el usuario aún no tiene sesión activa al hacer login/register.
    - Requests con Authorization Bearer: no usan cookies → CSRF no aplica.
    """
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        if request.url.path.startswith("/api/v1/auth/"):
            return
        if request.headers.get("authorization", "").lower().startswith("bearer "):
            return
        validate_csrf(request)


app = FastAPI(
    title=settings.project_name,
    version=settings.api_version,
    description="API for lore management and knowledge base",
    lifespan=lifespan,
    dependencies=[Depends(_csrf_for_unsafe)],
    docs_url=None if settings.environment == "production" else "/docs",
    redoc_url=None if settings.environment == "production" else "/redoc",
    openapi_url=None if settings.environment == "production" else "/openapi.json",
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Maneja excepciones no capturadas retornando error 500 genérico."""
    logger.error(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor."},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    _: RequestValidationError,
) -> JSONResponse:
    """Maneja errores de validación sin repetir el input del cliente (evita info leak)."""
    logger.warning("Validation error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=422,
        content={"detail": "Error de validación en la solicitud."},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
)

app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=settings.rate_limit_per_minute,
)
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
app.include_router(models_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(public_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(media_router, tags=["media"])
app.include_router(health_router)


def _custom_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema.setdefault("components", {}).setdefault("securitySchemes", {})["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "JWT obtenido del campo `access_token` en la respuesta de POST /auth/login (solo entorno local).",
    }
    # Apply BearerAuth to all operations except auth and health endpoints
    for path, path_item in schema.get("paths", {}).items():
        if path.startswith("/api/v1/auth/") or path in ("/health", "/"):
            continue
        for method, operation in path_item.items():
            if isinstance(operation, dict) and method != "parameters":
                operation.setdefault("security", [{"BearerAuth": []}])
    app.openapi_schema = schema
    return schema


if settings.environment != "production":
    app.openapi = _custom_openapi
