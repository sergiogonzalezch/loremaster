"""Rutas para listar modelos LLM disponibles en Ollama."""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.config import settings

router = APIRouter(tags=["models"])


class ModelInfo(BaseModel):
    """Información de un modelo LLM instalado en Ollama."""

    name: str
    size: int
    is_default: bool


@router.get("/models", response_model=list[ModelInfo])
def list_models(_: Annotated[dict, Depends(get_current_user)]) -> list[ModelInfo]:
    """Lista los modelos LLM instalados localmente en Ollama."""
    try:
        response = httpx.get(
            f"{settings.ollama_base_url}/api/tags",
            timeout=5.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail="El servicio de modelos no está disponible en este momento.",
        ) from exc

    models = response.json().get("models", [])
    return [
        ModelInfo(
            name=m["name"],
            size=m.get("size", 0),
            is_default=m["name"] == settings.ollama_model,
        )
        for m in models
    ]
