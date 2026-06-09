"""Caché semántica RAG — almacena respuestas en Redis indexadas por embedding de consulta.

Fail-open: si Redis no responde, lookup devuelve None y store es no-op.
"""

import json
import logging
import uuid

import numpy as np
import redis as _redis_lib

from app.core.config import settings

logger = logging.getLogger(__name__)

_KEY_PREFIX = "scache"
_client: _redis_lib.Redis | None = None


def _get_client() -> _redis_lib.Redis | None:
    global _client
    if _client is None:
        try:
            c = _redis_lib.from_url(settings.redis_url, decode_responses=False)
            c.ping()
            _client = c
        except Exception:  # noqa: BLE001
            logger.warning("Redis no disponible; caché semántica desactivada")
    return _client


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def lookup(collection_id: str, query_vec: np.ndarray) -> str | None:
    """Retorna respuesta cacheada si similitud coseno >= threshold, o None."""
    if not settings.semantic_cache_enabled:
        return None
    client = _get_client()
    if client is None:
        return None
    try:
        for key in client.scan_iter(f"{_KEY_PREFIX}:{collection_id}:*"):
            data = client.get(key)
            if data is None:
                continue
            entry = json.loads(data)
            cached_vec = np.array(entry["embedding"], dtype=np.float32)
            sim = _cosine_sim(query_vec, cached_vec)
            if sim >= settings.semantic_cache_threshold:
                logger.info(
                    "Cache hit para colección %s (similitud=%.3f)",
                    collection_id,
                    sim,
                )
                return str(entry["answer"])
    except Exception:  # noqa: BLE001
        logger.warning("Error consultando caché semántica", exc_info=True)
    return None


def store(collection_id: str, query_vec: np.ndarray, answer: str) -> None:
    """Almacena respuesta + embedding en Redis con TTL configurable."""
    if not settings.semantic_cache_enabled:
        return
    client = _get_client()
    if client is None:
        return
    try:
        key = f"{_KEY_PREFIX}:{collection_id}:{uuid.uuid4()}"
        payload = json.dumps({"embedding": query_vec.tolist(), "answer": answer})
        client.set(key, payload, ex=settings.semantic_cache_ttl)
        logger.debug("Respuesta RAG cacheada para colección %s", collection_id)
    except Exception:  # noqa: BLE001
        logger.warning("Error almacenando en caché semántica", exc_info=True)


def ping_redis() -> None:
    """Verifica conectividad con Redis (invocado desde lifespan)."""
    c = _redis_lib.from_url(settings.redis_url)
    c.ping()
