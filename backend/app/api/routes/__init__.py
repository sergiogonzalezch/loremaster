"""Re-exportación de todos los routers de la API."""

from app.api.routes.admin import admin_router
from app.api.routes.auth import auth_clerk_router, auth_router
from app.api.routes.collections import collections_router, rag_query_router
from app.api.routes.documents import documents_router
from app.api.routes.entities import content_router, entities_router
from app.api.routes.images import image_router
from app.api.routes.public import public_router
from app.api.routes.users import users_router
from app.api.routes.media import router as media_router
from app.api.routes.health import router as health_router
from app.api.routes.metadata import router as metadata_router

__all__ = [
    "admin_router",
    "auth_clerk_router",
    "auth_router",
    "collections_router",
    "content_router",
    "documents_router",
    "entities_router",
    "health_router",
    "image_router",
    "metadata_router",
    "public_router",
    "rag_query_router",
    "users_router",
    "media_router",
]
