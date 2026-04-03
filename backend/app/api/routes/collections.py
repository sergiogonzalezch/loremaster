from fastapi import APIRouter, HTTPException
from app.services.collection_service import create_collection_service

from app.services.documents_db_mock import collections

router = APIRouter(prefix="/collections", tags=["collections"])


@router.post("/")
async def create_collection(name: str, description: str = ""):
    response = create_collection_service(name, description)
    return {"response": response, "status": "success"}


@router.get("/")
async def get_collections():
    return list(collections.values())


@router.get("/{collection_id}")
async def get_collection(collection_id: str):
    collection = collections.get(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection

@router.delete("/{collection_id}")
async def delete_collection(collection_id: str):
    if collection_id in collections:
        del collections[collection_id]
        return {"message": f"Collection {collection_id} deleted successfully"}
    raise HTTPException(status_code=404, detail="Collection not found")