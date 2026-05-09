import os
import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlmodel import Session

from app.core.config import settings
from app.core.common import db_commit
from app.models.db.user import User

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _get_profile_image_dir(username: str) -> Path:
    return Path(settings.media_root) / "users" / username / "img" / "profile"


def _build_avatar_path(username: str, filename: str) -> str:
    return f"users/{username}/img/profile/{filename}"


def _build_avatar_url(avatar_path: str | None) -> str | None:
    if not avatar_path:
        return None
    return f"{settings.storage_base_url}/{avatar_path}"


def validate_image_file(file: UploadFile) -> None:
    if file.content_type not in {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}:
        raise ValueError(
            f"Tipo de archivo no permitido: {file.content_type}. "
            f"Solo se permiten imágenes: {', '.join(sorted(IMAGE_EXTENSIONS))}"
        )


async def upload_profile_image(session: Session, user: User, file: UploadFile) -> str:
    validate_image_file(file)

    ext = Path(file.filename or "image.jpg").suffix.lower()
    if ext not in IMAGE_EXTENSIONS:
        raise ValueError(f"Extensión no permitida: {ext}")

    max_bytes = int(settings.profile_image_max_size_mb * 1024 * 1024)
    content = await file.read()
    if len(content) > max_bytes:
        raise ValueError(
            f"El archivo excede el tamaño máximo de "
            f"{settings.profile_image_max_size_mb}MB"
        )

    profile_dir = _get_profile_image_dir(user.username)
    profile_dir.mkdir(parents=True, exist_ok=True)

    for existing in profile_dir.iterdir():
        if existing.is_file():
            existing.unlink()

    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = profile_dir / unique_filename
    with open(file_path, "wb") as f:
        f.write(content)

    avatar_path = _build_avatar_path(user.username, unique_filename)
    user.avatar_path = avatar_path
    session.add(user)
    db_commit(session, f"upload_profile_image({user.username})")

    return _build_avatar_url(avatar_path)


def delete_profile_image(session: Session, user: User) -> None:
    if not user.avatar_path:
        return

    profile_dir = _get_profile_image_dir(user.username)
    if profile_dir.exists():
        shutil.rmtree(profile_dir)

    user.avatar_path = None
    session.add(user)
    db_commit(session, f"delete_profile_image({user.username})")


def get_avatar_info(user: User) -> dict:
    return {
        "avatar_url": _build_avatar_url(user.avatar_path),
        "has_avatar": user.avatar_path is not None,
    }
