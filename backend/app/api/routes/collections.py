from fastapi import APIRouter, HTTPException
from app.services.collection_service import create_collection_service

from app.services.documents_db_mock import collections

router = APIRouter(prefix="/collections", tags=["collections"])


@router.post("/create")
async def create_collection(name: str, description: str = ""):
    response = create_collection_service(name, description)
    return {"response": response, "status": "success"}


@router.get("/list")
async def get_collections():
    return list(collections.values())


@router.get("/{collection_id}")
async def get_collection(collection_id: str):
    collection = collections.get(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection
