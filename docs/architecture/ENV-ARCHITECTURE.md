# ENV-ARCHITECTURE.md — Arquitectura de Variables de Entorno

Guía de referencia sobre cómo fluyen las variables de entorno en Lore Master:
qué archivo hace qué, quién lee qué, y qué valores son configurables.

---

## 1. Los cuatro archivos y sus roles

```
ARCHIVO                       ROL                          COMMITEADO
────────────────────────────────────────────────────────────────────
backend/.env.example          Plantilla local dev          ✅ Sí
backend/.env                  Config local real            ❌ .gitignore
.env.production.example       Plantilla Docker Compose     ✅ Sí
.env.production               Config Docker prod real      ❌ .gitignore
```

**Regla cardinal:** `backend/.env` y `.env.production` son **independientes**.
No son secuenciales ni se necesitan mutuamente.

- Solo quieres desarrollo local → solo `backend/.env`
- Solo quieres el stack Docker → solo `.env.production`
- Quieres ambos → ambos archivos, configurados por separado

---

## 2. Flujo completo por modo

### Modo local (uvicorn directo)

```
backend/.env.example
      │  cp .env.example .env
      ▼
backend/.env
      │  Pydantic env_file=".env"
      │  CWD = backend/ → encuentra backend/.env
      ▼
Pydantic Settings (app/core/config/__init__.py)
      │  prioridad: process env > env_file > default código
      ▼
FastAPI arranca con los valores de backend/.env
```

### Modo Docker prod (make prod-up)

```
.env.production.example
      │  cp .env.production.example .env.production
      ▼
.env.production
      │  --env-file .env.production  (Makefile DC_PROD)
      │  CWD = raíz del repo
      ▼
docker-compose.prod.yml
      │  interpola ${VAR} en el YAML
      │  construye el bloque environment: de cada servicio
      ▼
Contenedor loremaster-api
      │  variables inyectadas como process env vars
      ▼
Pydantic Settings (dentro del contenedor)
      │  env_file=".env" → busca /app/.env → NO existe (.dockerignore)
      │                  → silenciosamente ignorado
      │  lee process env vars (prioridad 1 de todas formas)
      ▼
FastAPI arranca con los valores del compose
```

---

## 3. Prioridad de Pydantic BaseSettings

```
1. Process env vars        ← GANA SIEMPRE
2. env_file=".env"         ← solo si existe el archivo en CWD
3. Default del campo       ← fallback del código Python
```

`extra="ignore"` — variables en el entorno que no coincidan con ningún
campo de Settings son descartadas silenciosamente sin error.

---

## 4. Cómo mapea Settings los nombres

Pydantic convierte `snake_case` → `UPPER_SNAKE_CASE` para buscar la env var:

```python
# Campo en Settings          Env var que busca
secret_key: str          →   SECRET_KEY
allowed_origins: list    →   ALLOWED_ORIGINS   (JSON array: ["http://..."])
rate_limit_enabled: bool →   RATE_LIMIT_ENABLED ("true"/"false" → bool)
database_url: str        →   DATABASE_URL
qdrant_url: str          →   QDRANT_URL
storage_base_url: str    →   STORAGE_BASE_URL
...
```

**Único campo sin default:** `secret_key: str` — si no está definido en
ninguna fuente, Pydantic lanza `ValidationError` y FastAPI no arranca.

---

## 5. Clasificación de variables en docker-compose.prod.yml

### Requeridas (:?) — compose ABORTA si no están en .env.production

| Variable | Quién la usa en el compose | Llega a Settings como |
|---|---|---|
| `SECRET_KEY` | `app` environment | `SECRET_KEY` → `secret_key` |
| `POSTGRES_USER` | `postgres` service + `DATABASE_URL` | embebida en `DATABASE_URL` |
| `POSTGRES_PASSWORD` | `postgres` service + `DATABASE_URL` | embebida en `DATABASE_URL` |
| `POSTGRES_DB` | `postgres` service + `DATABASE_URL` | embebida en `DATABASE_URL` |
| `ALLOWED_ORIGINS` | `app` environment | `ALLOWED_ORIGINS` → `allowed_origins` |

> `POSTGRES_*` nunca llegan al contenedor del backend como variables individuales.
> Docker Compose las usa para construir `DATABASE_URL=postgresql://USER:PASS@postgres/DB`.
> Settings lee `DATABASE_URL` ya completa — nunca ve `POSTGRES_USER` directamente.

### Opcionales con fallback (:-) — funcionan sin .env.production

| Variable | Fallback | Override en .env.production |
|---|---|---|
| `STORAGE_BASE_URL` | `http://localhost/media` | Para dominio real |
| `RATE_LIMIT_ENABLED` | `false` | `true` cuando haya usuarios reales |
| `LLAMA_GUARD_ENABLED` | `false` | `true` + ollama pull llama-guard3:8b |
| `LLAMA_GUARD_MODEL` | `llama-guard3:8b` | Otro modelo si aplica |
| `LLAMA_GUARD_TIMEOUT` | `5.0` | Ajustar según latencia |
| `S3_BUCKET` | `loremaster-media` | Nombre de bucket real en S3/R2 |

### Hardcodeadas — .env.production no tiene ningún efecto sobre estas

| Variable | Valor | Razón |
|---|---|---|
| `ENVIRONMENT` | `demo` | Este compose ES el compose de demo |
| `QDRANT_URL` | `http://qdrant:6333` | Nombre de servicio Docker, fijo |
| `REDIS_URL` | `redis://redis:6379` | Nombre de servicio Docker, fijo |
| `S3_ENDPOINT_URL` | `http://floci:4566` | Nombre de servicio Docker, fijo |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Host gateway, demo siempre local |
| `COMFYUI_URL` | `http://host.docker.internal:8188` | Host gateway, demo siempre local |
| `OLLAMA_MODEL` | `llama3.2:latest` | Modelo validado para el pipeline |
| `IMAGE_BACKEND` | `comfyui` | Cambiará en Semana 10 (GPU cloud — RunPod/Replicate) |
| `IMAGE_PROMPT_MODEL` | `mistral:latest` | Modelo validado |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | **Debe coincidir con Dockerfile** |
| `STORAGE_BACKEND` | `s3` | Floci en demo, siempre S3-compatible |
| `AWS_ACCESS_KEY_ID` | `test` | Credencial fija de Floci |
| `AWS_SECRET_ACCESS_KEY` | `test` | Credencial fija de Floci |
| `S3_REGION` | `us-east-1` | Floci siempre usa esta región |
| `MEDIA_ROOT` | `/app/media` | Path dentro del contenedor |
| `COOKIE_SECURE` | `true` | Obligatorio en demo/prod por seguridad |

---

## 6. Validaciones que cortan el arranque (model_validator)

Settings ejecuta estas comprobaciones después de cargar todas las variables.
Si alguna falla, FastAPI no arranca:

| Condición | Entorno | Error |
|---|---|---|
| `SECRET_KEY` no definida | todos | `ValidationError` — campo requerido |
| `SECRET_KEY` < 32 chars | demo, production | `ValueError` |
| `ALLOWED_ORIGINS` contiene `*` | todos | CORS con credentials no acepta wildcard |
| Cualquier origen `http://` (no localhost) | demo, production | HTTPS obligatorio |
| `COOKIE_SECURE=false` | demo, production | Cookies inseguras en HTTPS |
| `ENVIRONMENT` fuera del set válido | todos | Valor no reconocido |

> En `ENVIRONMENT=demo` (compose prod hardcodeado), el validador exige
> `SECRET_KEY ≥ 32 chars` y `COOKIE_SECURE=true`. Ambos están cubiertos:
> `SECRET_KEY` viene de `.env.production` y `COOKIE_SECURE=true` está hardcodeado.

---

## 7. Setup en equipo nuevo

```bash
# ── Solo desarrollo local ──────────────────────────────────────────────
cd backend
cp .env.example .env
# Editar SECRET_KEY (cualquier string en local, mínimo 1 char)
# Editar POSTGRES_* si usas modo PostgreSQL (dev.ps1 -Postgres)
make infra          # Qdrant + Redis
make run            # uvicorn desde backend/

# ── Solo stack Docker ──────────────────────────────────────────────────
cp .env.production.example .env.production
# Editar SECRET_KEY   (≥ 32 chars — diferente a la de local)
# Editar POSTGRES_PASSWORD
# Editar ALLOWED_ORIGINS=["http://localhost"]
make prod-up

# ── Ambos entornos ─────────────────────────────────────────────────────
# Ambos pasos anteriores de forma independiente.
# backend/.env y .env.production son archivos separados sin relación.
```

---

## 8. Puntos de mejora identificados

### Pendiente — cloud deploy con S3/R2 real (no bloquea demo local)

El backend S3 ya está implementado (`core/storage/s3_client.py` con boto3). Para activar
S3/R2 real en cloud deploy, las credenciales hardcodeadas para Floci deben volverse
interpolables en `docker-compose.prod.yml`:

```yaml
# Actual (hardcodeado para Floci demo)
S3_ENDPOINT_URL:       http://floci:4566
AWS_ACCESS_KEY_ID:     test
AWS_SECRET_ACCESS_KEY: test

# Para cloud (interpolado con fallback Floci)
S3_ENDPOINT_URL:       ${S3_ENDPOINT_URL:-http://floci:4566}
AWS_ACCESS_KEY_ID:     ${AWS_ACCESS_KEY_ID:-test}
AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY:-test}
```

Y añadir en `.env.production.example`:
```bash
# S3/R2 real — dejar vacío para usar Floci (demo)
S3_ENDPOINT_URL=https://tu-endpoint-r2.cloudflare.com   # o vacío para AWS
AWS_ACCESS_KEY_ID=<via secrets manager>
AWS_SECRET_ACCESS_KEY=<via secrets manager>
```

### Pendiente Semana 10 — GPU cloud (RunPod/Replicate)

```yaml
# Actual
IMAGE_BACKEND: comfyui

# Después de implementar cliente RunPod/Replicate
IMAGE_BACKEND: ${IMAGE_BACKEND:-comfyui}   # permite "runpod" o "replicate" sin tocar el compose
```

Añadir en `.env.production.example`:
```bash
# GPU cloud — dejar vacío para usar ComfyUI local
IMAGE_BACKEND=comfyui
# RUNPOD_API_KEY=<key>
# RUNPOD_ENDPOINT_ID=<endpoint>
```

### Sin fecha urgente — modelos Ollama configurables

Si se quiere cambiar de modelo sin editar el compose:

```yaml
OLLAMA_MODEL:       ${OLLAMA_MODEL:-llama3.2:latest}
IMAGE_PROMPT_MODEL: ${IMAGE_PROMPT_MODEL:-mistral:latest}
```

### Inconsistencia menor — default de `rate_limit_enabled`

El default en código Python es `True` (línea 107 de `config/__init__.py`),
pero el fallback del compose es `false`. En la práctica nunca hay problema
porque el compose siempre inyecta la variable. Pero conceptualmente
apuntan en direcciones distintas — el código dice "por defecto activo",
el compose dice "por defecto inactivo para demo".

---

*Última actualización: 2026-05-27 (revisado — S3 implementado; GPU cloud movido a Semana 10). Branch `main`.*
*Ver también: `docs/architecture/ENVIRONMENT.md` (referencia completa de variables), `docs/architecture/DEPLOY.md` (runbook operacional).*