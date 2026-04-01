from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
import shutil
import os

load_dotenv()
PROJECT_NAME = os.getenv("PROJECT_NAME", "Lore Master API")
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

# --- CONEXIÓN A QDRANT SIN DOCKER ---
# Al usar 'path', Qdrant guardará los vectores en una carpeta local.
# (Si quisieras que se borrara al apagar, usarías QdrantClient(":memory:"))
qdrant = QdrantClient(path="./qdrant_data")

COLLECTION_NAME = "lore_mundo"

# Crear la "tabla" (colección) de vectores si no existe al arrancar
if not qdrant.collection_exists(COLLECTION_NAME):
    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        # size=384 es el tamaño estándar para modelos de embedding pequeños de prueba
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )

app = FastAPI(title=PROJECT_NAME, version="0.1.0")

os.makedirs("temp_uploads", exist_ok=True)

class TextGenerationRequest(BaseModel):
    query: str
    
class TextGenerationResponse(BaseModel):
    response: str
    sources: list[str]

@app.get("/health", tags=["Sistema"])
def health_check():
    # Verificamos que Qdrant esté respondiendo
    colecciones = qdrant.get_collections()
    return {
        "status": "ok", 
        "qdrant_collections": [c.name for c in colecciones.collections]
    }

@app.post("/api/v1/documents/ingest", status_code=201, tags=["Documentos"])
async def ingest_document(file: UploadFile = File(...)):
    if file.content_type not in ["application/pdf", "text/plain"]:
        raise HTTPException(status_code=400, detail="Formato inválido.")
    
    file_path = f"temp_uploads/{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {
        "doc_id": "draft-123", 
        "filename": file.filename, 
        "status": "Archivo guardado, listo para vectorizar en Qdrant"
    }

@app.post("/api/v1/generate/text", response_model=TextGenerationResponse, tags=["Generación"])
def generate_text(request: TextGenerationRequest):
    return TextGenerationResponse(
        response=f"Respuesta generada para: '{request.query}'.",
        sources=["draft-chunk-1"]
    )