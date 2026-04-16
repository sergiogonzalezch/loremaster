import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import create_db_and_tables
from config import settings
from app.api.routes import generate, documents, collections, entities, entity_text_draft

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        create_db_and_tables()
    except Exception as e:
        logger.critical("Database initialization failed, aborting startup: %s", e)
        raise
    yield


app = FastAPI(
    title=settings.project_name,
    version=settings.api_version,
    description="API for managing lore and knowledge base",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"service": settings.project_name, "version": settings.api_version}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


app.include_router(collections.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(generate.router, prefix="/api/v1")
app.include_router(entities.router, prefix="/api/v1")
app.include_router(entity_text_draft.router, prefix="/api/v1")
