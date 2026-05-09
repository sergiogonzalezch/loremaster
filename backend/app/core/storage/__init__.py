import uuid
from pathlib import Path

from app.core.config import settings


def build_storage_path(*parts: str) -> Path:
    """Construye una ruta de almacenamiento uniendo las partes proporcionadas
    con la raíz de almacenamiento configurada."""
    return Path(settings.media_root) / "/".join(parts)


def save_file(content: bytes, relative_path: str) -> str:
    """Guarda el contenido binario en la ruta relativa dentro del directorio de medios.
    Crea los directorios padres si no existen.

    Retorna la ruta relativa donde se guardó el archivo.
    """
    path = Path(settings.media_root) / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)
    return relative_path


def build_storage_url(relative_path: str | None) -> str | None:
    """Construye la URL pública para un archivo dado su ruta relativa.
    Retorna None si la ruta es None o vacía."""
    if not relative_path:
        return None
    return f"{settings.storage_base_url}/{relative_path}"


def generate_unique_filename(extension: str) -> str:
    """Genera un nombre de archivo único usando UUID4 con la extensión dada."""
    return f"{uuid.uuid4()}{extension.lower()}"


def delete_directory(relative_path: str) -> None:
    """Elimina el directorio que contiene la ruta relativa, incluyendo todos sus archivos."""
    import shutil

    path = Path(settings.media_root) / relative_path
    if path.exists():
        shutil.rmtree(path.parent)


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
