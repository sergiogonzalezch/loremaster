"""Servicio de health check para servicios externos."""

import httpx

from app.core.config import settings


def check_services_health() -> dict:
    """Verifica el estado de Qdrant y Ollama.

    Returns:
        Dict con ``status`` global (``healthy`` | ``degraded``) y
        ``services`` con el estado individual de cada servicio externo.

    """
    result: dict = {"status": "healthy", "services": {}}

    try:
        with httpx.Client(timeout=settings.health_check_timeout_seconds) as client:
            resp = client.get(f"{settings.qdrant_url}/readyz")
            result["services"]["qdrant"] = "healthy" if resp.status_code == 200 else "unhealthy"
    except httpx.TransportError:
        result["services"]["qdrant"] = "unhealthy"
        result["status"] = "degraded"

    try:
        with httpx.Client(timeout=settings.health_check_timeout_seconds) as client:
            resp = client.get(f"{settings.ollama_base_url}/api/tags")
            result["services"]["ollama"] = "healthy" if resp.status_code == 200 else "unhealthy"
    except httpx.TransportError:
        result["services"]["ollama"] = "unhealthy"
        result["status"] = "degraded"

    return result
