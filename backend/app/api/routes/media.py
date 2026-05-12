"""Router para servir archivos multimedia.

Reemplaza el mount de StaticFiles para proteger contra path traversal.
Las imágenes son accesibles públicamente (no requieren auth) para que
los navegadores puedan cargarlas via <img src=...>.

NOTA DE SEGURIDAD: Para producción, considerar:
- Signed URLs con expiración
- Cookies HttpOnly para auth en requests de recursos estáticos
- CDN con autenticación
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from app.core.config import settings
from app.database import get_session
from app.models.db.image_generation import ImageRecord

router = APIRouter(prefix="", tags=["media"])
logger = logging.getLogger(__name__)


@router.get("/media/{path:path}")
def serve_media(path: str, session: Session = Depends(get_session)):
    """Sirve archivos multimedia (imágenes, avatares).

    Valida path traversal y verifica is_shared en BD para imágenes generadas.
    Los avatares de perfil (users/*/img/profile/*) son siempre públicos.
    """
    # Prevenir path traversal
    if ".." in path or path.startswith(("/", "\\")):
        raise HTTPException(status_code=400, detail="Ruta inválida.")

    media_root_resolved = Path(settings.media_root).resolve()
    file_path = (media_root_resolved / path).resolve()

    # Defensa en profundidad: asegurar que el archivo está bajo media_root
    if not file_path.is_relative_to(media_root_resolved):
        logger.warning("Path traversal attempt: %s", path)
        raise HTTPException(status_code=403, detail="Acceso denegado.")

    # Clasificar el tipo de recurso por su ruta: users/{u}/img/{tipo}/...
    parts = Path(path).parts
    is_generation = (
        len(parts) >= 4 and parts[2] == "img" and parts[3] == "generation"
    )  # noqa: PLR2004
    is_profile = (
        len(parts) >= 4 and parts[2] == "img" and parts[3] == "profile"
    )  # noqa: PLR2004

    if is_generation:
        record = session.exec(
            select(ImageRecord).where(
                ImageRecord.storage_path == path,
                ImageRecord.is_shared.is_(True),
                ImageRecord.is_deleted.is_(False),
            )
        ).first()
        if not record:
            raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    elif not is_profile:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")

    # Lista blanca estricta de tipos de archivo permitidos (C-6)
    suffix = file_path.suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    if suffix not in media_types:
        logger.warning("Blocked request for disallowed file type: %s", path)
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")

    return FileResponse(
        file_path,
        media_type=media_types[suffix],
        headers={
            "Cache-Control": "public, max-age=3600",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": f'inline; filename="{file_path.name}"',
        },
    )
