import logging

from fastapi import HTTPException
from sqlalchemy import func
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
        raise HTTPException(status_code=409, detail="Collection name already exists")

    collection = Collection(name=name, description=description)
    session.add(collection)
    session.commit()
    session.refresh(collection)
    logger.info("Collection '%s' created with id %s", name, collection.id)
    return collection


def list_collections_service(
    session: Session, page: int = 1, page_size: int = 20
) -> tuple[list[Collection], int]:
    base_filter = (Collection.is_deleted == False,)
    total = session.exec(
        select(func.count()).select_from(
            select(Collection).where(*base_filter).subquery()
        )
    ).one()
    skip = (page - 1) * page_size
    items = session.exec(
        select(Collection).where(*base_filter).offset(skip).limit(page_size)
    ).all()
    return list(items), total


def delete_collection_service(session: Session, collection: Collection) -> bool:
    cascade_delete_collection(session, collection)
    session.commit()
    return True
