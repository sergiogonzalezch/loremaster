import uuid
from app.services.documents_db_mock import documents, collections

def create_collection_service(name: str, description: str = ""):
    collection_id = str(uuid.uuid4())
    collections[collection_id] = {
        "id": collection_id,
        "name": name,
        "description": description,
        "status": "active",
    }
    documents[collection_id] = {}
    return {"collection_id": collection_id, "name": name, "description": description} 