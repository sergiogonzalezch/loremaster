import logging
from datetime import datetime, timezone
from typing import Literal, Optional

from sqlmodel import Session, select

from app.core.database.utils import soft_delete, paginate_with_sort, db_commit
from app.core.exceptions import (
    ContentDiscardedError,
    ContentNotShareableError,
)
from app.models.db.entity import Entity
from app.models.db.entity_content import EntityContent
from app.models.schemas.entity_content import EntityContentResponse
from app.models.db.generated_text import GeneratedText
from app.models.enums import ContentCategory, ContentStatus

logger = logging.getLogger(__name__)


def list_contents(
    session: Session,
    entity_id: str,
    collection_id: str,
    category: Optional[ContentCategory] = None,
    status: Literal["active", "pending", "confirmed", "discarded", "all"] = "active",
    page: int = 1,
    page_size: int = 20,
    order: Literal["asc", "desc"] = "desc",
) -> tuple[list[EntityContentResponse], int]:
    """Lista los contenidos de una entidad con filtros y paginación.

    Args:
        session: Sesión de base de datos activa.
        entity_id: Identificador de la entidad.
        collection_id: Identificador de la colección.
        category: Filtrar por categoría (opcional).
        status: Filtrar por estado. 'active' excluye discarded por defecto.
        page: Número de página.
        page_size: Elementos por página.
        order: Orden ascendente o descendente.

    Returns:
        Tupla de (lista de contenidos con GeneratedText, total de resultados).
    """
    conditions = [
        EntityContent.entity_id == entity_id,
        EntityContent.collection_id == collection_id,
        EntityContent.is_deleted == False,
    ]

    if status == "active":
        conditions.append(
            EntityContent.status.in_([ContentStatus.pending, ContentStatus.confirmed])
        )
    elif status == "pending":
        conditions.append(EntityContent.status == ContentStatus.pending)
    elif status == "confirmed":
        conditions.append(EntityContent.status == ContentStatus.confirmed)
    elif status == "discarded":
        conditions.append(EntityContent.status == ContentStatus.discarded)

    if category is not None:
        conditions.append(EntityContent.category == category)

    items, total = paginate_with_sort(
        session,
        EntityContent,
        conditions,
        page=page,
        page_size=page_size,
        order_col=EntityContent.created_at,
        order=order,
    )
    return [_to_response(session, item) for item in items], total


def edit_content(
    session: Session,
    content_id: str,
    entity_id: str,
    collection_id: str,
    new_text: str,
) -> EntityContentResponse | None:
    """Edita el texto de un contenido activo (pending o confirmed).

    No permite editar contenidos descartados.

    Args:
        session: Sesión de base de datos activa.
        content_id: Identificador del contenido.
        entity_id: Identificador de la entidad.
        collection_id: Identificador de la colección.
        new_text: Nuevo texto para el contenido.

    Returns:
        Contenido actualizado con el GeneratedText asociado, o None si no existe.

    Raises:
        ContentDiscardedError: Si el contenido está descartado.
    """
    new_text = new_text.strip()
    content = _get_active_content(session, content_id, entity_id, collection_id)
    if not content:
        return None
    if content.status == ContentStatus.discarded:
        raise ContentDiscardedError()
    now = datetime.now(timezone.utc)
    content.content = new_text
    content.updated_at = now
    session.add(content)
    db_commit(session, f"edit_content({content_id})")
    session.refresh(content)
    return _to_response(session, content)


def confirm_content(
    session: Session,
    content_id: str,
    entity: Entity,
) -> EntityContent | None:
    """Confirma un contenido pendiente y descarta automáticamente sus hermanos.

    Al confirmar, todos los contenidos pending de la misma categoría en la
    misma entidad se marcan como 'discarded'.

    Args:
        session: Sesión de base de datos activa.
        content_id: Identificador del contenido a confirmar.
        entity: Instancia de la entidad propietaria.

    Returns:
        Contenido confirmado, o None si no existe o no está pending.
    """
    content = _get_pending_content(session, content_id, entity.id, entity.collection_id)
    if not content:
        return None

    now = datetime.now(timezone.utc)
    content.status = ContentStatus.confirmed
    content.confirmed_at = now
    content.updated_at = now
    session.add(content)

    discarded = _discard_sibling_contents(
        session,
        entity_id=entity.id,
        collection_id=entity.collection_id,
        category=content.category,
        exclude_id=content_id,
        statuses=[ContentStatus.pending],
    )
    logger.info(
        "Auto-discarded %d sibling content(s) for entity %s category %s",
        discarded,
        entity.id,
        content.category,
    )

    db_commit(session, f"confirm_content({content_id})")
    session.refresh(content)
    logger.info("EntityContent %s confirmed for entity %s", content_id, entity.id)
    return content


def discard_content(
    session: Session,
    content_id: str,
    entity_id: str,
    collection_id: str,
) -> EntityContentResponse | None:
    """Descarta un contenido pendiente.

    Args:
        session: Sesión de base de datos activa.
        content_id: Identificador del contenido.
        entity_id: Identificador de la entidad.
        collection_id: Identificador de la colección.

    Returns:
        Contenido descartado con sus metadatos, o None si no existe.
    """
    content = _get_pending_content(session, content_id, entity_id, collection_id)
    if not content:
        return None
    content.status = ContentStatus.discarded
    content.updated_at = datetime.now(timezone.utc)
    session.add(content)
    db_commit(session, f"discard_content({content_id})")
    session.refresh(content)
    logger.info("EntityContent %s discarded", content_id)
    return _to_response(session, content)


def share_content(
    session: Session,
    content_id: str,
    entity_id: str,
    collection_id: str,
    shared: bool,
) -> EntityContentResponse | None:
    """Comparte o deja de compartir un contenido en el feed público.

    Solo contenidos en estado 'confirmed' pueden compartirse.

    Args:
        session: Sesión de base de datos activa.
        content_id: Identificador del contenido.
        entity_id: Identificador de la entidad.
        collection_id: Identificador de la colección.
        shared: True para compartir, False para dejar de compartir.

    Returns:
        Contenido actualizado, o None si no existe.

    Raises:
        ContentNotShareableError: Si el contenido no está confirmado.
    """
    content = _get_active_content(session, content_id, entity_id, collection_id)
    if not content:
        return None
    if content.status != ContentStatus.confirmed:
        raise ContentNotShareableError()
    content.is_shared = shared
    session.add(content)
    db_commit(session, f"share_content({content_id})")
    session.refresh(content)
    logger.info("EntityContent %s is_shared=%s", content_id, shared)
    return _to_response(session, content)


def soft_delete_content(
    session: Session,
    content_id: str,
    entity_id: str,
    collection_id: str,
) -> bool:
    """Elimina suavemente un contenido de entidad.

    Establece is_shared=False y marca como eliminada.

    Args:
        session: Sesión de base de datos activa.
        content_id: Identificador del contenido.
        entity_id: Identificador de la entidad.
        collection_id: Identificador de la colección.

    Returns:
        True si se eliminó, False si no se encontró el contenido.
    """
    content = _get_active_content(session, content_id, entity_id, collection_id)
    if not content:
        return False
    content.is_shared = False
    soft_delete(session, content)
    db_commit(session, f"soft_delete_content({content_id})")
    logger.info("EntityContent %s soft-deleted", content_id)
    return True


# ── Private helpers ───────────────────────────────────────────────────────────


def _to_response(session: Session, content: EntityContent) -> EntityContentResponse:
    gt = session.get(GeneratedText, content.generated_text_id)
    return EntityContentResponse(
        id=content.id,
        entity_id=content.entity_id,
        collection_id=content.collection_id,
        generated_text_id=content.generated_text_id,
        category=content.category,
        content=content.content,
        raw_content=gt.raw_content if gt else None,
        query=gt.query if gt else None,
        sources_count=gt.sources_count if gt else 0,
        token_count=gt.token_count if gt else 0,
        status=content.status,
        is_shared=content.is_shared,
        created_at=content.created_at,
        confirmed_at=content.confirmed_at,
        updated_at=content.updated_at,
    )


def _get_active_content(
    session: Session,
    content_id: str,
    entity_id: str,
    collection_id: str,
) -> EntityContent | None:
    return session.exec(
        select(EntityContent).where(
            EntityContent.id == content_id,
            EntityContent.entity_id == entity_id,
            EntityContent.collection_id == collection_id,
            EntityContent.is_deleted == False,
        )
    ).first()


def _get_pending_content(
    session: Session,
    content_id: str,
    entity_id: str,
    collection_id: str,
) -> EntityContent | None:
    content = _get_active_content(session, content_id, entity_id, collection_id)
    return content if content and content.status == ContentStatus.pending else None


def _discard_sibling_contents(
    session: Session,
    entity_id: str,
    collection_id: str,
    category: ContentCategory,
    exclude_id: str,
    statuses: list[ContentStatus],
) -> int:
    siblings = session.exec(
        select(EntityContent).where(
            EntityContent.entity_id == entity_id,
            EntityContent.collection_id == collection_id,
            EntityContent.category == category,
            EntityContent.id != exclude_id,
            EntityContent.status.in_(statuses),
            EntityContent.is_deleted == False,
        )
    ).all()
    for s in siblings:
        s.status = ContentStatus.discarded
        session.add(s)
    return len(siblings)
