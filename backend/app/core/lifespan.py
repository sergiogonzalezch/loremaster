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
from app.engine.rag import ping_qdrant

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
    import os as _os
    if _os.getenv("SKIP_MIGRATIONS", "").lower() in ("1", "true", "yes"):
        logger.info("Database migrations skipped (SKIP_MIGRATIONS)")
    else:
        try:
            # Correr migraciones en thread separado para no bloquear el event loop de asyncio.
            # SQLite + asyncio/greenlet en el mismo thread puede provocar un deadlock silencioso.
            await asyncio.wait_for(asyncio.to_thread(_run_migrations), timeout=30.0)
            logger.info("Database migrations applied")
        except Exception as e:
            logger.critical("Database migration failed, aborting startup: %s", e)
            raise

    if settings.storage_backend == "s3":
        def _init_s3_bucket() -> None:
            from app.core.storage.s3_client import get_s3_client
            _s3 = get_s3_client()
            try:
                _s3.head_bucket(Bucket=settings.s3_bucket)
            except Exception:  # noqa: BLE001
                _s3.create_bucket(Bucket=settings.s3_bucket)

        try:
            await asyncio.wait_for(asyncio.to_thread(_init_s3_bucket), timeout=15.0)
            logger.info("S3 bucket ready (%s @ %s)", settings.s3_bucket, settings.s3_endpoint_url)
        except Exception as e:  # noqa: BLE001
            logger.warning("S3 bucket initialization failed: %s", e)

    try:
        await asyncio.wait_for(asyncio.to_thread(ping_qdrant), timeout=10.0)
        logger.info("Qdrant connection OK (%s)", settings.qdrant_url)
    except Exception as e:  # noqa: BLE001
        logger.warning("Qdrant not reachable at startup: %s", e)

    try:
        async with httpx.AsyncClient() as client:
            await client.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
        logger.info("Ollama connection OK (%s)", settings.ollama_base_url)
    except Exception as e:  # noqa: BLE001
        logger.warning("Ollama not reachable at startup: %s", e)

    # Redirigir uvicorn.access hacia nuestro root handler para que los logs de
    # cada request (GET /api/v1/... 200) sean visibles con el mismo formato.
    # Esto debe hacerse aquí, después de que uvicorn aplica su propia dictConfig,
    # de lo contrario uvicorn la sobreescribiría al arrancar.
    _access_logger = logging.getLogger("uvicorn.access")
    _access_logger.handlers.clear()
    _access_logger.propagate = True

    yield
