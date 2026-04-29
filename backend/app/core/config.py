from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    project_name: str = "Lore Master API"
    api_version: str = "1.0.0"
    environment: str = "local"
    allowed_origins: list[str] = ["http://localhost:3000"]

    # LLM (Ollama)
    ollama_model: str = "llama3.2:latest"
    ollama_base_url: str = "http://localhost:11434"

    # LLM parameters
    temperature: float = 0.7
    max_tokens: int = 2000
    max_concurrent_llm_calls: int = 1
    max_pending_contents: int = 5

    # Vector DB (Qdrant)
    qdrant_url: str = "http://localhost:6333"

    # Embeddings
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dims: int = 384
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k: int = 4
    rag_score_threshold: float = 0.5

    # Database (default SQLite for local dev; set DATABASE_URL in .env for PostgreSQL)
    database_url: str = "sqlite:///./loremaster.db"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
