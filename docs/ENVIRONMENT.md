# ENVIRONMENT.md — Guía de Variables de Entorno

Mapa completo de todas las variables de entorno del backend, con los valores
recomendados por entorno y las reglas de validación que aplica `Settings`.

---

## Entornos disponibles

| `ENVIRONMENT` | Descripción | Guardas de seguridad activas |
|---|---|---|
| `local` | Desarrollo en máquina propia | Relajadas (HTTP, SQLite, sin Clerk) |
| `test` | Tests automáticos (`pytest`) | Rate limiting desactivado, SQLite in-memory |
| `demo` | Demo pública / staging | HTTPS obligatorio, Cookies Secure, CORS HTTPS |
| `production` | Producción real | Ídem demo + SECRET_KEY ≥ 32 chars |

El `model_validator` de `Settings` **rechaza el arranque** si se violan las reglas
de seguridad del entorno seleccionado.

---

## Tabla de variables

### General

| Variable | Local | Demo | Producción | Defecto código |
|---|---|---|---|---|
| `PROJECT_NAME` | `"Lore Master API"` | igual | igual | `"Lore Master API"` |
| `ENVIRONMENT` | `local` | `demo` | `production` | `local` |
| `LOG_LEVEL` | `DEBUG` o `INFO` | `INFO` | `WARNING` o `ERROR` | `INFO` |
| `ALLOWED_ORIGINS` | `["http://localhost:5173"]` | `["https://demo.example.com"]` | `["https://app.example.com"]` | `["http://localhost:3000"]` |

> **Regla:** en `demo`/`production` todos los orígenes deben usar `https://`. El arranque falla si se pasa `http://`.

---

### Autenticación JWT

| Variable | Local | Demo | Producción | Notas |
|---|---|---|---|---|
| `SECRET_KEY` | cualquier string ≥ 1 char | **≥ 32 chars** | **≥ 32 chars** | Generar: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ALGORITHM` | `HS256` | `HS256` | `HS256` | — |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | `60` | `60` | Ajustar según política de sesión |

> **Regla:** fuera de `local` el arranque falla si `SECRET_KEY` tiene menos de 32 caracteres.

---

### Cookies de sesión

| Variable | Local | Demo | Producción | Notas |
|---|---|---|---|---|
| `COOKIE_SECURE` | `false` | **`true`** | **`true`** | Requiere HTTPS. El arranque falla si es `false` en demo/prod |
| `COOKIE_SAMESITE` | `Strict` | `Strict` | `Strict` | `Lax` si se necesitan requests cross-site |
| `COOKIE_ACCESS_NAME` | `access_token` | igual | igual | — |
| `COOKIE_CSRF_NAME` | `csrf_token` | igual | igual | — |
| `COOKIE_DOMAIN` | vacío | `.example.com` | `.example.com` | Vacío = dominio actual del request |
| `COOKIE_PATH` | `/` | `/` | `/` | — |

---

### Clerk (auth producción)

| Variable | Local | Demo | Producción | Notas |
|---|---|---|---|---|
| `CLERK_JWKS_URL` | placeholder | URL real de Clerk | URL real de Clerk | Solo se usa cuando el frontend llama con token Clerk |
| `CLERK_AUDIENCE` | placeholder | audience real | audience real | — |

> En `local` Clerk no se utiliza; la autenticación es local con JWT propio.

---

### Base de datos

| Variable | Local | Demo | Producción | Notas |
|---|---|---|---|---|
| `DATABASE_URL` | `sqlite:///./loremaster.db` | `postgresql://...` | `postgresql://...` | SQLite solo para local |
| `POSTGRES_USER` | — | `loremaster` | `loremaster` | Solo si `COMPOSE_PROFILES=postgres` |
| `POSTGRES_PASSWORD` | — | generada | generada | `openssl rand -hex 16` |
| `POSTGRES_DB` | — | `loremaster` | `loremaster` | — |

---

### LLM — Ollama

| Variable | Local | Demo | Producción | Notas |
|---|---|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | URL del servidor Ollama | URL del servidor Ollama | — |
| `OLLAMA_MODEL` | `llama3.2:latest` | igual | igual | Cambiar según el modelo disponible |
| `TEMPERATURE` | `0.7` | `0.7` | `0.7` | — |
| `MAX_TOKENS` | `2000` | `2000` | `2000` | `num_predict` de Ollama |
| `MAX_CONCURRENT_LLM_CALLS` | `1` | `1`–`2` | ajustar por RAM/GPU | Semáforo de concurrencia |
| `MAX_PENDING_CONTENTS` | `5` | `5` | `5` | Límite de drafts por entidad/categoría |

---

### Rate Limiting

| Variable | Local / Eval | Demo | Producción | Notas |
|---|---|---|---|---|
| `RATE_LIMIT_ENABLED` | `false` | `true` | `true` | `false` para eval y desarrollo; el middleware se salta completamente |
| `RATE_LIMIT_PER_MINUTE` | 30 | 30 | 30 | Límite base (POST/PATCH/DELETE) por usuario/IP en 60s |
| `RATE_LIMIT_LLM_PER_MINUTE` | 5 | 5 | 5 | Endpoints `/query` y `/build-prompt` |
| `RATE_LIMIT_IMAGE_PER_MINUTE` | 3 | 3 | 3 | Endpoint `/image-generation/generate` |
| `REDIS_URL` | `redis://localhost:6379` | `redis://redis:6379` | `redis://redis:6379` | El docker-compose lo levanta en el puerto por defecto |

> **Nota:** el entorno `test` (`pytest`) siempre omite el rate limiting
> independientemente de `RATE_LIMIT_ENABLED`, mediante el bypass
> `if settings.environment == "test"` en el middleware.

---

### RAG y Embeddings

| Variable | Local | Demo | Producción | Notas |
|---|---|---|---|---|
| `QDRANT_URL` | `http://localhost:6333` | `http://qdrant:6333` | `http://qdrant:6333` | En docker-compose usar el nombre del servicio |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | igual | igual | — |
| `EMBEDDING_DIMS` | `384` | `384` | `384` | Debe coincidir con el modelo |
| `CHUNK_SIZE` | `400` | `400` | `400` | Caracteres por chunk |
| `CHUNK_OVERLAP` | `150` | `150` | `150` | Solapamiento entre chunks |
| `TOP_K` | `4` | `4` | `4` | Chunks de contexto recuperados por consulta |
| `RAG_SCORE_THRESHOLD` | `0.3` | `0.3` | `0.3` | Score mínimo de similitud |
| `MAX_PDF_PAGES` | `100` | `100` | `100` | Prevención de PDF bombs |

---

### Generación de imágenes

| Variable | Local | Demo | Producción | Notas |
|---|---|---|---|---|
| `IMAGE_BACKEND` | `comfyui` (o `mock` sin servidor) | `comfyui` | `comfyui` | `mock` devuelve URL placeholder; independiente del entorno — usar `comfyui` en local si el servidor está disponible |
| `IMAGE_PROMPT_MODEL` | `mistral:latest` | igual | igual | Modelo Ollama para construir el prompt visual |
| `IMAGE_PROMPT_TOKENS` | `512` | `512` | `512` | Límite tokens del text encoder (SD/Flux) |
| `IMAGE_BATCH_SIZE_DEFAULT` | `4` | `4` | `4` | Imágenes por generación |
| `IMAGE_WIDTH` / `IMAGE_HEIGHT` | `1024` | `1024` | `1024` | — |
| `IMAGE_SEED_BASE` | `42` | `42` | `42` | — |
| `COMFYUI_URL` | `http://localhost:8188` | URL del servidor | URL del servidor | — |
| `COMFYUI_TIMEOUT` | `300` | `300` | `300` | Segundos máximos de espera |
| `COMFYUI_REQUEST_TIMEOUT` | `30.0` | `30.0` | `30.0` | Timeout HTTP por request individual |

---

### Storage / Media

| Variable | Local | Demo | Producción | Notas |
|---|---|---|---|---|
| `STORAGE_BACKEND` | `local` | `s3` o `r2` | `s3` o `r2` | `local` guarda en `./media/`; s3/r2 usa bucket externo |
| `MEDIA_ROOT` | `./media` | — | — | Solo relevante si `STORAGE_BACKEND=local` |
| `STORAGE_BASE_URL` | `http://localhost:8000/media` | URL CDN/bucket | URL CDN/bucket | URL pública para servir archivos |
| `PROFILE_IMAGE_MAX_SIZE_MB` | `5` | `5` | `5` | — |
| `DOCUMENT_MAX_UPLOAD_MB` | `50` | `50` | `50` | — |
| `DOCUMENT_EXTRACTION_TIMEOUT_SECONDS` | `30` | `30` | `30` | — |

> Para S3/R2 añadir también: `S3_ENDPOINT_URL`, `S3_BUCKET`, `AWS_ACCESS_KEY_ID`,
> `AWS_SECRET_ACCESS_KEY`. En producción usar IAM roles o secrets manager en lugar
> de variables de entorno en disco.

---

## Flujo por entorno

```
local/SQLite  →  make dev
├── ENVIRONMENT=local
├── DATABASE_URL=sqlite:///./loremaster.db
├── COOKIE_SECURE=false
├── RATE_LIMIT_ENABLED=false
├── IMAGE_BACKEND=comfyui  (o "mock" sin servidor ComfyUI)
├── STORAGE_BACKEND=local
└── Docker: Qdrant + Redis

local/PostgreSQL  →  make dev-pg
├── igual que local/SQLite
├── DATABASE_URL=postgresql://...
└── Docker: Qdrant + Redis + Postgres

demo / staging  →  make prod-up  (con docker-compose.prod.yml)
├── ENVIRONMENT=demo
├── DATABASE_URL=postgresql://...
├── COOKIE_SECURE=true                ← arranque falla si false
├── ALLOWED_ORIGINS=["https://..."]   ← arranque falla si http://
├── RATE_LIMIT_ENABLED=true
├── IMAGE_BACKEND=comfyui
├── STORAGE_BACKEND=s3 o r2
└── Docker: Qdrant + Redis + Postgres (sin puertos expuestos)

production  →  make prod-up
├── igual que demo
├── SECRET_KEY ≥ 32 chars             ← arranque falla si no se cumple
├── LOG_LEVEL=WARNING o ERROR
└── variables inyectadas por CI/CD o secrets manager (no .env en disco)
```

---

## Validaciones que corta el arranque

Estas comprobaciones están en `Settings._validate_cors()` y **lanzan `ValueError`**
si se violan, impidiendo que el servidor arranque:

| Condición | Entorno | Error |
|---|---|---|
| `ALLOWED_ORIGINS` contiene `*` | todos | CORS con credentials no puede usar wildcard |
| `SECRET_KEY` < 32 chars | demo, production | Clave insegura |
| Cualquier origen `http://` | demo, production | HTTPS obligatorio en CORS |
| `COOKIE_SECURE=false` | demo, production | Cookies inseguras en HTTPS |
| `ENVIRONMENT` fuera del set válido | todos | Valor no reconocido |

---

## Checklist de despliegue

Antes de subir a demo o producción verificar:

- [ ] `ENVIRONMENT=demo` o `production`
- [ ] `SECRET_KEY` generada con `secrets.token_hex(32)` (≥ 32 chars)
- [ ] `COOKIE_SECURE=true`
- [ ] `ALLOWED_ORIGINS` solo con `https://`
- [ ] `RATE_LIMIT_ENABLED=true`
- [ ] `DATABASE_URL` apuntando a PostgreSQL
- [ ] `COMPOSE_PROFILES=postgres`
- [ ] `STORAGE_BACKEND=s3` o `r2` (no `local`)
- [ ] `IMAGE_BACKEND=comfyui`
- [ ] `LOG_LEVEL=WARNING`
- [ ] Clerk configurado (`CLERK_JWKS_URL`, `CLERK_AUDIENCE`)
- [ ] Credenciales AWS/R2 gestionadas con secrets manager, no en `.env` en disco
