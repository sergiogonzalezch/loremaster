from fastapi import Depends, HTTPException
from sqlmodel import Session

from app.database import engine
from app.models.collections import Collection


def get_valid_collection(collection_id: str) -> Collection:
    with Session(engine) as session:
        collection = session.get(Collection, collection_id)
        if not collection or collection.is_deleted:
            raise HTTPException(status_code=404, detail="Collection not found")
        return collection
