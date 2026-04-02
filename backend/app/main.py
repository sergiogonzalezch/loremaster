from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from app.api.routes import generate

# from qdrant_client import QdrantClient
# from qdrant_client.http.models import Distance, VectorParams
# import shutil
import os

load_dotenv()
PROJECT_NAME = os.getenv("PROJECT_NAME", "Lore Master API")
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

app = FastAPI(
    title=PROJECT_NAME,
    description="API for managing lore and knowledge base",
    version="1.0.0",
)

@app.get("/")
def health():
    return {"status": "ok", "environment": ENVIRONMENT}

app.include_router(generate.router, prefix="/api/v1/generate/text", tags=["generate"])