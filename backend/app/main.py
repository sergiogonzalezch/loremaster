from fastapi import FastAPI
from dotenv import load_dotenv
from app.api.routes import generate, documents, collections

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
def read_root():
    return {"message": f"Welcome to {PROJECT_NAME} API!"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "environment": ENVIRONMENT}

app.include_router(collections.router, prefix="/api/v1", tags=["collections"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(generate.router, prefix="/api/v1", tags=["generate"])
# app.include_router(entities.router, prefix="/api/v1", tags=["entities"])