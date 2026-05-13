"""Router para servir archivos multimedia.

Reemplaza el mount de StaticFiles para proteger contra path traversal.

Control de acceso por tipo de recurso:
- Imágenes generadas (users/*/img/generation/*):
    - is_shared=True  → público (feed)
    - is_shared=False → solo el owner autenticado (cookie HttpOnly)
- Avatares de perfil (users/*/img/profile/*) → siempre públicos
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from app.core.auth.dependencies import get_current_user_optional
from app.core.config import settings
from app.database import get_session
from app.models.db.collection import Collection
from app.models.db.image_generation import ImageRecord

router = APIRouter(prefix="", tags=["media"])
logger = logging.getLogger(__name__)

_ALLOWED_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

# Posición de los segmentos en rutas users/{user}/img/{tipo}/...
_PATH_KIND_IDX = 3
_PATH_MIN_PARTS = _PATH_KIND_IDX + 1


def _resolve_safe_media_path(path: str) -> Path:
    """Valida la ruta y devuelve la ruta absoluta del archivo bajo media_root."""
    if ".." in path or path.startswith(("/", "\\")):
        raise HTTPException(status_code=400, detail="Ruta inválida.")

    media_root_resolved = Path(settings.media_root).resolve()
    file_path = (media_root_resolved / path).resolve()

    if not file_path.is_relative_to(media_root_resolved):
        logger.warning("Path traversal attempt: %s", path)
        raise HTTPException(status_code=403, detail="Acceso denegado.")

    return file_path


def _classify_media_kind(path: str) -> str | None:
    """Clasifica la ruta como 'generation', 'profile' o None si no aplica."""
    parts = Path(path).parts
    if len(parts) < _PATH_MIN_PARTS or parts[2] != "img":
        return None
    kind = parts[_PATH_KIND_IDX]
    if kind in ("generation", "profile"):
        return kind
    return None


def _check_generation_access(
    session: Session,
    storage_path: str,
    current_user: dict | None,
) -> None:
    """Verifica que el usuario actual puede acceder a una imagen generada.

    Lanza 404 si la imagen no existe, no es pública y el usuario no es el owner.
    """
    record = session.exec(
        select(ImageRecord).where(
            ImageRecord.storage_path == storage_path,
            ImageRecord.is_deleted.is_(False),
        )
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    if record.is_shared:
        return
    if not current_user:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    owned = session.exec(
        select(Collection).where(
            Collection.id == record.collection_id,
            Collection.owner_id == current_user["sub"],
            Collection.is_deleted.is_(False),
        )
    ).first()
    if not owned:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")


@router.get("/media/{path:path}")
def serve_media(
    path: str,
    session: Session = Depends(get_session),
    current_user: dict | None = Depends(get_current_user_optional),
):
    """Sirve archivos multimedia (imágenes, avatares).

    Valida path traversal. Para imágenes generadas aplica auth + ownership
    cuando is_shared=False. Los avatares de perfil son públicos.
    """
    file_path = _resolve_safe_media_path(path)

    kind = _classify_media_kind(path)
    if kind is None:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    if kind == "generation":
        _check_generation_access(session, path, current_user)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")

    suffix = file_path.suffix.lower()
    if suffix not in _ALLOWED_MEDIA_TYPES:
        logger.warning("Blocked request for disallowed file type: %s", path)
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")

    return FileResponse(
        file_path,
        media_type=_ALLOWED_MEDIA_TYPES[suffix],
        headers={
            "Cache-Control": "public, max-age=3600",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": f'inline; filename="{file_path.name}"',
        },
    )
