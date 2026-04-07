from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    project_name: str = "Lore Master API"
    environment: str = "local"
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 500
    model_name: str = "gpt-4o-mini"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()