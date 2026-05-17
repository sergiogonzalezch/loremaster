"""Servicios de lógica de negocio para moderación de contenido."""

import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.models.db.moderation_log import ModerationLog

logger = logging.getLogger(__name__)


def log_moderation_event(
    session: Session,
    layer: str,
    snippet: str,
    *,
    user_id: str | None = None,
    collection_id: str | None = None,
    entity_id: str | None = None,
    operation: str | None = None,
    pattern_matched: str | None = None,
) -> None:
    """Registra un evento de moderación en la base de datos.

    Args:
        session: Sesión de base de datos activa.
        layer: Capa donde ocurrió el evento ('input', 'output', 'document').
        snippet: Texto que activó la moderación (se trunca a 200 caracteres).
        user_id: Clerk sub del usuario autenticado (opcional).
        collection_id: ID de la colección (opcional).
        entity_id: ID de la entidad (opcional).
        operation: Operación que disparó el evento (optional).
        pattern_matched: Expresión regular que coincidió (opcional).

    """
    try:
        entry = ModerationLog(
            layer=layer,
            snippet=snippet[:200],
            user_id=user_id,
            collection_id=collection_id,
            entity_id=entity_id,
            operation=operation,
            pattern_matched=pattern_matched[:200] if pattern_matched else None,
        )
        session.add(entry)
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.warning("Failed to persist moderation log entry: %s", e)
