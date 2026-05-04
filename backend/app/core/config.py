from pydantic import model_validator
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

    # Image generation
    image_prompt_tokens: int = 150
    image_backend: str = "mock"
    image_batch_size_default: int = 4
    image_width: int = 1024
    image_height: int = 1024
    image_seed_base: int = 42

    # Storage
    media_root: str = "./media"
    storage_backend: str = "local"  # local | s3 | r2
    storage_base_url: str = "http://localhost:8000/media"

    # Vector DB (Qdrant)
    qdrant_url: str = "http://localhost:6333"

    # Embeddings
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dims: int = 384
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k: int = 4
    rag_score_threshold: float = 0.3

    # Database (default SQLite for local dev; set DATABASE_URL in .env for PostgreSQL)
    database_url: str = "sqlite:///./loremaster.db"

    @model_validator(mode="after")
    def _validate_cors(self) -> "Settings":
        if "*" in self.allowed_origins:
            raise ValueError(
                "ALLOWED_ORIGINS no puede contener '*' cuando allow_credentials=True. "
                "Especifica los orígenes concretos en .env"
            )
        return self

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
