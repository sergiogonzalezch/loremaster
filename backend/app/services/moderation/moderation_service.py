"""Servicios de lógica de negocio para moderación de contenido."""

import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.models.db.moderation_log import ModerationLog

logger = logging.getLogger(__name__)


def log_moderation_event(session: Session, layer: str, snippet: str) -> None:
    """Registra un evento de moderación en la base de datos.

    Args:
        session: Sesión de base de datos activa.
        layer: Capa donde ocurrió el evento (ej. 'input', 'output', 'guard').
        snippet: Texto que activó la moderación (se trunca a 200 caracteres).

    """
    try:
        entry = ModerationLog(layer=layer, snippet=snippet[:200])
        session.add(entry)
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.warning("Failed to persist moderation log entry: %s", e)
