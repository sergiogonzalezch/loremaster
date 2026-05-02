import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from alembic import command
from alembic.config import Config
from fastapi import FastAPI

from app.core.config import settings

logger = logging.getLogger(__name__)

_ALEMBIC_INI = Path(__file__).resolve().parent.parent.parent / "alembic.ini"


def _run_migrations() -> None:
    alembic_cfg = Config(str(_ALEMBIC_INI))
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
        from app.engine.rag import ping_qdrant

        await asyncio.to_thread(ping_qdrant)
        logger.info("Qdrant connection OK (%s)", settings.qdrant_url)
    except Exception as e:
        logger.warning("Qdrant not reachable at startup: %s", e)

    try:
        async with httpx.AsyncClient() as client:
            await client.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
        logger.info("Ollama connection OK (%s)", settings.ollama_base_url)
    except Exception as e:
        logger.warning("Ollama not reachable at startup: %s", e)

    yield
