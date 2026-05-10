"""Re-exportación de todos los routers de la API."""

from app.api.routes.auth import auth_router, auth_clerk_router
from app.api.routes.admin.admin import router as admin_router
from app.api.routes.collections import collections_router, rag_query_router
from app.api.routes.documents import documents_router
from app.api.routes.entities import entities_router, content_router
from app.api.routes.health import router as health_router
from app.api.routes.images import image_router
from app.api.routes.metadata import router as metadata_router
from app.api.routes.public.public import public_router
from app.api.routes.users.users import router as users_router

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
]
