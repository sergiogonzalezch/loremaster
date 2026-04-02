from fastapi import FastAPI, UploadFile, File, HTTPException
from dotenv import load_dotenv
from app.api.routes import generate, documents, entities

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
app.include_router(documents.router, prefix="/api/v1/documents/ingest", tags=["documents"])
app.include_router(entities.router, prefix="/api/v1/entities", tags=["entities"])