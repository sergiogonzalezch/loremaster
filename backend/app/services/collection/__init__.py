"""Servicios de colecciones: CRUD y listado."""

from app.services.collection.collection_service import (
    create_collection_service,
    delete_collection_service,
    get_collection_with_counts_service,
    list_collections_service,
    update_collection_service,
)

__all__ = [
    "create_collection_service",
    "delete_collection_service",
    "get_collection_with_counts_service",
    "list_collections_service",
    "update_collection_service",
]
