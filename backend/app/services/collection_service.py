import uuid
from app.services.documents_db_mock import documents

def create_collection_service(name: str, description: str = ""):
    collection_id = str(uuid.uuid4())
    documents[collection_id] = {
        "id": collection_id,
        "name": name,
        "description": description,
        "status": "active",
    }
    return {"collection_id": collection_id, "name": name, "description": description} 