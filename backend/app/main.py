from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import generate, documents, collections, entities
from app.database import create_db_and_tables
from config import settings
# Agregar import
from app.api.routes import generate, documents, collections, entities, entity_text_draft

# Agregar router

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title=settings.project_name,
    description="API for managing lore and knowledge base",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
def read_root():
    return {
        "service": "AI Multimodal API",
        "version": "1.0.0",
        "model": settings.ollama_model,
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "environment": settings.environment}


app.include_router(collections.router, prefix="/api/v1", tags=["collections"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(generate.router, prefix="/api/v1", tags=["generate"])
app.include_router(entities.router, prefix="/api/v1", tags=["entities"])
app.include_router(entity_text_draft.router, prefix="/api/v1", tags=["entity-drafts"])
