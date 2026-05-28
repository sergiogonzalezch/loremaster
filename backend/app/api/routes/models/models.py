"""Rutas para listar modelos LLM disponibles en Ollama."""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.services.model_service import list_ollama_models

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
        models = list_ollama_models()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail="El servicio de modelos no está disponible en este momento.",
        ) from exc
    return [ModelInfo(**m) for m in models]
