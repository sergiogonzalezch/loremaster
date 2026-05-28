"""Servicio para listar modelos LLM disponibles en Ollama."""

import httpx

from app.core.config import settings


def list_ollama_models() -> list[dict]:
    """Obtiene y filtra los modelos LLM instalados en Ollama.

    Returns:
        Lista de dicts con keys ``name``, ``size``, ``is_default``.

    Raises:
        httpx.HTTPError: Si Ollama no responde o devuelve error HTTP.

    """
    response = httpx.get(
        f"{settings.ollama_base_url}/api/tags",
        timeout=settings.ollama_models_timeout_seconds,
    )
    response.raise_for_status()

    models = response.json().get("models", [])
    excluded = settings.ollama_excluded_models
    return [
        {
            "name": m["name"],
            "size": m.get("size", 0),
            "is_default": m["name"] == settings.ollama_model,
        }
        for m in models
        if not any(m["name"].startswith(prefix) for prefix in excluded)
    ]
