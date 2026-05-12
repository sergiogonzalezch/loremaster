"""Utilidades de almacenamiento de archivos para la aplicación."""

import uuid
from pathlib import Path

from app.core.config import settings


def build_storage_path(*parts: str) -> Path:
    """Construye una ruta de almacenamiento.

    Une las partes proporcionadas con la raíz de almacenamiento configurada.
    """
    return Path(settings.media_root).joinpath(*parts)


def save_file(content: bytes, relative_path: str) -> str:
    """Guarda el contenido binario en la ruta relativa.

    Crea los directorios padres si no existen dentro del directorio de medios.

    Retorna la ruta relativa donde se guardó el archivo.
    """
    media_root_resolved = Path(settings.media_root).resolve()
    path = (media_root_resolved / relative_path).resolve()
    if not path.is_relative_to(media_root_resolved):
        raise ValueError(
            "Ruta de archivo inválida: intento de path traversal detectado"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return relative_path


def build_storage_url(relative_path: str | None) -> str | None:
    """Construye la URL pública para un archivo.

    Retorna None si la ruta es None o vacía.
    """
    if not relative_path:
        return None
    return f"{settings.storage_base_url.rstrip('/')}/{relative_path}"


def generate_unique_filename(extension: str) -> str:
    """Genera un nombre de archivo único usando UUID4 con la extensión dada."""
    return f"{uuid.uuid4()}{extension.lower()}"


def build_generation_path(
    username: str,
    collection_id: str,
    entity_id: str,
    generation_id: str,
    filename: str,
) -> str:
    """Construye la ruta relativa para una imagen generada.

    Formato: users/{username}/img/generation/{collection_id}/{entity_id}/{generation_id}/{filename}
    """
    return f"users/{username}/img/generation/{collection_id}/{entity_id}/{generation_id}/{filename}"
