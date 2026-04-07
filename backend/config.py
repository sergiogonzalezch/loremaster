from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    project_name: str = "Lore Master API"
    environment: str = "local"

    # LLM (Ollama)

    ollama_model: str = "llama3.2:latest"
    ollama_base_url: Optional[str] = None

    # LLM parameters
    temperature: float = 0.7
    max_tokens: int = 500

    # # Vector database (Qdrant)
    # qdrant_url: Optional[str] = None

    # # Redis
    # redis_url: Optional[str] = None
    # cache_ttl: int = 3600  #
    # cache_threshold: float = 0.95

    # # ComfyUI
    # comfyui_url: Optional[str] = None
    # comfyui_url: Optional[str] = None
    # comfy_timeout: int = 60

    # # DB
    # database_url: str = "sqlite:///./loremaster.db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
