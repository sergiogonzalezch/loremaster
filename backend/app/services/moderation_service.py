import logging

from sqlmodel import Session

from app.models.moderation_log import ModerationLog

logger = logging.getLogger(__name__)


def log_moderation_event(session: Session, layer: str, snippet: str) -> None:
    try:
        entry = ModerationLog(layer=layer, snippet=snippet[:200])
        session.add(entry)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning("Failed to persist moderation log entry: %s", e)
