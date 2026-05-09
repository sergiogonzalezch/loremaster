"""Rutas de colecciones y consultas RAG."""

from app.api.routes.collections.collections import router as collections_router
from app.api.routes.collections.rag_query import router as rag_query_router

__all__ = ["collections_router", "rag_query_router"]
