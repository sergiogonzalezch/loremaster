import logging
from datetime import datetime, timezone
from typing import Literal, Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Session, select

from app.core.exceptions import DatabaseError, DuplicateCollectionNameError
from app.models.collections import Collection, UpdateCollectionRequest
from app.models.documents import Document
from app.models.entities import Entity
from app.services.deletion_service import cascade_delete_collection

logger = logging.getLogger(__name__)


def _fetch_counts(
    session: Session, collection_ids: list[str]
) -> tuple[dict[str, int], dict[str, int]]:
    if not collection_ids:
        return {}, {}
    doc_rows = session.exec(
        select(Document.collection_id, func.count(Document.id))
        .where(
            Document.collection_id.in_(collection_ids),
            Document.is_deleted == False,
        )
        .group_by(Document.collection_id)
    ).all()
    entity_rows = session.exec(
        select(Entity.collection_id, func.count(Entity.id))
        .where(
            Entity.collection_id.in_(collection_ids),
            Entity.is_deleted == False,
        )
        .group_by(Entity.collection_id)
    ).all()
    return (
        {cid: cnt for cid, cnt in doc_rows},
        {cid: cnt for cid, cnt in entity_rows},
    )


def get_collection_with_counts_service(
    session: Session, collection: Collection
) -> dict:
    doc_counts, entity_counts = _fetch_counts(session, [collection.id])
    return {
        **collection.model_dump(),
        "document_count": doc_counts.get(collection.id, 0),
        "entity_count": entity_counts.get(collection.id, 0),
    }


def create_collection_service(
    session: Session, name: str, description: str = ""
) -> Collection:
    name = name.strip()
    description = description.strip()
    existing = session.exec(
        select(Collection).where(
            Collection.name == name,
            Collection.is_deleted == False,
        )
    ).first()
    if existing:
        raise DuplicateCollectionNameError(name)

    collection = Collection(name=name, description=description)
    session.add(collection)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise DuplicateCollectionNameError(name)
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
    order: Literal["asc", "desc"] = "desc",
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
    sort_col = (
        Collection.created_at.asc() if order == "asc" else Collection.created_at.desc()
    )
    skip = (page - 1) * page_size
    items = session.exec(
        select(Collection)
        .where(*conditions)
        .order_by(sort_col)
        .offset(skip)
        .limit(page_size)
    ).all()
    collection_ids = [c.id for c in items]
    doc_counts, entity_counts = _fetch_counts(session, collection_ids)
    enriched = [
        {
            **c.model_dump(),
            "document_count": doc_counts.get(c.id, 0),
            "entity_count": entity_counts.get(c.id, 0),
        }
        for c in items
    ]
    return enriched, total


def update_collection_service(
    session: Session, collection: Collection, request: UpdateCollectionRequest
) -> Collection:
    new_name = request.name.strip() if request.name is not None else collection.name
    if new_name != collection.name:
        existing = session.exec(
            select(Collection).where(
                Collection.name == new_name,
                Collection.is_deleted == False,
            )
        ).first()
        if existing:
            raise DuplicateCollectionNameError(new_name)

    if request.name is not None:
        collection.name = request.name.strip()
    if request.description is not None:
        collection.description = request.description.strip()

    collection.updated_at = datetime.now(timezone.utc)
    session.add(collection)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise DuplicateCollectionNameError(new_name)
    session.refresh(collection)
    logger.info("Collection '%s' updated (id %s)", collection.name, collection.id)
    return collection


def delete_collection_service(session: Session, collection: Collection) -> bool:
    try:
        vectors_cleaned = cascade_delete_collection(session, collection)
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error("DB commit failed deleting collection %s: %s", collection.id, e)
        raise DatabaseError() from e
    logger.info("Collection '%s' (%s) deleted", collection.name, collection.id)
    return vectors_cleaned
