import uuid
from pathlib import Path

from app.core.config import settings


def build_storage_path(*parts: str) -> Path:
    return Path(settings.media_root) / "/".join(parts)


def save_file(content: bytes, relative_path: str) -> str:
    path = Path(settings.media_root) / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)
    return relative_path


def build_storage_url(relative_path: str | None) -> str | None:
    if not relative_path:
        return None
    return f"{settings.storage_base_url}/{relative_path}"


def generate_unique_filename(extension: str) -> str:
    return f"{uuid.uuid4()}{extension.lower()}"


def delete_directory(relative_path: str) -> None:
    import shutil

    path = Path(settings.media_root) / relative_path
    if path.exists():
        shutil.rmtree(path.parent)
