"""Operaciones de soft-delete en cascada.

Este módulo contiene funciones que propagan soft-delete a entidades hijas
(EntityContent) cuando se elimina una entidad o colección padre.
No realiza borrado físico de archivos ni vectores.
"""

import logging

from sqlmodel import Session, select

from app.core.database.soft_delete import soft_delete
from app.models.db.entity_content import EntityContent

logger = logging.getLogger(__name__)


def cascade_delete_by_entity(
    session: Session,
    entity_id: str,
    collection_id: str,
) -> int:
    """Realiza soft-delete de todos los EntityContent asociados a una entidad.

    Args:
        session: Sesión de base de datos activa.
        entity_id: Identificador de la entidad.
        collection_id: Identificador de la colección (para filtrar contenidos).

    Returns:
        Número de EntityContents eliminados de forma suave.

    """
    contents = session.exec(
        select(EntityContent).where(
            EntityContent.entity_id == entity_id,
            EntityContent.collection_id == collection_id,
            EntityContent.is_deleted.is_(False),
        ),
    ).all()
    for c in contents:
        soft_delete(session, c)
    logger.info(
        "Soft-deleted %d EntityContent(s) [entity_id=%s]",
        len(contents),
        entity_id,
    )
    return len(contents)


def cascade_delete_by_collection(
    session: Session,
    collection_id: str,
) -> int:
    """Realiza soft-delete de todos los EntityContent de una colección.

    Args:
        session: Sesión de base de datos activa.
        collection_id: Identificador de la colección.

    Returns:
        Número de EntityContents eliminados de forma suave.

    """
    contents = session.exec(
        select(EntityContent).where(
            EntityContent.collection_id == collection_id,
            EntityContent.is_deleted.is_(False),
        ),
    ).all()
    for c in contents:
        soft_delete(session, c)
    logger.info(
        "Soft-deleted %d EntityContent(s) [collection_id=%s]",
        len(contents),
        collection_id,
    )
    return len(contents)
