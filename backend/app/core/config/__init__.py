"""Configuración de la aplicación usando Pydantic Settings.

Carga variables de entorno desde archivo .env y valida valores críticos
como CORS y secret_key en entornos no locales.
"""

import os
import warnings

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración centralizada de la aplicación Lore Master.

    Lee variables de entorno desde .env y aplica valores por defecto
    para desarrollo local.

    Attributes:
        project_name: Nombre del proyecto.
        api_version: Versión de la API.
        environment: Entorno de ejecución (local, demo, production, test).
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR).
        allowed_origins: Lista de orígenes permitidos para CORS.

        ollama_model: Modelo de Ollama para LLM.
        ollama_base_url: URL base del servidor Ollama.

        temperature: Temperatura del LLM (creatividad).
        max_tokens: Máximo de tokens en respuestas del LLM.
        max_concurrent_llm_calls: Límite de llamadas concurrentes al LLM.
        max_pending_contents: Máximo de contenidos pendientes por entidad.
        rate_limit_per_minute: Límite de requests por minuto por usuario (P-2).

        image_prompt_tokens: Tokens máximos para prompts de imagen.
        image_backend: Backend de generación de imágenes (mock, comfyui).
        image_batch_size_default: Tamaño de batch por defecto.
        image_width: Ancho de imagen generada.
        image_height: Alto de imagen generado.
        image_seed_base: Semilla base para generación.

        comfyui_url: URL del servidor ComfyUI.

        media_root: Directorio raíz para archivos multimedia.
        storage_backend: Backend de almacenamiento (local, s3, r2).
        storage_base_url: URL base para servir archivos multimedia.
        profile_image_max_size_mb: Tamaño máximo de avatar en MB.

        qdrant_url: URL del servidor Qdrant.

        embedding_model: Modelo de embeddings para RAG.
        embedding_dims: Dimensiones del vector de embedding.
        chunk_size: Tamaño de chunk en caracteres.
        chunk_overlap: Solapamiento entre chunks.
        top_k: Chunks de contexto recuperados por RAG.
        rag_score_threshold: Umbral de score para RAG.
        max_pdf_pages: Límite de páginas para PDFs (H-7, prevención de PDF bombs).

        secret_key: Clave secreta para firmar JWT (C-7).
        algorithm: Algoritmo de firma JWT.
        access_token_expire_minutes: Duración del token JWT en minutos.

        clerk_jwks_url: URL JWKS de Clerk para producción.
        clerk_audience: Audience de Clerk.

        database_url: URL de conexión a la base de datos.

    """

    project_name: str = "Lore Master API"
    api_version: str = "1.0.0"
    environment: str = "local"
    log_level: str = "INFO"
    allowed_origins: list[str] = ["http://localhost:3000"]

    # LLM (Ollama)
    ollama_model: str = "llama3.2:latest"
    ollama_base_url: str = "http://localhost:11434"

    # LLM parameters
    temperature: float = 0.7
    max_tokens: int = 2000
    max_concurrent_llm_calls: int = 1
    max_pending_contents: int = 5
    rate_limit_per_minute: int = 30  # P-2: Rate limiting (30 req/min)

    # Image generation
    image_prompt_tokens: int = 512
    image_backend: str = "mock"
    image_batch_size_default: int = 4
    image_width: int = 1024
    image_height: int = 1024
    image_seed_base: int = 42

    # ComfyUI
    comfyui_url: str = "http://localhost:8188"

    # Storage
    media_root: str = "./media"
    storage_backend: str = "local"  # local | s3 | r2
    storage_base_url: str = "http://localhost:8000/media"
    profile_image_max_size_mb: float = 5.0

    # Vector DB (Qdrant)
    qdrant_url: str = "http://localhost:6333"

    # Embeddings
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dims: int = 384
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k: int = 4
    rag_score_threshold: float = 0.3
    max_pdf_pages: int = 100  # H-7: Prevención de PDF bombs

    # Auth (JWT)
    secret_key: str  # C-7: Requerida. Generar con: python -c "import secrets; print(secrets.token_hex(32))"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Cookies (H-13, H-14, M-17)
    cookie_access_name: str = "access_token"
    cookie_csrf_name: str = "csrf_token"
    cookie_secure: bool = False  # True en producción/demo (HTTPS)
    cookie_samesite: str = "Strict"
    cookie_domain: str | None = None
    cookie_path: str = "/api/v1"

    # Clerk (production)
    clerk_jwks_url: str = "https://your-org.clerk.accounts.dev/.well-known/jwks.json"
    clerk_audience: str = "your-audience-id"

    # Database (default SQLite for local dev; set DATABASE_URL in .env for PostgreSQL)
    database_url: str = "sqlite:///./loremaster.db"

    @model_validator(mode="after")
    def _validate_cors(self) -> "Settings":
        """Valida configuraciones críticas de seguridad.

        Verifica que:
        - CORS no use '*' cuando allow_credentials=True.
        - SECRET_KEY tenga al menos 32 caracteres en entornos no locales (C-7).
        - ALLOWED_ORIGINS use HTTPS en producción.
        - ENVIRONMENT sea un valor válido.
        """
        if "*" in self.allowed_origins:
            raise ValueError(
                "ALLOWED_ORIGINS no puede contener '*' cuando allow_credentials=True. "
                "Especifica los orígenes concretos en .env"
            )
        if self.environment != "local" and len(self.secret_key) < 32:  # noqa: PLR2004
            raise ValueError(
                f"SECRET_KEY debe tener al menos 32 caracteres en entornos no locales. "
                f"Actual: {len(self.secret_key)} caracteres"
            )
        if self.environment in ("production", "demo"):
            for origin in self.allowed_origins:
                if not origin.startswith("https://"):
                    raise ValueError(
                        f"ALLOWED_ORIGINS en {self.environment} debe usar HTTPS: '{origin}'. "
                        f"Cambia a https:// para entorno {self.environment}"
                    )
        valid_envs = {"local", "demo", "production", "test"}
        if self.environment not in valid_envs:
            raise ValueError(
                f"ENVIRONMENT debe ser uno de: {', '.join(valid_envs)}. "
                f"Valor recibido: '{self.environment}'"
            )
        if self.environment == "local" and not os.environ.get("ENVIRONMENT"):
            warnings.warn(
                "ENVIRONMENT no está definida en el entorno. "
                "Ejecutando en modo 'local' con guardas de seguridad relajadas. "
                "Define ENVIRONMENT=local explícitamente para confirmar la intención (M-12).",
                stacklevel=2,
            )
        return self

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
