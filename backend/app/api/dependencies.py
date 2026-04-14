from fastapi import Depends, HTTPException
from sqlmodel import Session

from app.database import get_session
from app.models.collections import Collection


def get_valid_collection(
    collection_id: str,
    session: Session = Depends(get_session),
) -> Collection:
    collection = session.get(Collection, collection_id)
    if not collection or collection.is_deleted:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection