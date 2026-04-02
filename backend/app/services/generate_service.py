from app.services.documents_db_mock import documents

def generate_response(query:str):
    if not documents: 
        return {"error": "No hay documentos disponibles para procesar la consulta."}

    doc = list(documents.values())[0]

    return {
        "query": query,
        "sources": [{"filename": doc["filename"]}],
        "response": f"Respuesta generada para la consulta: '{query}' utilizando el documento '{doc['filename']}'"
    }