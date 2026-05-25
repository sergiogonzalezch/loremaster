# Plan — Semana 9: Dockerfile + Deuda técnica

## Contexto

La rama `feature/week-9` no tiene implementación nueva. Los 5 objetivos de la semana están pendientes. El `backend/Dockerfile` es el bloqueante de todo: sin él no hay compose completo, ni CI, ni deploy. Esta semana también resuelve el HTTP 429 en el semáforo LLM y la deuda técnica de índices FK.

**Stack a containerizar:** FastAPI + uvicorn, Python 3.11, deps en `requirements.txt`. Migraciones Alembic corren en startup via `lifespan.py`. El embedding model (`paraphrase-multilingual-MiniLM-L12-v2`, ~90 MB) se descarga de HuggingFace al primer uso.

---

## Tarea 1 — `backend/Dockerfile` (multi-stage)

**Archivo:** `backend/Dockerfile`

```
Stage 1 — builder
  FROM python:3.11-slim AS builder
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
  # Pre-descargar el embedding model para evitar cold-start en primer deploy
  RUN PYTHONPATH=/install/lib/python3.11/site-packages \
      python -c "from sentence_transformers import SentenceTransformer; \
                 SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

Stage 2 — runtime
  FROM python:3.11-slim
  # Crear usuario no-root (buenas prácticas de seguridad)
  RUN useradd -m -u 1000 loremaster
  WORKDIR /app
  COPY --from=builder /install /usr/local
  # El cache del modelo queda en /root/.cache del builder — copiarlo al runtime user
  COPY --from=builder /root/.cache /home/loremaster/.cache
  RUN chown -R loremaster:loremaster /home/loremaster/.cache /app
  COPY . .
  USER loremaster
  EXPOSE 8000
  CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Notas:**
- `--prefix=/install` instala deps en un directorio separado para la copia limpia al runtime stage.
- El modelo HuggingFace cachea en `~/.cache/huggingface/hub/`. Al copiar el cache del builder al runtime user, el primer request no descarga nada.
- Sin `--reload` en producción (necesita uvicorn workers, pero con semáforo=1 no hay ventaja de múltiples workers para LLM).
- `.dockerignore` a crear: `venv/`, `*.db`, `media/`, `tests/`, `evaluations/`, `__pycache__/`, `.env`.

---

## Tarea 2 — `docker-compose.prod.yml` — añadir servicio `app`

**Archivo:** `backend/docker-compose.prod.yml`

Añadir el servicio `app` al compose existente (que ya tiene qdrant, redis, postgres):

```yaml
  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: loremaster-api
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      qdrant:
        condition: service_started  # qdrant no tiene healthcheck aún
    ports:
      - "127.0.0.1:8000:8000"
    environment:
      ENVIRONMENT: demo
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      QDRANT_URL: http://qdrant:6333
      REDIS_URL: redis://redis:6379
      OLLAMA_BASE_URL: http://host.docker.internal:11434
      COMFYUI_URL: http://host.docker.internal:8188
      MEDIA_ROOT: /app/media
      STORAGE_BASE_URL: ${STORAGE_BASE_URL}
      SECRET_KEY: ${SECRET_KEY:?SECRET_KEY requerida}
      COOKIE_SECURE: "true"
      ALLOWED_ORIGINS: ${ALLOWED_ORIGINS}
    volumes:
      - media_data:/app/media
    extra_hosts:
      - "host.docker.internal:host-gateway"
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:8000/health', timeout=5)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    networks:
      - loremaster

volumes:
  qdrant_data:
  postgres_data:
  media_data:    # nuevo
```

**Notas:**
- `host.docker.internal` con `extra_hosts: host-gateway` funciona en Linux Docker. Permite acceder a Ollama y ComfyUI que corren en el host.
- `start_period: 60s` da tiempo al startup (migraciones + descarga de recursos).
- Puerto expuesto solo en `127.0.0.1` (no público) — para demo detrás de nginx/proxy.
- `SECRET_KEY`, `STORAGE_BASE_URL`, `ALLOWED_ORIGINS` se inyectan desde un `.env` en el directorio donde se ejecuta el compose.

**Añadir healthcheck a Qdrant en prod:**
```yaml
  qdrant:
    ...
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:6333/readyz || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5
```
Y cambiar `condition: service_started` → `condition: service_healthy` una vez que el healthcheck funcione en CI.

---

## Tarea 3 — `.dockerignore`

**Archivo:** `backend/.dockerignore` (nuevo)

```
venv/
.venv/
__pycache__/
*.pyc
*.pyo
.env
*.db
media/
tests/
evaluations/
.pycache/
*.egg-info/
.ruff_cache/
```

---

## Tarea 4 — HTTP 429 + `Retry-After` en el semáforo LLM

### 4a. Nueva excepción de dominio

**Archivo:** `backend/app/core/exceptions/__init__.py` (o el archivo de excepciones existente)

Añadir:
```python
class LLMBusyError(Exception):
    """El semáforo LLM está ocupado. Retornar 429 al cliente."""
```

### 4b. Check fail-fast en `rag_pipeline.py`

**Archivo:** `backend/app/engine/rag_pipeline.py`

En `invoke_rag_pipeline` e `invoke_generation_pipeline`, antes del `async with _llm_semaphore:`:

```python
from app.core.exceptions import LLMBusyError

# Dentro de la función, antes del async with:
if _llm_semaphore.locked():
    raise LLMBusyError()

async with _llm_semaphore:
    ...
```

### 4c. Check fail-fast en `image_prompt_builder.py`

**Archivo:** `backend/app/engine/image_prompt_builder.py`

El semáforo aquí es `threading.Semaphore`. Cambiar patrón a `acquire(blocking=False)`:

```python
if not _llm_semaphore.acquire(blocking=False):
    raise LLMBusyError()
try:
    ...  # llamada LLM
finally:
    _llm_semaphore.release()
```

### 4d. 429 en las rutas

Las rutas que llaman estos pipelines (`rag_query.py`, `content.py`, `image_generation.py`) deben capturar `LLMBusyError`:

```python
from app.core.exceptions import LLMBusyError
from fastapi import HTTPException
from fastapi.responses import JSONResponse

# En el try/except de cada ruta:
except LLMBusyError:
    raise HTTPException(
        status_code=429,
        headers={"Retry-After": "30"},
        detail="El servicio LLM está ocupado. Intenta de nuevo en 30 segundos.",
    )
```

**Rutas afectadas** (identificar cuáles llaman directamente los pipelines):
- `app/api/routes/collections/rag_query.py`
- `app/api/routes/entities/content.py`
- `app/api/routes/images/image_generation.py`

---

## Tarea 5 — Deuda técnica: índice FK en `entity.collection_id`

**Archivo:** nueva migración Alembic

```bash
alembic revision --autogenerate -m "add index entity collection_id"
```

Verificar que la migración generada añada:
```python
op.create_index('ix_entity_collection_id', 'entity', ['collection_id'])
```

Si autogenerate no lo detecta (SQLModel no siempre emite índices en FK), añadirlo manualmente.

---

## Fuera de scope esta semana

- **Llama Guard 3** — diferido (complejidad alta, impacto bajo para demo de 1 usuario)
- **Prometheus + Grafana** — diferido a Semana 12 según STRATEGY

---

## Orden de implementación

1. `.dockerignore`
2. `backend/Dockerfile`
3. `docker-compose.prod.yml` (añadir `app` + qdrant healthcheck + `media_data` volume)
4. `LLMBusyError` + check en `rag_pipeline.py` + `image_prompt_builder.py` + rutas (429)
5. Migración Alembic para índice FK

---

## Verificación

```bash
# 1. Build local del Dockerfile
cd backend
docker build -t loremaster-api .

# 2. Levantar el stack completo
docker compose -f docker-compose.prod.yml up -d

# 3. Verificar health
curl http://localhost:8000/health

# 4. Verificar 429 en semáforo (simular con 2 requests paralelos al /query)
# Backend tests
cd backend && make test

# 5. Verificar migración del índice
alembic upgrade head
```
