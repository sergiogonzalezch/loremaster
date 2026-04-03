from app.services.documents_db_mock import documents

def generate_response(query:str, doc_id: str = None):
    if not documents: 
        return {"error": "No hay documentos disponibles para procesar la consulta."}

    if doc_id:
        doc = documents.get(doc_id)
    else:
        doc = list(documents.values())[0]

    return {
        "query": query,
        "sources": [{"filename": doc["filename"]}],
        "message": f"Respuesta generada para la consulta: '{query}' utilizando el documento '{doc['filename']}'"
    }