"""Router para servir archivos multimedia con autenticación.

Reemplaza el mount de StaticFiles para proteger las imágenes con JWT.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session

from app.core.auth.dependencies import get_current_user
from app.core.config import settings
from app.database import get_session
from app.models.db.collection import Collection

router = APIRouter(prefix="", tags=["media"])
logger = logging.getLogger(__name__)


@router.get("/media/{path:path}")
def serve_media(
    path: str,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Serve media files with authentication.

    The path format is: {collection_id}/{entity_id}/{generation_id}/{image_id}.{extension}
    Verifies ownership by checking the collection belongs to the user.
    """
    parts = path.split("/")

    if len(parts) != 4:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")

    collection_id = parts[0]

    collection = session.get(Collection, collection_id)
    if not collection or collection.is_deleted:
        raise HTTPException(status_code=404, detail="Colección no encontrada.")
    if collection.owner_id != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Acceso denegado.")

    file_path = Path(settings.media_root) / path

    if not file_path.exists():
        logger.warning(f"Media file not found: {file_path}")
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")

    return FileResponse(
        file_path,
        media_type=f"image/{file_path.suffix[1:]}",
        headers={"Cache-Control": "public, max-age=3600"},
    )