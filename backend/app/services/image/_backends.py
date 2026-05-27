"""Implementaciones de backends de generación de imágenes (mock y ComfyUI).

Módulo puro: no accede a la base de datos ni a la sesión SQLModel.
Devuelve datos crudos que el servicio orquestador persiste.
"""

import logging
import uuid as _uuid
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.exceptions import ComfyUITimeoutError, ComfyUIUnavailableError
from app.core.storage import build_generation_path, build_storage_url, save_file
from app.engine.comfyui_client import (
    ComfyUIClient,
    inject_prompt,
    inject_seed,
    load_template,
)
from app.models.db.entity import Entity

logger = logging.getLogger(__name__)


@dataclass
class _ImageData:
    image_id: str
    filename: str
    seed: int
    storage_path: str | None = None
    image_url: str | None = None


@dataclass
class _GenerationParams:
    content_id: str
    category: str
    auto_prompt: str
    final_prompt: str
    batch_size: int
    seed_base: int
    backend: str


def _generate_mock_images(
    entity: Entity,
    batch_size: int,
    seed_base: int,
) -> list[_ImageData]:
    """Genera URLs placeholder para entornos sin ComfyUI."""
    images = []
    for i in range(batch_size):
        image_id = str(_uuid.uuid4())
        seed = seed_base + i
        placeholder_url = (
            f"https://placehold.co/{settings.image_width}x{settings.image_height}"
            f"/1a1a2e/9d6fe8?text={entity.name.replace(' ', '+')}+{i + 1}"
        )
        images.append(
            _ImageData(
                image_id=image_id,
                filename=f"{image_id}.png",
                seed=seed,
                image_url=placeholder_url,
            )
        )
    return images


def _save_comfyui_image(
    image_data: bytes,
    username: str,
    entity: Entity,
    generation_id: str,
    filename: str,
) -> str:
    relative_path = build_generation_path(
        username,
        entity.collection_id,
        entity.id,
        generation_id,
        filename,
    )
    save_file(image_data, relative_path)
    return relative_path


def _generate_comfyui_images(
    username: str,
    entity: Entity,
    params: _GenerationParams,
    generation_id: str,
) -> list[_ImageData]:
    """Llama a ComfyUI, descarga y guarda cada imagen del batch.

    Raises:
        ComfyUIUnavailableError: si ComfyUI no responde.
        ComfyUITimeoutError: si se agota el tiempo de espera.
        RuntimeError: si ninguna imagen del batch se generó con éxito.

    """
    client = ComfyUIClient(
        base_url=settings.comfyui_url,
        request_timeout=settings.comfyui_request_timeout,
    )
    workflow_base = load_template("flux2-klein-4b-api.json")
    workflow_base = inject_prompt(workflow_base, params.final_prompt)

    results: list[_ImageData] = []

    for i in range(params.batch_size):
        seed = params.seed_base + i
        workflow = inject_seed(workflow_base, seed)

        try:
            prompt_id = client.queue_prompt(workflow)
            result = client.get_history_until_complete(
                prompt_id,
                timeout=settings.comfyui_timeout,
            )
            output_images = client.get_output_images(result)
        except httpx.ConnectError as exc:
            raise ComfyUIUnavailableError() from exc
        except TimeoutError as exc:
            raise ComfyUITimeoutError(settings.comfyui_timeout) from exc
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning(
                "ComfyUI falló en iteración %d/%d: %s",
                i + 1,
                params.batch_size,
                exc,
            )
            continue

        for img_info in output_images[:1]:
            try:
                image_bytes = client.download_image(
                    filename=img_info["filename"],
                    subfolder=img_info["subfolder"],
                    folder_type=img_info["type"],
                )
            except (httpx.HTTPError, OSError) as exc:
                logger.warning("Descarga falló en iteración %d: %s", i + 1, exc)
                continue

            image_id = str(_uuid.uuid4())
            filename = f"{image_id}.png"
            storage_path = _save_comfyui_image(
                image_bytes, username, entity, generation_id, filename
            )
            results.append(
                _ImageData(
                    image_id=image_id,
                    filename=filename,
                    seed=seed,
                    storage_path=storage_path,
                    image_url=build_storage_url(storage_path),
                )
            )

    if not results:
        msg = "No se generaron imágenes desde ComfyUI"
        raise RuntimeError(msg)

    return results
