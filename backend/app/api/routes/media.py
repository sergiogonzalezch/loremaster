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

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import settings

router = APIRouter(prefix="", tags=["media"])
logger = logging.getLogger(__name__)


@router.get("/media/{path:path}")
def serve_media(path: str):
    """Sirve archivos multimedia (imágenes, avatares).

    Valida que el path no intente path traversal (..) y que
    el archivo exista dentro del directorio de medios.
    """
    # Prevenir path traversal
    if ".." in path or path.startswith("/") or path.startswith("\\"):
        raise HTTPException(status_code=400, detail="Ruta inválida.")

    media_root_resolved = Path(settings.media_root).resolve()
    file_path = (media_root_resolved / path).resolve()

    # Defensa en profundidad: asegurar que el archivo está bajo media_root
    if not file_path.is_relative_to(media_root_resolved):
        logger.warning(f"Path traversal attempt: {path}")
        raise HTTPException(status_code=403, detail="Acceso denegado.")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")

    # Inferir content type por extensión
    suffix = file_path.suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    media_type = media_types.get(suffix, "application/octet-stream")

    return FileResponse(
        file_path,
        media_type=media_type,
        headers={
            "Cache-Control": "public, max-age=3600",
            "X-Content-Type-Options": "nosniff",
        },
    )
