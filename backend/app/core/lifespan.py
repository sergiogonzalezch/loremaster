import logging
import urllib.request
from contextlib import asynccontextmanager
from urllib.error import URLError

from alembic import command
from alembic.config import Config
from fastapi import FastAPI

from app.core.config import settings

logger = logging.getLogger(__name__)


def _run_migrations() -> None:
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        _run_migrations()
        logger.info("Database migrations applied")
    except Exception as e:
        logger.critical("Database migration failed, aborting startup: %s", e)
        raise

    try:
        from app.core.rag_engine import ping_qdrant

        ping_qdrant()
        logger.info("Qdrant connection OK (%s)", settings.qdrant_url)
    except Exception as e:
        logger.warning("Qdrant not reachable at startup: %s", e)

    try:
        urllib.request.urlopen(f"{settings.ollama_base_url}/api/tags", timeout=5)
        logger.info("Ollama connection OK (%s)", settings.ollama_base_url)
    except (URLError, Exception) as e:
        logger.warning("Ollama not reachable at startup: %s", e)

    yield
