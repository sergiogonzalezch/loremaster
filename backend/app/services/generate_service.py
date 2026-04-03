from app.services.documents_db_mock import documents

def generate_response(query:str, collection_id: str = None):
    if not documents: 
        return {"error": "No hay documentos disponibles para procesar la consulta."}

    if collection_id:
        collection = documents.get(collection_id)
    else:
        collection = list(documents.values())[0]

    return {
        "query": query,
        "sources": [{"filename": collection['name']}],
        "message": f"Respuesta generada para la consulta: '{query}' utilizando la colección '{collection['name']}'"
    }