"""Servicios de lógica de negocio para perfiles de usuario y avatares."""

import contextlib
import re
import shutil
from pathlib import Path

from fastapi import UploadFile
from sqlmodel import Session

from app.core.config import settings
from app.core.database.utils import db_commit
from app.core.storage import (
    build_storage_path,
    build_storage_url,
    generate_unique_filename,
    save_file,
)
from app.core.storage.validator import FileValidator
from app.models.db.user import User


def _get_profile_dir(username: str) -> Path:
    return build_storage_path("users", username, "img", "profile")


def get_avatar_info(user: User) -> dict:
    """Obtiene la información del avatar de un usuario.

    Args:
        user: Instancia del usuario.

    Returns:
        Diccionario con avatar_url y has_avatar.

    """
    return {
        "avatar_url": build_storage_url(user.avatar_path),
        "has_avatar": user.avatar_path is not None,
    }


async def upload_profile_image(session: Session, user: User, file: UploadFile) -> str:
    """Sube o reemplaza la imagen de perfil de un usuario.

    Si el usuario ya tiene avatar, lo reemplaza eliminando el anterior.

    Args:
        session: Sesión de base de datos activa.
        user: Instancia del usuario.
        file: Archivo de imagen subido.

    Returns:
        URL pública de la imagen subida.

    """
    if not re.match(r"^[A-Za-z0-9_-]{3,50}$", user.username):
        raise ValueError(
            f"Username inválido para construcción de ruta: {user.username!r}"
        )

    max_bytes = int(settings.profile_image_max_size_mb * 1024 * 1024)
    content = FileValidator.validate_image(file, max_bytes=max_bytes)

    ext = Path(file.filename or "image.jpg").suffix.lower()
    unique_filename = generate_unique_filename(ext)
    relative_path = f"users/{user.username}/img/profile/{unique_filename}"

    profile_dir = _get_profile_dir(user.username)
    profile_dir.mkdir(parents=True, exist_ok=True)
    for existing in profile_dir.iterdir():
        if existing.is_file():
            existing.unlink()

    save_file(content, relative_path)

    user.avatar_path = relative_path
    session.add(user)
    db_commit(session, f"upload_profile_image({user.username})")

    return build_storage_url(relative_path)


def delete_profile_image(session: Session, user: User) -> None:
    """Elimina la imagen de perfil de un usuario.

    Si no tiene avatar, no hace nada.

    Args:
        session: Sesión de base de datos activa.
        user: Instancia del usuario.

    """
    if not user.avatar_path:
        return

    profile_dir = _get_profile_dir(user.username)
    if profile_dir.exists() and profile_dir.is_dir():
        media_root_resolved = Path(settings.media_root).resolve()
        for item in profile_dir.iterdir():
            resolved = item.resolve()
            if resolved.is_file() and resolved.is_relative_to(media_root_resolved):
                resolved.unlink()
            elif resolved.is_dir() and resolved.is_relative_to(media_root_resolved):
                shutil.rmtree(resolved)
        with contextlib.suppress(OSError):
            profile_dir.rmdir()

    user.avatar_path = None
    session.add(user)
    db_commit(session, f"delete_profile_image({user.username})")
