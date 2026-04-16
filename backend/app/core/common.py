import logging
from datetime import datetime, timezone
from typing import TypeVar, Type, Optional

from sqlmodel import Session, select, SQLModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=SQLModel)


def soft_delete(session: Session, record) -> bool:
    record.is_deleted = True
    record.deleted_at = datetime.now(timezone.utc)
    if hasattr(record, "updated_at"):
        record.updated_at = datetime.now(timezone.utc)
    session.add(record)
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
    filters = [
        model.collection_id == collection_id,
        model.is_deleted == False,
    ]

    if hasattr(model, "status"):
        filters.append(getattr(model, "status") != "processing")

    stmt = select(model).where(*filters)
    return session.exec(stmt).all()
