from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):

    project_name: str = "Lore Master API"
    environment: str = "local"

    # LLM (Ollama)
    ollama_model: str = "llama3.2:latest"
    ollama_base_url: Optional[str] = None

    # LLM parameters
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=500, gt=0, le=8192)

    # Vector DB (Qdrant)
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    qdrant_collection: str = "loremaster"

    # Embeddings
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    chunk_size: int = Field(default=512, gt=0)
    chunk_overlap: int = Field(default=50, ge=0)

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl: int = 3600
    cache_threshold: float = 0.95

    # Database
    database_url: str = "sqlite:///./loremaster.db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
