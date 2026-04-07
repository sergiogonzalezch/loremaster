from fastapi import FastAPI
from app.api.routes import generate, documents, collections
from config import settings
app = FastAPI(
    title=settings.project_name,
    description="API for managing lore and knowledge base",
    version="1.0.0",
)


@app.get("/")
def read_root():
     return {
        "service": "AI Multimodal API",
        "version": "1.0.0",
        "model": settings.model_name,
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "environment": settings.environment}


app.include_router(collections.router, prefix="/api/v1", tags=["collections"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(generate.router, prefix="/api/v1", tags=["generate"])
# app.include_router(entities.router, prefix="/api/v1", tags=["entities"])
