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

        ollama_model: Modelo de Ollama para LLM (generación de contenido).
        ollama_base_url: URL base del servidor Ollama.
        ollama_excluded_models: Prefijos de modelos excluidos del endpoint GET /models.
            Útil para ocultar modelos incompatibles con el pipeline RAG (ej. modelos
            con thinking mode que emiten <think> tags y rompen el parser de respuestas).
        image_prompt_model: Modelo de Ollama para extracción de atributos visuales.

        temperature: Temperatura del LLM (creatividad).
        max_tokens: Máximo de tokens en respuestas del LLM (Ollama num_predict, output).
        max_concurrent_llm_calls: Semáforo de llamadas simultáneas a Ollama (default 1).
        max_pending_contents: Máximo de contenidos en estado pending por entidad/categoría.
        rate_limit_per_minute: Límite de requests por minuto por IP (middleware global).

        image_prompt_tokens: Tokens máximos para prompts de imagen (truncate hacia ComfyUI).
        image_backend: Backend de generación (mock para tests/local, comfyui en producción).
        image_batch_size_default: Tamaño de batch por defecto.
        image_width: Ancho de imagen generada.
        image_height: Alto de imagen generado.
        image_seed_base: Semilla base para generación.

        comfyui_url: URL del servidor ComfyUI.
        comfyui_timeout: Segundos máximos para que ComfyUI genere una imagen.
        comfyui_request_timeout: Timeout en segundos para cada request HTTP a ComfyUI.

        media_root: Directorio raíz para archivos multimedia.
        storage_backend: Backend de almacenamiento (local, s3, r2).
        storage_base_url: URL base para servir archivos multimedia.
        profile_image_max_size_mb: Tamaño máximo de avatar en MB.
        document_max_upload_mb: Tamaño máximo de documento subido en MB.
        document_extraction_timeout_seconds: Timeout para extracción de texto de documentos.

        qdrant_url: URL del servidor Qdrant.

        embedding_model: Modelo de embeddings para RAG.
        embedding_dims: Dimensiones del vector de embedding.
        chunk_size: Tamaño de chunk en caracteres.
        chunk_overlap: Solapamiento entre chunks.
        top_k: Chunks de contexto recuperados por RAG.
        rag_score_threshold: Umbral de score para RAG.
        max_pdf_pages: Límite de páginas para PDFs (prevención de PDF bombs).

        secret_key: Clave secreta para firmar JWT.
        algorithm: Algoritmo de firma JWT.
        access_token_expire_minutes: Duración del token JWT en minutos.

        clerk_jwks_url: URL JWKS de Clerk para producción.
        clerk_audience: Audience de Clerk.

        cookie_access_name: Nombre de la cookie HttpOnly que contiene el JWT local.
        cookie_csrf_name: Nombre de la cookie CSRF (double-submit pattern).
        cookie_secure: True en producción/demo (HTTPS obligatorio). False solo en local.
        cookie_samesite: Política SameSite (Strict | Lax | None).
        cookie_domain: Dominio de las cookies; None usa el dominio actual del request.
        cookie_path: Path de las cookies (default /).

        database_url: URL de conexión a la base de datos.

    """

    project_name: str = "Lore Master API"
    api_version: str = "1.0.0"
    environment: str = "local"
    log_level: str = "INFO"
    allowed_origins: list[str] = ["http://localhost:3000"]

    # LLM - Ollama
    ollama_model: str = "llama3.2:latest"
    ollama_base_url: str = "http://localhost:11434"
    ollama_excluded_models: list[str] = []

    # LLM parameters
    temperature: float = 0.7
    max_tokens: int = 2000
    max_concurrent_llm_calls: int = 1
    max_pending_contents: int = 5

    # Llama Guard — capa semántica de moderación (fail-open)
    llama_guard_enabled: bool = False
    llama_guard_model: str = "llama-guard3:8b"
    llama_guard_timeout: float = 5.0
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 30  # Rate limiting base (req/min)
    rate_limit_llm_per_minute: int = 5  # Endpoints que invocan Ollama
    rate_limit_image_per_minute: int = 3  # Endpoints de generación de imagen
    redis_url: str = "redis://localhost:6379"

    # Image generation
    image_prompt_tokens: int = 512
    image_prompt_model: str = "mistral:latest"
    image_backend: str = "comfyui"
    image_batch_size_default: int = 4
    image_width: int = 1024
    image_height: int = 1024
    image_seed_base: int = 42

    # ComfyUI
    comfyui_url: str = "http://localhost:8188"
    comfyui_timeout: int = 300
    comfyui_request_timeout: float = 30.0
    health_check_timeout_seconds: float = 2.0  # timeout para health checks de Qdrant y Ollama
    ollama_models_timeout_seconds: float = 5.0  # timeout para GET /api/tags de Ollama

    # Storage
    media_root: str = "./media"
    storage_backend: str = "local"  # local | s3
    storage_base_url: str = "http://localhost:8000/media"
    s3_endpoint_url: str | None = None  # None = AWS real; URL = Floci/MinIO/R2
    s3_bucket: str = "loremaster-media"
    s3_region: str = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    profile_image_max_size_mb: float = 10.0
    document_max_upload_mb: int = 50
    document_extraction_timeout_seconds: int = 30
    document_event_stream_max_seconds: int = 300  # duración máxima del SSE de documentos

    # Vector DB (Qdrant)
    qdrant_url: str = "http://localhost:6333"
    qdrant_retry_attempts: int = 3  # reintentos al borrar vectores
    qdrant_retry_delay_seconds: float = 0.5  # segundos entre reintentos

    # Embeddings
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dims: int = 384
    chunk_size: int = 400
    chunk_overlap: int = 150
    top_k: int = 4
    rag_score_threshold: float = 0.3
    max_pdf_pages: int = 100  # Prevención de PDF bombs

    # Auth - JWT
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15  # corto; el refresh token renueva la sesión
    refresh_token_expire_days: int = 7

    # Cookies Security
    cookie_access_name: str = "access_token"
    cookie_refresh_name: str = "refresh_token"
    cookie_csrf_name: str = "csrf_token"
    cookie_secure: bool = False  # True en producción/demo (HTTPS)
    cookie_samesite: str = "Strict"
    cookie_domain: str | None = None
    cookie_path: str = "/"

    # RunPod Serverless — GPU cloud para generación de imágenes
    runpod_api_key: str | None = None
    runpod_endpoint_id: str | None = None

    # Clerk - production
    clerk_jwks_url: str = "https://your-org.clerk.accounts.dev/.well-known/jwks.json"
    clerk_audience: str = "your-audience-id"

    # Database (default SQLite for local dev; set DATABASE_URL in .env for PostgreSQL)
    database_url: str = "sqlite:///./loremaster.db"

    @model_validator(mode="after")
    def _validate_cors(self) -> "Settings":
        """Valida configuraciones críticas de seguridad.

        Verifica que:
        - CORS no use '*' cuando allow_credentials=True.
        - SECRET_KEY tenga al menos 32 caracteres en entornos no locales.
        - ALLOWED_ORIGINS use HTTPS en producción.
        - ENVIRONMENT sea un valor válido.
        """
        if "*" in self.allowed_origins:
            msg = "ALLOWED_ORIGINS no puede contener '*' cuando allow_credentials=True. Especifica los orígenes concretos en .env"
            raise ValueError(
                msg,
            )
        if self.environment != "local" and len(self.secret_key) < 32:
            msg = f"SECRET_KEY debe tener al menos 32 caracteres en entornos no locales. Actual: {len(self.secret_key)} caracteres"
            raise ValueError(
                msg,
            )
        if self.environment in ("production", "demo"):
            for origin in self.allowed_origins:
                is_localhost = "localhost" in origin or "127.0.0.1" in origin
                if not origin.startswith("https://") and not is_localhost:
                    msg = f"ALLOWED_ORIGINS en {self.environment} debe usar HTTPS: '{origin}'. Cambia a https:// para entorno {self.environment}"
                    raise ValueError(
                        msg,
                    )
        valid_envs = {"local", "demo", "production", "test"}
        if self.environment not in valid_envs:
            msg = f"ENVIRONMENT debe ser uno de: {', '.join(valid_envs)}. Valor recibido: '{self.environment}'"
            raise ValueError(
                msg,
            )
        if self.environment in ("production", "demo") and not self.cookie_secure:
            msg = "COOKIE_SECURE debe ser True en entornos production/demo. " "Añade COOKIE_SECURE=true al .env de producción."
            raise ValueError(msg)
        if self.environment == "local" and not os.environ.get("ENVIRONMENT"):
            warnings.warn(
                "ENVIRONMENT no está definida en el entorno. "
                "Ejecutando en modo 'local' con guardas de seguridad relajadas. "
                "Define ENVIRONMENT=local explícitamente para confirmar la intención.",
                stacklevel=2,
            )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
