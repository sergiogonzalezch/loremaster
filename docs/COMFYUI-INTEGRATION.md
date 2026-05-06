# Plan de Integración ComfyUI (Detallado)

## 0. Prerrequisito — Template en Formato API

El template `flux2-klein-4b-template.json` está en **formato UI** (exportado con el botón "Save" de ComfyUI). El endpoint `/prompt` de ComfyUI **solo acepta formato API**. Son formatos incompatibles.

### Cómo exportar el template en formato API

1. Abrir ComfyUI en el navegador
2. Ir a **Settings → Developer Mode** → activar la opción
3. Cargar el workflow `flux2-klein-4b-template.json` (o el existente en ComfyUI)
4. En el menú superior, usar el botón **"Export (API)"** (aparece solo en modo Developer)
5. Guardar el archivo como:
   ```
   backend/app/domain/templates/flux2-klein-4b-api.json
   ```

### Diferencia entre formatos

**Formato UI** (actual, no sirve para la API):
```json
{
  "nodes": [
    { "id": 12, "type": "PrimitiveStringMultiline", "widgets_values": ["..."] }
  ]
}
```

**Formato API** (requerido por `/prompt`):
```json
{
  "12": {
    "class_type": "PrimitiveStringMultiline",
    "inputs": { "value": "el prompt aquí" }
  }
}
```

El archivo `flux2-klein-4b-template.json` se conserva como referencia visual pero **no se usa en el backend**.

---

## 1. Flujo Completo

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                          USUARIO                                                   │
│  frontend (Loremaster)                                                             │
│       │                                                                            │
│       ├─► clic "generar imágenes"                                                   │
│       │   (auto_prompt + final_prompt + batch_size)                                │
│       │                                                                           │
│       ▼                                                                            │
├───────────────────────────────────────────────────────────────────────────────────┤
│                          BACKEND (Loremaster)                                       │
│                                                                                   │
│  1. Validar content_id → confirmado                                               │
│  2. Validar prompts con content_guard                                              │
│  3. Cargar template JSON API (flux2-klein-4b-api.json)                           │
│  4. Inyectar final_prompt en el nodo "12" (PrimitiveStringMultiline)             │
│  5. Armar workflow JSON completo                                                   │
│  6. POST /prompt → ComfyUI                                                        │
│       │                                                                           │
│       ▼                                                                           │
├───────────────────────────────────────────────────────────────────────────────────┤
│                    COMFYUI (localhost:8188)                                        │
│                                                                                   │
│  1. Recibe workflow en formato API                                                │
│  2. Carga modelo UNET (flux-2-klein-4b)                                           │
│  3. Carga CLIP (qwen_3_4b_fp4_flux2)                                             │
│  4. Carga VAE (flux2-vae)                                                        │
│  5. Ejecuta nodos del subgraph "Configuracion"                                     │
│  6. Genera imagen → SaveImage node (id=3)                                         │
│  7. Guarda en /output/{timestamp}_{semilla}.png                                   │
│       │                                                                           │
│       ▼                                                                           │
├───────────────────────────────────────────────────────────────────────────────────┤
│                          BACKEND (Loremaster)                                       │
│                                                                                   │
│  1. Polling GET /history/{prompt_id} hasta status.status_str="success"            │
│  2. GET /view?filename=x.png&type=output → binary image                          │
│  3. Guardar en storage local (media_root)                                          │
│  4. Crear ImageGeneration + ImageRecord en DB                                   │
│  5. Retornar respuesta al frontend                                              │
└────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Archivos a Modificar

| Archivo | Cambio | Líneas |
|---------|--------|--------|
| `core/config.py` | Añadir `comfyui_url` | ~25 |
| `services/image_generation_service.py` | Añadir branch `elif backend == "comfyui"` | ~193-225 |

---

## 3. Nuevos Archivos a Crear

| Archivo | Propósito |
|---------|-----------|
| `engine/comfyui_client.py` | Cliente HTTP para ComfyUI |
| `domain/templates/flux2-klein-4b-api.json` | Template en formato API (exportar desde ComfyUI, ver Sección 0) |

---

## 4. Código Completo

### 4.1. Configuración (config.py)

**Ubicación**: `backend/app/core/config.py`

**Cambio**: Añadir variable `comfyui_url` después de `image_seed_base`:

```python
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
    image_prompt_tokens: int = 512
    image_backend: str = "mock"
    image_batch_size_default: int = 4
    image_width: int = 1024
    image_height: int = 1024
    image_seed_base: int = 42

    # ── ComfyUI (NUEVO) ───────────────────────────────────────────────────────────
    comfyui_url: str = "http://localhost:8188"

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

    secret_key: str = "your-secret-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    clerk_jwks_url: str = "https://your-org.clerk.accounts.dev/.well-known/jwks.json"
    clerk_audience: str = "your-audience-id"

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
```

---

### 4.2. Cliente ComfyUI (comfyui_client.py) - NUEVO

**Ubicación**: `backend/app/engine/comfyui_client.py`

**Nota**: El template debe estar en **formato API** (ver Sección 0). `inject_prompt()` usa claves string y el campo `inputs`, no `widgets_values`.

```python
# app/engine/comfyui_client.py
"""
Cliente HTTP para la API de ComfyUI.

Endpoints utilizados:
- POST /prompt → Envía workflow en formato API para ejecución
- GET /history/{prompt_id} → Consulta estado y resultados
- GET /view → Descarga imágenes generadas

El template debe estar en formato API (Export API desde ComfyUI con Developer Mode).
"""

import json
import time
from pathlib import Path

import httpx


class ComfyUIClient:
    """Cliente para interactuar con la API de ComfyUI."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        with httpx.Client(timeout=30.0) as client:
            response = client.request(method, url, **kwargs)
            response.raise_for_status()
            return response

    def queue_prompt(self, workflow: dict) -> str:
        """
        Envía un workflow en formato API para ejecución.

        Args:
            workflow: Workflow en formato API (dict con IDs de nodo como claves string)

        Returns:
            prompt_id: ID de la ejecución para tracking

        Raises:
            httpx.HTTPStatusError: Si el workflow es inválido o ComfyUI rechaza la petición
        """
        response = self._request(
            "POST",
            "prompt",
            json={"prompt": workflow},
        )
        data = response.json()

        if "prompt_id" in data:
            return data["prompt_id"]

        if "node_errors" in data:
            raise RuntimeError(f"Errores en nodos: {data['node_errors']}")

        raise RuntimeError(f"Respuesta inesperada de ComfyUI: {data}")

    def get_history(self, prompt_id: str) -> dict:
        """
        Obtiene el estado y resultados de una ejecución.

        Devuelve dict con:
        - status: "queued" | "running" | "completed" | "failed"
        - outputs: {node_id: {"images": [...]}} si completado
        - error: mensaje de error si falló
        """
        response = self._request("GET", f"history/{prompt_id}")
        data = response.json()

        if prompt_id not in data:
            return {"status": "queued", "outputs": {}}

        entry = data[prompt_id]
        status_str = entry.get("status", {}).get("status_str", "")

        if status_str == "success":
            return {"status": "completed", "outputs": entry.get("outputs", {})}

        if status_str == "error":
            messages = entry.get("status", {}).get("messages", [])
            return {"status": "failed", "error": str(messages)}

        return {"status": "running", "outputs": {}}

    def get_history_until_complete(
        self,
        prompt_id: str,
        timeout: int = 300,
        poll_interval: float = 2.0,
    ) -> dict:
        """
        Espera hasta que la ejecución complete (polling).

        Args:
            prompt_id: ID del prompt
            timeout: Timeout máximo en segundos (default 300 = 5 min)
            poll_interval: Intervalo de polling en segundos (default 2)

        Returns:
            Resultado de get_history() cuando status="completed"

        Raises:
            TimeoutError: Si excede el timeout
            RuntimeError: Si la ejecución falla
        """
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(
                    f"Timeout después de {timeout}s esperando generación ComfyUI"
                )

            result = self.get_history(prompt_id)
            status = result.get("status", "queued")

            if status == "completed":
                return result

            if status == "failed":
                raise RuntimeError(f"Generación falló: {result.get('error', 'Unknown error')}")

            time.sleep(poll_interval)

    def download_image(
        self,
        filename: str,
        subfolder: str = "",
        folder_type: str = "output",
    ) -> bytes:
        """
        Descarga una imagen generada.

        Args:
            filename: Nombre del archivo (del history)
            subfolder: Subcarpeta donde se guardó (del history)
            folder_type: "output", "input" o "temp" (default: "output")

        Returns:
            Bytes de la imagen
        """
        params = {"filename": filename, "type": folder_type}
        if subfolder:
            params["subfolder"] = subfolder

        response = self._request("GET", "view", params=params)
        return response.content

    def get_output_images(self, history_result: dict) -> list[dict]:
        """
        Extrae las imágenes generadas del resultado del history.

        Args:
            history_result: Resultado de get_history() con status="completed"

        Returns:
            Lista de dicts con: {"filename", "subfolder", "type", "node_id"}
        """
        outputs = history_result.get("outputs", {})
        images = []

        for node_id, node_output in outputs.items():
            if "images" in node_output:
                for img in node_output["images"]:
                    images.append({
                        "filename": img.get("filename"),
                        "subfolder": img.get("subfolder", ""),
                        "type": img.get("type", "output"),
                        "node_id": node_id,
                    })

        return images


# ── Funciones auxiliares para el template ───────────────────────────────────────────────


def load_template(template_name: str) -> dict:
    """
    Carga un template de workflow de ComfyUI en formato API desde JSON.

    Args:
        template_name: Nombre del archivo template (sin path). Debe ser formato API.

    Returns:
        Workflow JSON como dict

    Raises:
        FileNotFoundError: Si el template no existe
    """
    template_dir = Path(__file__).parent.parent / "domain" / "templates"
    template_path = template_dir / template_name

    if not template_path.exists():
        raise FileNotFoundError(f"Template no encontrado: {template_path}")

    with open(template_path, encoding="utf-8") as f:
        return json.load(f)


def inject_prompt(workflow: dict, prompt: str) -> dict:
    """
    Inyecta el prompt en el nodo 12 (PrimitiveStringMultiline) del workflow.

    El template debe estar en formato API de ComfyUI. En este formato, los nodos
    son claves string y el prompt se inyecta en inputs["value"], no en widgets_values.

    Args:
        workflow: Workflow en formato API (dict con claves string de IDs de nodo)
        prompt: Prompt del usuario a inyectar

    Returns:
        Copia del workflow con el prompt inyectado

    Raises:
        ValueError: Si el nodo 12 no existe en el template
    """
    workflow = json.loads(json.dumps(workflow))  # deep copy

    node = workflow.get("12")
    if node is None:
        raise ValueError(
            "Nodo 12 (PrimitiveStringMultiline) no encontrado en el template. "
            "Verificar que el template esté en formato API (ver Sección 0)."
        )

    node["inputs"]["value"] = prompt
    return workflow
```

---

### 4.3. Modificaciones en image_generation_service.py

**Ubicación**: `backend/app/services/image_generation_service.py`

**Cambio**: Reemplazar el bloque `else` del stub por el branch `"comfyui"` completo y añadir las funciones auxiliares. El código final del archivo:

```python
# app/services/image_generation_service.py

import uuid as _uuid
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.core.config import settings
from app.core.exceptions import DatabaseError, NoContextAvailableError
from app.domain.content_guard import check_user_input
from app.engine.image_prompt_builder import build_visual_prompt
from app.models.entities import Entity
from app.models.entity_content import EntityContent
from app.models.enums import ContentCategory, ContentStatus
from app.models.image_generation import (
    ImageGeneration,
    ImageRecord,
    BuildPromptResponse,
    GenerateImagesResponse,
    ImageResult,
    ImageRecordResponse,
    ImageGenerationListItem,
)

ALLOWED_IMAGE_CATEGORIES = {
    ContentCategory.extended_description,
    ContentCategory.backstory,
    ContentCategory.scene,
    ContentCategory.chapter,
}


def _get_confirmed_content(
    session: Session,
    entity: Entity,
    content_id: str,
) -> EntityContent | None:
    """Busca un EntityContent confirmado que pertenezca a la entidad."""
    return session.exec(
        select(EntityContent).where(
            EntityContent.id == content_id,
            EntityContent.entity_id == entity.id,
            EntityContent.collection_id == entity.collection_id,
            EntityContent.status == ContentStatus.confirmed,
            EntityContent.is_deleted == False,
        )
    ).first()


def _build_url(storage_path: str | None) -> str | None:
    """Construye la URL completa desde el storage_path."""
    if not storage_path:
        return None
    return f"{settings.storage_base_url}/{storage_path}"


def _generate_mock_images(
    entity: Entity,
    batch_size: int,
) -> list[tuple[str, str]]:
    """Genera URLs placeholder para el backend mock."""
    images = []
    for i in range(batch_size):
        image_id = str(_uuid.uuid4())
        placeholder_url = (
            f"https://placehold.co/{settings.image_width}x{settings.image_height}/1a1a2e/9d6fe8"
            f"?text={entity.name.replace(' ', '+')}+{i+1}"
        )
        images.append((image_id, placeholder_url))
    return images


def _save_comfyui_image(
    image_data: bytes,
    entity: Entity,
    generation_id: str,
    filename: str,
) -> str:
    """
    Guarda una imagen descargada de ComfyUI en el storage local.

    Returns:
        storage_path relativo (sin media_root) para guardar en DB
    """
    relative_path = f"{entity.collection_id}/{entity.id}/{generation_id}/{filename}"
    abs_dir = Path(settings.media_root) / entity.collection_id / entity.id / generation_id
    abs_dir.mkdir(parents=True, exist_ok=True)

    with open(abs_dir / filename, "wb") as f:
        f.write(image_data)

    return relative_path


def _generate_comfyui_images(
    session: Session,
    entity: Entity,
    content_id: str,
    auto_prompt: str,
    final_prompt: str,
    batch_size: int,
    category: str,
) -> tuple[str, list[ImageResult]]:
    """
    Genera imágenes usando ComfyUI.

    Returns:
        (generation_id, list[ImageResult])

    Raises:
        RuntimeError: Si la generación falla o no produce imágenes
    """
    from app.engine.comfyui_client import (
        ComfyUIClient,
        inject_prompt,
        load_template,
    )

    generation_id = str(_uuid.uuid4())

    # Crear ImageGeneration ANTES del loop de ImageRecord para satisfacer FK
    generation = ImageGeneration(
        id=generation_id,
        entity_id=entity.id,
        collection_id=entity.collection_id,
        content_id=content_id,
        category=category,
        auto_prompt=auto_prompt,
        final_prompt=final_prompt,
        prompt_token_count=len(final_prompt) // 4,
        batch_size=batch_size,
        backend="comfyui",
        width=settings.image_width,
        height=settings.image_height,
    )
    session.add(generation)

    client = ComfyUIClient(base_url=settings.comfyui_url)

    # El template debe estar en formato API (ver Sección 0 del doc de integración)
    workflow = load_template("flux2-klein-4b-api.json")
    workflow = inject_prompt(workflow, final_prompt)

    prompt_id = client.queue_prompt(workflow)
    result = client.get_history_until_complete(prompt_id)
    output_images = client.get_output_images(result)

    images_result: list[ImageResult] = []
    generated_count = 0

    for i, img_info in enumerate(output_images):
        if generated_count >= batch_size:
            break

        try:
            image_data = client.download_image(
                filename=img_info["filename"],
                subfolder=img_info["subfolder"],
                folder_type=img_info["type"],
            )
        except Exception:
            continue

        image_id = str(_uuid.uuid4())
        seed = settings.image_seed_base + i
        filename = f"{image_id}.png"

        storage_path = _save_comfyui_image(
            image_data=image_data,
            entity=entity,
            generation_id=generation_id,
            filename=filename,
        )

        record = ImageRecord(
            id=image_id,
            generation_id=generation_id,
            entity_id=entity.id,
            collection_id=entity.collection_id,
            seed=seed,
            storage_path=storage_path,
            image_url=_build_url(storage_path),
            filename=filename,
            extension="png",
            width=settings.image_width,
            height=settings.image_height,
            generation_ms=0,
        )
        session.add(record)

        images_result.append(
            ImageResult(
                id=image_id,
                image_url=_build_url(storage_path),
                seed=seed,
                width=settings.image_width,
                height=settings.image_height,
                generation_ms=0,
            )
        )

        generated_count += 1

    if generated_count == 0:
        raise RuntimeError("No se generaron imágenes desde ComfyUI")

    return generation_id, images_result


def build_prompt_service(
    session: Session,
    entity: Entity,
    content_id: str,
) -> BuildPromptResponse:
    """
    Construye el prompt automático sin guardar nada (efímero).

    Raises:
        NoContextAvailableError: Si el contenido no existe o no está confirmado
        ValueError: Si la categoría no es soportada para generación de imágenes
    """
    content = _get_confirmed_content(session, entity, content_id)
    if not content:
        raise NoContextAvailableError()

    if content.category not in ALLOWED_IMAGE_CATEGORIES:
        raise ValueError(
            f"Categoría '{content.category.value}' no soportada para generación de imágenes"
        )

    build_result = build_visual_prompt(
        entity_type=entity.type,
        confirmed_content=content.content,
        category=content.category,
        max_tokens=settings.image_prompt_tokens,
    )

    return BuildPromptResponse(
        auto_prompt=build_result["prompt"],
        token_count=build_result["token_count"],
    )


def generate_images_service(
    session: Session,
    entity: Entity,
    content_id: str,
    auto_prompt: str,
    final_prompt: str,
    batch_size: int,
) -> GenerateImagesResponse:
    """
    Genera un batch de imágenes.

    Raises:
        NoContextAvailableError: Si el contenido no existe o no está confirmado
        ValueError: Si image_backend no es "mock" ni "comfyui"
    """
    content = _get_confirmed_content(session, entity, content_id)
    if not content:
        raise NoContextAvailableError()

    check_user_input(auto_prompt)
    check_user_input(final_prompt)

    images_result: list[ImageResult] = []

    if settings.image_backend == "mock":
        mock_images = _generate_mock_images(entity, batch_size)
        generation_id = str(_uuid.uuid4())

        generation = ImageGeneration(
            id=generation_id,
            entity_id=entity.id,
            collection_id=entity.collection_id,
            content_id=content_id,
            category=content.category.value,
            auto_prompt=auto_prompt,
            final_prompt=final_prompt,
            prompt_token_count=len(auto_prompt) // 4,
            batch_size=batch_size,
            backend="mock",
            width=settings.image_width,
            height=settings.image_height,
        )
        session.add(generation)

        for i, (image_id, image_url) in enumerate(mock_images):
            record = ImageRecord(
                id=image_id,
                generation_id=generation_id,
                entity_id=entity.id,
                collection_id=entity.collection_id,
                seed=settings.image_seed_base + i,
                storage_path=None,
                image_url=image_url,
                filename=f"{image_id}.png",
                extension="png",
                width=settings.image_width,
                height=settings.image_height,
                generation_ms=0,
            )
            session.add(record)

            images_result.append(
                ImageResult(
                    id=image_id,
                    image_url=image_url,
                    seed=settings.image_seed_base + i,
                    width=settings.image_width,
                    height=settings.image_height,
                    generation_ms=0,
                )
            )

    elif settings.image_backend == "comfyui":
        generation_id, images_result = _generate_comfyui_images(
            session=session,
            entity=entity,
            content_id=content_id,
            auto_prompt=auto_prompt,
            final_prompt=final_prompt,
            batch_size=batch_size,
            category=content.category.value,
        )

    else:
        raise ValueError(
            f"Backend '{settings.image_backend}' no soportado. "
            "Usar: 'mock' o 'comfyui'"
        )

    try:
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        raise DatabaseError() from e

    return GenerateImagesResponse(
        generation_id=generation_id,
        auto_prompt=auto_prompt,
        final_prompt=final_prompt,
        batch_size=batch_size,
        backend=settings.image_backend,
        images=images_result,
    )


def delete_image_service(
    session: Session,
    entity: Entity,
    generation_id: str,
    image_id: str,
) -> None:
    """
    Elimina una imagen individual del batch (soft delete).

    Raises:
        NoContextAvailableError: Si la imagen no existe o no pertenece a la entidad
    """
    record = session.exec(
        select(ImageRecord).where(
            ImageRecord.id == image_id,
            ImageRecord.generation_id == generation_id,
            ImageRecord.entity_id == entity.id,
            ImageRecord.is_deleted == False,
        )
    ).first()

    if not record:
        raise NoContextAvailableError()

    record.is_deleted = True
    record.deleted_at = datetime.now(timezone.utc)

    # Bugfix: storage_path puede ser None en imágenes mock aunque el backend cambie
    if settings.image_backend != "mock" and record.storage_path:
        full_path = os.path.join(settings.media_root, record.storage_path)
        if full_path and os.path.exists(full_path):
            try:
                os.remove(full_path)
            except OSError:
                pass

    try:
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        raise DatabaseError() from e


def get_generation_service(
    session: Session,
    entity: Entity,
    generation_id: str,
) -> GenerateImagesResponse:
    """
    Obtiene una generación existente con sus imágenes.

    Raises:
        NoContextAvailableError: Si la generación no existe o no pertenece a la entidad
    """
    generation = session.exec(
        select(ImageGeneration).where(
            ImageGeneration.id == generation_id,
            ImageGeneration.entity_id == entity.id,
            ImageGeneration.is_deleted == False,
        )
    ).first()

    if not generation:
        raise NoContextAvailableError()

    records = session.exec(
        select(ImageRecord).where(
            ImageRecord.generation_id == generation_id,
            ImageRecord.is_deleted == False,
        )
    ).all()

    images = [
        ImageResult(
            id=r.id,
            image_url=_build_url(r.storage_path),
            seed=r.seed,
            width=r.width,
            height=r.height,
            generation_ms=r.generation_ms,
        )
        for r in records
    ]

    return GenerateImagesResponse(
        generation_id=generation.id,
        auto_prompt=generation.auto_prompt,
        final_prompt=generation.final_prompt,
        batch_size=generation.batch_size,
        backend=generation.backend,
        images=images,
    )


def list_generations_service(
    session: Session,
    entity: Entity,
) -> tuple[list, int]:
    """
    Lista todas las generaciones de imágenes de una entidad.

    Returns:
        (generations_list, total_count)
    """
    generations = session.exec(
        select(ImageGeneration)
        .where(
            ImageGeneration.entity_id == entity.id,
            ImageGeneration.collection_id == entity.collection_id,
            ImageGeneration.is_deleted == False,
        )
        .order_by(ImageGeneration.created_at.desc())
    ).all()

    result = []
    for gen in generations:
        records = session.exec(
            select(ImageRecord)
            .where(
                ImageRecord.generation_id == gen.id,
                ImageRecord.is_deleted == False,
            )
            .order_by(ImageRecord.seed.asc())
        ).all()

        images = [
            ImageRecordResponse(
                id=r.id,
                generation_id=r.generation_id,
                entity_id=r.entity_id,
                collection_id=r.collection_id,
                seed=r.seed,
                storage_path=r.storage_path,
                image_url=r.image_url,
                filename=r.filename,
                extension=r.extension,
                width=r.width,
                height=r.height,
                generation_ms=r.generation_ms,
                created_at=r.created_at,
                is_deleted=r.is_deleted,
                deleted_at=r.deleted_at,
            )
            for r in records
        ]

        result.append(
            ImageGenerationListItem(
                id=gen.id,
                entity_id=gen.entity_id,
                collection_id=gen.collection_id,
                content_id=gen.content_id,
                category=gen.category,
                auto_prompt=gen.auto_prompt,
                final_prompt=gen.final_prompt,
                batch_size=gen.batch_size,
                backend=gen.backend,
                width=gen.width,
                height=gen.height,
                created_at=gen.created_at,
                is_deleted=gen.is_deleted,
                images=images,
            )
        )

    return result, len(result)
```

---

## 5. Template JSON

**Ubicación**: `backend/app/domain/templates/`

| Archivo | Formato | Uso |
|---------|---------|-----|
| `flux2-klein-4b-template.json` | UI (ComfyUI "Save") | Referencia visual, carga en ComfyUI |
| `flux2-klein-4b-api.json` | API (ComfyUI "Export API") | **Usado por el backend** |

### Decisiones del archivo API generado

| Decisión | Detalle |
|----------|---------|
| **Nodos incluidos** | 16 nodos funcionales: 3, 8, 12, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108 |
| **Nodos excluidos** | SetNode/GetNode (helpers de UI), MarkdownNote (76), subgraph contenedor (14) |
| **Subgrafo expandido** | Los nodos 96-108 del subgraph "Configuracion" están flattened al nivel principal |
| **Punto de inyección** | Nodo `"12"` → `inputs.value` — compatible con `inject_prompt()` del plan |
| **Ruta del modelo** | `flux-klein-4b\\flux-2-klein-4b.safetensors` — ajustar separador en Linux/Mac |

El nodo de inyección en formato API:

```json
"12": {
  "class_type": "PrimitiveStringMultiline",
  "inputs": {
    "value": "placeholder — sobreescrito por inject_prompt()"
  }
}
```

El subgraph "Configuracion" (id=14) contiene:
- FLUX2-Klein-4B model — cfg=1.0 (no cambiar, es Distilled)
- CLIP: qwen_3_4b_fp4_flux2
- VAE: flux2-vae
- 4 steps (euler sampler, optimizado para Klein 4B)
- Resolución: 1024×1024

---

## 6. Manejo de Errores

| Error | Causa | Manejo |
|-------|-------|--------|
| `httpx.ConnectError` | ComfyUI no corre | Excepción sube al router → 503 |
| `httpx.HTTPStatusError` | Workflow inválido (400) o error interno (500) | `_request()` lo lanza vía `raise_for_status()` |
| `TimeoutError` | Generación lenta (>300s) | Excepción sube al router → 504 |
| `RuntimeError("Generación falló")` | `status_str="error"` en ComfyUI | Excepción con mensaje del log de ComfyUI |
| `RuntimeError("No se generaron imágenes")` | ComfyUI completó pero no produjo output | Excepción sube al router → 500 |
| `ValueError("Nodo 12 no encontrado")` | Template en formato UI en lugar de API | Error en startup/primer uso, revisar Sección 0 |

---

## 7. Pasos de Implementación

```
Step 0:  Exportar template en formato API (Prerrequisito manual)
        ├── Abrir ComfyUI → Settings → Developer Mode
        ├── Cargar workflow Flux2-Klein-4B
        └── Export (API) → guardar como flux2-klein-4b-api.json

Step 1:  config.py
        └── Añadir comfyui_url = "http://localhost:8188"

Step 2:  engine/comfyui_client.py (nuevo)
        ├── ComfyUIClient class
        ├── _request() con raise_for_status()
        ├── queue_prompt()
        ├── get_history() con status.status_str
        ├── get_history_until_complete()
        ├── download_image()
        ├── get_output_images()
        ├── load_template()
        └── inject_prompt() para formato API (clave "12", inputs["value"])

Step 3:  services/image_generation_service.py
        ├── Añadir _save_comfyui_image() con ruta relativa correcta
        ├── Añadir _generate_comfyui_images() con parámetros category y auto_prompt
        │   └── ImageGeneration ANTES del loop de ImageRecord (evitar FK violation)
        ├── Añadir branch "comfyui" en generate_images_service()
        └── Corregir delete_image_service(): añadir guard "and record.storage_path"

Step 4:  Tests
        ├── Mock ComfyUIClient con unittest.mock.patch
        └── test_ig_13_generate_batch_comfyui (ver Sección 8)

Step 5:  Integration test
        └── IMAGE_BACKEND=comfyui en .env + ComfyUI corriendo en localhost:8188
```

---

## 8. Tests

### Unit test con mock (sin ComfyUI)

```python
# tests/test_image_generation_service.py (añadir al final)

from unittest.mock import MagicMock, patch


def test_ig_13_generate_batch_comfyui(
    db_session: Session,
    sample_entity: Entity,
    sample_entity_content_confirmed: EntityContent,
):
    """IG-13: generate_images con backend comfyui guarda registros en DB."""

    fake_image_bytes = b"fake-png-bytes"

    mock_client = MagicMock()
    mock_client.queue_prompt.return_value = "prompt-uuid-123"
    mock_client.get_history_until_complete.return_value = {
        "status": "completed",
        "outputs": {
            "3": {
                "images": [
                    {"filename": "img_001.png", "subfolder": "", "type": "output"}
                ]
            }
        },
    }
    mock_client.get_output_images.return_value = [
        {"filename": "img_001.png", "subfolder": "", "type": "output", "node_id": "3"}
    ]
    mock_client.download_image.return_value = fake_image_bytes

    with (
        patch("app.services.image_generation_service.settings") as mock_settings,
        patch("app.engine.comfyui_client.ComfyUIClient", return_value=mock_client),
        patch("app.engine.comfyui_client.load_template", return_value={"12": {"inputs": {"value": ""}}}),
        patch("app.engine.comfyui_client.inject_prompt", side_effect=lambda w, p: w),
        patch("app.services.image_generation_service._save_comfyui_image", return_value="col/ent/gen/img.png"),
    ):
        mock_settings.image_backend = "comfyui"
        mock_settings.comfyui_url = "http://localhost:8188"
        mock_settings.image_width = 1024
        mock_settings.image_height = 1024
        mock_settings.image_seed_base = 42
        mock_settings.storage_base_url = "http://localhost:8000/media"

        result = generate_images_service(
            db_session,
            sample_entity,
            sample_entity_content_confirmed.id,
            auto_prompt="a warrior in blue armor",
            final_prompt="a warrior in blue armor, high quality",
            batch_size=1,
        )

    assert result.generation_id
    assert result.backend == "comfyui"
    assert len(result.images) == 1
    assert result.images[0].image_url is not None
```

---

## 9. Consideraciones Adicionales

- **Polling interval**: 2 segundos entre chequeos de status
- **Timeout**: 5 minutos (300s) por batch; ajustar si el hardware es lento
- **Storage**: Las imágenes se descargan del output de ComfyUI y se guardan en `media_root` local; ComfyUI conserva su copia en `/output`
- **Batch size**: ComfyUI genera 1 imagen por ejecución con este template. Para `batch_size > 1`, el backend lanza múltiples ejecuciones secuenciales
- **Semilla**: La semilla actual (`image_seed_base + i`) es fija. Para variación real en batches, usar `secrets.randbelow(2**32)`

---

## 10. Notas de API Key

> **Nota**: La API key de ComfyUI solo es necesaria cuando:
> - Se usan **Partner Nodes** (modelos pagos como Flux Pro, Kling, etc.)
> - Se accede desde fuera de localhost
>
> **No es necesaria** para:
> - ComfyUI local con modelos locales (Flux2-Klein)
> - RunPod con modelos subidos por el usuario

La API key se puede añadir más adelante si se usan Partner Nodes en RunPod.

---

## 11. Frontend — Sin Cambios Requeridos

El frontend **no requiere modificaciones** porque:

1. **API endpoint idéntico**: `POST /image-generation/generate` acepta los mismos parámetros (`content_id`, `auto_prompt`, `final_prompt`, `batch_size`)
2. **Componente existente**: `ImageGenerator.tsx` ya maneja el flujo completo
3. **Respuesta idéntica**: `GenerateImagesResponse` tiene la misma estructura sin importar el backend

### Mejora Opcional: Mostrar Backend en Uso

```tsx
// frontend/src/components/ImageGenerator.tsx
const [backend, setBackend] = useState<string>("mock");

const response = await generateImages(...);
setBackend(response.backend);

{backend === "comfyui" && (
  <Alert variant="success" className="mb-2">
    Generando con ComfyUI (Flux2-Klein)
  </Alert>
)}
```
