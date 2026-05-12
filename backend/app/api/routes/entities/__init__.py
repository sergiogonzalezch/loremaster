"""Rutas de entidades y contenido."""

from app.api.routes.entities.content import router as content_router
from app.api.routes.entities.entities import router as entities_router

__all__ = ["content_router", "entities_router"]
