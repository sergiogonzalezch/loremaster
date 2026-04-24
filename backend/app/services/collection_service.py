import logging
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.collections import Collection
from app.services.deletion_service import cascade_delete_collection

logger = logging.getLogger(__name__)


def create_collection_service(
    session: Session, name: str, description: str = ""
) -> Collection:
    existing = session.exec(
        select(Collection).where(
            Collection.name == name,
            Collection.is_deleted == False,
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=409, detail="Ya existe una colección con ese nombre."
        )

    collection = Collection(name=name, description=description)
    session.add(collection)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409, detail="Ya existe una colección con ese nombre."
        )
    session.refresh(collection)
    logger.info("Collection '%s' created with id %s", name, collection.id)
    return collection


def list_collections_service(
    session: Session,
    page: int = 1,
    page_size: int = 20,
    name: Optional[str] = None,
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None,
) -> tuple[list[Collection], int]:
    conditions = [Collection.is_deleted == False]
    if name:
        conditions.append(Collection.name.ilike(f"%{name}%"))
    if created_after:
        conditions.append(Collection.created_at >= created_after)
    if created_before:
        conditions.append(Collection.created_at <= created_before)

    total = session.exec(
        select(func.count()).select_from(
            select(Collection).where(*conditions).subquery()
        )
    ).one()
    skip = (page - 1) * page_size
    items = session.exec(
        select(Collection).where(*conditions).offset(skip).limit(page_size)
    ).all()
    return list(items), total


def delete_collection_service(session: Session, collection: Collection) -> bool:
    vectors_cleaned = cascade_delete_collection(session, collection)
    session.commit()
    return vectors_cleaned
