"""Endpoints de monitoreo y health check."""

import httpx
from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    """Endpoint de health check para monitoreo."""
    status = {"status": "healthy", "services": {}}

    qdrant_url = settings.qdrant_url
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{qdrant_url}/ready")
            status["services"]["qdrant"] = (
                "healthy" if resp.status_code == 200 else "unhealthy"
            )
    except httpx.TransportError:
        status["services"]["qdrant"] = "unhealthy"
        status["status"] = "degraded"

    ollama_url = settings.ollama_base_url
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{ollama_url}/api/tags")
            status["services"]["ollama"] = (
                "healthy" if resp.status_code == 200 else "unhealthy"
            )
    except httpx.TransportError:
        status["services"]["ollama"] = "unhealthy"
        status["status"] = "degraded"

    return status
