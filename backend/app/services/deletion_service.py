"""Orquestación de eliminaciones completas (soft-delete + físico).

Coordina:
1. Soft-delete en base de datos (colecciones, documentos, entidades, imágenes).
2. Borrado físico de archivos de imagen en disco.
3. Eliminación de vectores en Qdrant (con reintentos).

Importa funciones de cascade_service para la fase de soft-delete en cascada.
"""

import logging
import time
from datetime import UTC, datetime
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database.soft_delete import soft_delete
from app.core.storage import delete_file
from app.core.database.utils import db_commit
from app.engine.rag import delete_collection_vectors
from app.models.db.collection import Collection
from app.models.db.document import Document
from app.models.db.entity import Entity
from app.models.db.image_generation import ImageRecord
from app.models.db.user import User
from app.services.cascade_service import (
    cascade_delete_by_collection,
    cascade_delete_by_entity,
)
from app.services.profile.profile_service import delete_profile_image

logger = logging.getLogger(__name__)


def _delete_vectors_with_retry(collection_id: str) -> bool:
    """Elimina vectores de Qdrant con reintentos automáticos.

    Realiza hasta settings.qdrant_retry_attempts intentos con settings.qdrant_retry_delay_seconds de demora.

    Args:
        collection_id: Identificador de la colección cuyos vectores se eliminarán.

    Returns:
        True si la eliminación fue exitosa; False si fallaron todos los intentos
        (vectores huérfanos que requieren limpieza manual).

    """
    for attempt in range(1, settings.qdrant_retry_attempts + 1):
        try:
            delete_collection_vectors(collection_id)
        except Exception as e:
            if attempt < settings.qdrant_retry_attempts:
                logger.warning(
                    "Qdrant cleanup attempt %d/%d failed for collection %s: %s",
                    attempt,
                    settings.qdrant_retry_attempts,
                    collection_id,
                    e,
                )
                time.sleep(settings.qdrant_retry_delay_seconds)
            else:
                logger.exception(
                    "Orphan vectors remain in Qdrant for collection %s after %d attempts — manual cleanup needed. collection_id=%s",
                    collection_id,
                    settings.qdrant_retry_attempts,
                    collection_id,
                )
        else:
            return True
    return False


def cascade_delete_entity(session: Session, entity: Entity) -> None:
    """Elimina en cascada una entidad y todos sus contenidos relacionados.

    Acumula los cambios con commit=False — el caller es responsable del commit.
    Callers conocidos: cascade_delete_collection (commit al final de la colección)
    y delete_entity_service (db_commit inmediato después de esta llamada).

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

    soft_delete(session, entity, commit=False)
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
        soft_delete(session, doc, commit=False)
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

    soft_delete(session, collection, commit=False)
    logger.info("Collection %s soft-deleted", collection.id)

    db_commit(session, f"cascade_delete_collection({collection.id})")
    return _delete_vectors_with_retry(collection.id)


def _delete_image_file(storage_path: str | None) -> None:
    delete_file(storage_path)


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
        soft_delete(session, img, commit=False)
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


def delete_user_service(session: Session, user: User) -> None:
    """Elimina un usuario y todas sus colecciones en cascada (operación de administración).

    Cascade-elimina colecciones y sus contenidos, borra el avatar y soft-deleteae al usuario.
    El log de auditoría y la verificación de auto-eliminación son responsabilidad del caller.

    Args:
        session: Sesión de base de datos activa.
        user: Instancia del usuario a eliminar.

    """
    collections = session.exec(
        select(Collection).where(
            Collection.owner_id == user.id,
            Collection.is_deleted.is_(False),
        ),
    ).all()
    for collection in collections:
        cascade_delete_collection(session, collection)

    try:
        delete_profile_image(session, user)
    except OSError:
        logger.warning("Failed to delete avatar for user %s during deletion", user.id)

    user.is_deleted = True
    user.deleted_at = datetime.now(UTC)
    session.add(user)
    session.commit()
