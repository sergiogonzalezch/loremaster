import logging
from datetime import datetime, timezone
from typing import TypeVar, Type, Optional

from sqlmodel import Session, select, SQLModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=SQLModel)


def soft_delete(session: Session, entity) -> bool:
    entity.is_deleted = True
    entity.deleted_at = datetime.now(timezone.utc)
    if hasattr(entity, "updated_at"):
        entity.updated_at = datetime.now(timezone.utc)
    session.add(entity)
    return True


def get_active_by_id(
    session: Session,
    model: Type[T],
    record_id: str,
    collection_id: str,
) -> Optional[T]:
    stmt = select(model).where(
        model.id == record_id,
        model.collection_id == collection_id,
        model.is_deleted == False,
    )
    return session.exec(stmt).first()


def list_active_by_collection(
    session: Session,
    model: Type[T],
    collection_id: str,
) -> list[T]:
    stmt = select(model).where(
        model.collection_id == collection_id,
        model.is_deleted == False,
    )
    return session.exec(stmt).all()