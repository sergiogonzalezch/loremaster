"""Gestión del ciclo de vida de la aplicación FastAPI."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from alembic.config import Config
from fastapi import FastAPI

from alembic import command
from app.core.config import settings

logger = logging.getLogger(__name__)

_ALEMBIC_INI = Path(__file__).resolve().parent.parent.parent / "alembic.ini"


def _run_migrations() -> None:
    """Ejecuta las migraciones de Alembic heads-up usando la URL de la base de datos configurada."""
    alembic_cfg = Config(str(_ALEMBIC_INI))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Contexto del ciclo de vida de la aplicación.

    Al iniciar: aplica migraciones, verifica conexión a Qdrant y Ollama.
    Al cerrar: yield (sin limpieza especial).
    """
    try:
        _run_migrations()
        logger.info("Database migrations applied")
    except Exception as e:
        logger.critical("Database migration failed, aborting startup: %s", e)
        raise

    try:
        # Lazy import para evitar circularidad en startup (rag importa modelos).
        from app.engine.rag import ping_qdrant  # noqa: PLC0415

        await asyncio.to_thread(ping_qdrant)
        logger.info("Qdrant connection OK (%s)", settings.qdrant_url)
    except Exception as e:  # noqa: BLE001
        logger.warning("Qdrant not reachable at startup: %s", e)

    try:
        async with httpx.AsyncClient() as client:
            await client.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
        logger.info("Ollama connection OK (%s)", settings.ollama_base_url)
    except Exception as e:  # noqa: BLE001
        logger.warning("Ollama not reachable at startup: %s", e)

    yield
