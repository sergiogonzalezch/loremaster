"""Utilidades de almacenamiento de archivos para la aplicación."""

import logging
import uuid
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


def build_storage_path(*parts: str) -> Path:
    """Construye una ruta de almacenamiento.

    Une las partes proporcionadas con la raíz de almacenamiento configurada.
    """
    return Path(settings.media_root).joinpath(*parts)


def save_file(content: bytes, relative_path: str) -> str:
    """Guarda el contenido binario en la ruta relativa.

    En modo s3 sube el objeto al bucket configurado.
    En modo local escribe en disco dentro de media_root.

    Retorna la ruta relativa donde se guardó el archivo.
    """
    if settings.storage_backend == "s3":
        from app.core.storage.s3_client import get_s3_client

        get_s3_client().put_object(
            Bucket=settings.s3_bucket,
            Key=relative_path,
            Body=content,
        )
        return relative_path

    media_root_resolved = Path(settings.media_root).resolve()
    path = (media_root_resolved / relative_path).resolve()
    if not path.is_relative_to(media_root_resolved):
        msg = "Ruta de archivo inválida: intento de path traversal detectado"
        raise ValueError(
            msg,
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return relative_path


def delete_file(relative_path: str | None) -> None:
    """Elimina un archivo del almacenamiento.

    En modo s3 elimina el objeto del bucket (no-op si no existe).
    En modo local elimina el archivo de disco dentro de media_root.
    No lanza excepción si el archivo no existe.
    """
    if not relative_path:
        return

    if settings.storage_backend == "s3":
        from app.core.storage.s3_client import get_s3_client

        try:
            get_s3_client().delete_object(Bucket=settings.s3_bucket, Key=relative_path)
            logger.info("Deleted S3 object: %s", relative_path)
        except Exception:
            logger.warning("Failed to delete S3 object: %s", relative_path)
        return

    media_root_resolved = Path(settings.media_root).resolve()
    file_path = (media_root_resolved / relative_path).resolve()
    if not file_path.is_relative_to(media_root_resolved):
        logger.warning("Attempted to delete file outside media_root: %s", relative_path)
        return
    try:
        file_path.unlink()
        logger.info("Deleted file: %s", relative_path)
    except (FileNotFoundError, OSError) as e:
        logger.warning("Failed to delete file %s: %s", relative_path, e)


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
