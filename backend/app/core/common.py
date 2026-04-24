import logging
from datetime import datetime, timezone
from typing import TypeVar, Type, Optional

from sqlalchemy import func
from sqlmodel import Session, select, SQLModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=SQLModel)


def soft_delete(session: Session, record) -> bool:
    now = datetime.now(timezone.utc)
    record.is_deleted = True
    record.deleted_at = now
    if hasattr(record, "updated_at"):
        record.updated_at = now
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
    stmt = select(model).where(
        model.collection_id == collection_id,
        model.is_deleted == False,
    )
    return session.exec(stmt).all()


def list_active_paginated(
    session: Session,
    model: Type[T],
    collection_id: str,
    skip: int,
    limit: int,
) -> tuple[list[T], int]:
    base_filter = (
        model.collection_id == collection_id,
        model.is_deleted == False,
    )
    total = session.exec(
        select(func.count()).select_from(select(model).where(*base_filter).subquery())
    ).one()
    items = session.exec(
        select(model).where(*base_filter).offset(skip).limit(limit)
    ).all()
    return list(items), total
