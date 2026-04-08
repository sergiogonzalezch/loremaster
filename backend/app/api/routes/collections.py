from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.collection_service import create_collection_service
from app.services.documents_db_mock import collections

router = APIRouter(prefix="/collections", tags=["collections"])


class CreateCollectionRequest(BaseModel):
    name: str
    description: str = ""


@router.post("/", status_code=201)
async def create_collection(request: CreateCollectionRequest):
    existing_names = {c["name"] for c in collections.values()}
    if request.name in existing_names:
        raise HTTPException(status_code=409, detail="Collection name already exists")
    response = create_collection_service(request.name, request.description)
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
    if collection_id not in collections:
        raise HTTPException(status_code=404, detail="Collection not found")
    del collections[collection_id]
    return {"message": f"Collection {collection_id} deleted successfully"}
