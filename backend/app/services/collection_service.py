import logging

from sqlmodel import Session, select

from app.models.collections import Collection
from app.core.exceptions import DuplicateNameError
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
        raise DuplicateNameError("Collection name already exists")

    collection = Collection(name=name, description=description)
    session.add(collection)
    session.commit()
    session.refresh(collection)
    logger.info("Collection '%s' created with id %s", name, collection.id)
    return collection


def list_collections_service(session: Session) -> list[Collection]:
    stmt = select(Collection).where(Collection.is_deleted == False)
    return session.exec(stmt).all()


def delete_collection_service(session: Session, collection: Collection) -> bool:
    cascade_delete_collection(session, collection)
    session.commit()
    return True
