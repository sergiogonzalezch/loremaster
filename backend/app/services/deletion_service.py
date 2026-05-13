"""Orquestación de eliminaciones completas (soft-delete + físico).

Coordina:
1. Soft-delete en base de datos (colecciones, documentos, entidades, imágenes).
2. Borrado físico de archivos de imagen en disco.
3. Eliminación de vectores en Qdrant (con reintentos).

Importa funciones de cascade_service para la fase de soft-delete en cascada.
"""

import logging
import time
from pathlib import Path

from sqlmodel import Session, select

from app.core.config import settings
from app.core.database.soft_delete import soft_delete
from app.engine.rag import delete_collection_vectors
from app.models.db.collection import Collection
from app.models.db.document import Document
from app.models.db.entity import Entity
from app.models.db.image_generation import ImageRecord
from app.services.cascade_service import (
    cascade_delete_by_collection,
    cascade_delete_by_entity,
)

logger = logging.getLogger(__name__)

_QDRANT_RETRY_ATTEMPTS = 3
_QDRANT_RETRY_DELAY = 0.5


def _delete_vectors_with_retry(collection_id: str) -> bool:
    """Elimina vectores de Qdrant con reintentos automáticos.

    Realiza hasta 3 intentos con 0.5 segundos de demora entre cada uno.

    Args:
        collection_id: Identificador de la colección cuyos vectores se eliminarán.

    Returns:
        True si la eliminación fue exitosa; False si fallaron todos los intentos
        (vectores huérfanos que requieren limpieza manual).

    """
    for attempt in range(1, _QDRANT_RETRY_ATTEMPTS + 1):
        try:
            delete_collection_vectors(collection_id)
        except Exception as e: 
            if attempt < _QDRANT_RETRY_ATTEMPTS:
                logger.warning(
                    "Qdrant cleanup attempt %d/%d failed for collection %s: %s",
                    attempt,
                    _QDRANT_RETRY_ATTEMPTS,
                    collection_id,
                    e,
                )
                time.sleep(_QDRANT_RETRY_DELAY)
            else:
                logger.exception(
                    "Orphan vectors remain in Qdrant for collection %s "
                    "after %d attempts — manual cleanup needed. "
                    "collection_id=%s",
                    collection_id,
                    _QDRANT_RETRY_ATTEMPTS,
                    collection_id,
                )
        else:
            return True
    return False


def cascade_delete_entity(session: Session, entity: Entity) -> None:
    """Elimina en cascada una entidad y todos sus contenidos relacionados.

    Se eliminan de forma suave: los EntityContent asociados, los ImageRecord
    asociados, y la propia entidad.

    Args:
        session: Sesión de base de datos activa.
        entity: Instancia de la entidad a eliminar.

    """
    deleted_contents = cascade_delete_by_entity(
        session,
        entity.id,
        entity.collection_id,
    )
    logger.info(
        "Soft-deleted %d EntityContent(s) for entity %s",
        deleted_contents,
        entity.id,
    )

    deleted_images = _cascade_delete_images_by_entity(session, entity.id)
    logger.info(
        "Soft-deleted %d ImageRecord(s) for entity %s",
        deleted_images,
        entity.id,
    )

    soft_delete(session, entity)
    logger.info(
        "Entity %s soft-deleted from collection %s",
        entity.id,
        entity.collection_id,
    )


def cascade_delete_collection(session: Session, collection: Collection) -> bool:
    """Elimina en cascada una colección y todos sus contenidos relacionados.

    Se eliminan de forma suave: todos los documentos, todas las entidades
    (con sus contenidos e imágenes asociados), los EntityContents huérfanos,
    los ImageRecord huérfanos, y la propia colección. Además intenta eliminar
    los vectores de Qdrant con reintentos automáticos.

    Args:
        session: Sesión de base de datos activa.
        collection: Instancia de la colección a eliminar.

    Returns:
        True si los vectores de Qdrant también fueron eliminados exitosamente;
        False si fallaron los reintentos y quedan vectores huérfanos
        (requieren limpieza manual).

    """
    docs = session.exec(
        select(Document).where(
            Document.collection_id == collection.id,
            Document.is_deleted.is_(False),
        ),
    ).all()
    for doc in docs:
        soft_delete(session, doc)
    logger.info(
        "Soft-deleted %d document(s) for collection %s",
        len(docs),
        collection.id,
    )

    entities = session.exec(
        select(Entity).where(
            Entity.collection_id == collection.id,
            Entity.is_deleted.is_(False),
        ),
    ).all()
    for entity in entities:
        cascade_delete_entity(session, entity)
    logger.info(
        "Soft-deleted %d entity(ies) for collection %s",
        len(entities),
        collection.id,
    )

    orphan_contents = cascade_delete_by_collection(session, collection.id)
    if orphan_contents > 0:
        logger.info(
            "Soft-deleted %d orphan EntityContent(s) for collection %s",
            orphan_contents,
            collection.id,
        )

    orphan_images = _cascade_delete_images_by_collection(session, collection.id)
    if orphan_images > 0:
        logger.info(
            "Soft-deleted %d orphan ImageRecord(s) for collection %s",
            orphan_images,
            collection.id,
        )

    soft_delete(session, collection)
    logger.info("Collection %s soft-deleted", collection.id)

    return _delete_vectors_with_retry(collection.id)


def _delete_image_file(storage_path: str | None) -> None:
    """Elimina el archivo físico del disco si existe.

    Args:
        storage_path: Ruta relativa del archivo a eliminar dentro de media_root.

    """
    if not storage_path:
        return
    try:
        media_root_resolved = Path(settings.media_root).resolve()
        file_path = (media_root_resolved / storage_path).resolve()
        if not file_path.is_relative_to(media_root_resolved):
            logger.warning(
                "Attempted to delete file outside media_root: %s",
                storage_path,
            )
            return
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            logger.info("Deleted file: %s", storage_path)
    except OSError as e:
        logger.warning("Failed to delete file %s: %s", storage_path, e)


def _cascade_delete_images(
    session: Session,
    entity_id: str | None = None,
    collection_id: str | None = None,
    *,
    delete_files: bool = True,
) -> int:
    """Elimina de forma suave los ImageRecord según los filtros indicados.

    Args:
        session: Sesión de base de datos activa.
        entity_id: Si se proporciona, elimina imágenes de esta entidad.
        collection_id: Si se proporciona, elimina imágenes de esta colección.
        delete_files: Si True, elimina también los archivos físicos del disco.

    Returns:
        Número de ImageRecords eliminados de forma suave.

    Raises:
        ValueError: Si no se proporciona al menos un filtro (entity_id o collection_id).

    """
    conditions = [ImageRecord.is_deleted.is_(False)]
    if entity_id is not None:
        conditions.append(ImageRecord.entity_id == entity_id)
    if collection_id is not None:
        conditions.append(ImageRecord.collection_id == collection_id)

    images = session.exec(select(ImageRecord).where(*conditions)).all()
    for img in images:
        if delete_files:
            _delete_image_file(img.storage_path)
        soft_delete(session, img)
    return len(images)


def _cascade_delete_images_by_entity(session: Session, entity_id: str) -> int:
    """Elimina de forma suave todos los ImageRecord asociados a una entidad.

    Args:
        session: Sesión de base de datos activa.
        entity_id: Identificador de la entidad.

    Returns:
        Número de ImageRecords eliminados de forma suave.

    """
    return _cascade_delete_images(session, entity_id=entity_id)


def _cascade_delete_images_by_collection(session: Session, collection_id: str) -> int:
    """Elimina de forma suave todos los ImageRecord asociados a una colección.

    Args:
        session: Sesión de base de datos activa.
        collection_id: Identificador de la colección.

    Returns:
        Número de ImageRecords eliminados de forma suave.

    """
    return _cascade_delete_images(session, collection_id=collection_id)
