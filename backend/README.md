# Lore Master — Backend

API REST con pipeline RAG. FastAPI + SQLModel + LangChain + Qdrant + Ollama.

## Requisitos

- Python 3.10+
- Docker + Docker Compose
- Ollama corriendo localmente con `llama3.2:latest`

## Instalación

El venv se crea y sincroniza automáticamente al usar los launchers (`loremaster.bat`, `loremaster.sh`, `dev.ps1`).

Para trabajar directamente con el backend sin el launcher:

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: .\venv\Scripts\Activate.ps1
make install-dev                # instala requirements.txt + requirements-dev.txt
```

## Variables de entorno

Copia el archivo de ejemplo y ajusta los valores:

```bash
cp .env.example .env
```

**General**

| Variable | Por defecto | Propósito |
|---|---|---|
| `PROJECT_NAME` | `Lore Master API` | Nombre del proyecto (docs Swagger y metadatos) |
| `ENVIRONMENT` | `local` | Entorno: `local`, `demo`, `production`, `test` |
| `LOG_LEVEL` | `INFO` | Nivel de logging: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `ALLOWED_ORIGINS` | `["http://localhost:3000","http://localhost:5173"]` | Orígenes permitidos por CORS |

**Base de datos**

| Variable | Por defecto | Propósito |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./loremaster.db` | SQLite en dev; `postgresql://user:pass@host:5433/db` en prod |
| `POSTGRES_USER` | — | Usuario PostgreSQL (requerido si `DATABASE_URL` es postgres) |
| `POSTGRES_PASSWORD` | — | Contraseña PostgreSQL |
| `POSTGRES_DB` | — | Nombre de la base de datos PostgreSQL |

**LLM (Ollama)**

| Variable | Por defecto | Propósito |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Endpoint de Ollama |
| `OLLAMA_MODEL` | `llama3.2:latest` | Modelo LLM para generación de contenido |
| `OLLAMA_EXCLUDED_MODELS` | `[]` | Array JSON de prefijos excluidos de `GET /models` (ej. `["qwen3","deepseek-r1"]`). Útil para ocultar modelos con thinking mode que rompen el parser RAG |
| `MAX_TOKENS` | `2000` | Máximo de tokens en la respuesta del LLM (`num_predict`) |
| `TEMPERATURE` | `0.7` | Temperatura del LLM (creatividad) |
| `MAX_CONCURRENT_LLM_CALLS` | `1` | Peticiones simultáneas máximas al LLM (semáforo) |
| `MAX_PENDING_CONTENTS` | `5` | Máximo de contenidos en estado `pending` por entidad/categoría |

**Embeddings y RAG**

| Variable | Por defecto | Propósito |
|---|---|---|
| `QDRANT_URL` | `http://localhost:6333` | Base de datos vectorial |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Modelo de embeddings |
| `EMBEDDING_DIMS` | `384` | Dimensiones del vector de embedding |
| `CHUNK_SIZE` | `400` | Tamaño de chunk en caracteres |
| `CHUNK_OVERLAP` | `150` | Solapamiento entre chunks |
| `TOP_K` | `4` | Chunks de contexto recuperados por RAG |
| `RAG_SCORE_THRESHOLD` | `0.3` | Score mínimo de similitud coseno para incluir un chunk |
| `MAX_PDF_PAGES` | `100` | Límite de páginas para PDFs (prevención de PDF bombs) |

**Generación de imágenes**

| Variable | Por defecto | Propósito |
|---|---|---|
| `IMAGE_PROMPT_MODEL` | `mistral:latest` | Modelo Ollama para extraer atributos visuales del lore |
| `IMAGE_PROMPT_TOKENS` | `512` | Tokens máximos para el prompt visual (límite del text encoder SD/Flux) |
| `IMAGE_BACKEND` | `comfyui` | Motor de generación: `comfyui` (producción) o `mock` (tests/local sin ComfyUI) |
| `IMAGE_BATCH_SIZE_DEFAULT` | `4` | Imágenes por defecto por generación |
| `IMAGE_WIDTH` | `1024` | Ancho de las imágenes generadas |
| `IMAGE_HEIGHT` | `1024` | Alto de las imágenes generadas |
| `IMAGE_SEED_BASE` | `42` | Semilla base para reproducibilidad del batch |
| `COMFYUI_URL` | `http://localhost:8188` | Endpoint del servidor ComfyUI |
| `COMFYUI_TIMEOUT` | `300` | Segundos máximos para que ComfyUI genere una imagen |
| `COMFYUI_REQUEST_TIMEOUT` | `30.0` | Timeout en segundos por request HTTP individual a ComfyUI |

**Almacenamiento**

| Variable | Por defecto | Propósito |
|---|---|---|
| `MEDIA_ROOT` | `./media` | Directorio raíz para archivos multimedia |
| `STORAGE_BACKEND` | `local` | Backend de almacenamiento: `local`, `s3`, `r2` |
| `STORAGE_BASE_URL` | `http://localhost:8000/media` | URL base para servir archivos multimedia |
| `PROFILE_IMAGE_MAX_SIZE_MB` | `5` | Tamaño máximo de avatar en MB |
| `DOCUMENT_MAX_UPLOAD_MB` | `50` | Tamaño máximo de documentos subidos (PDF/TXT) en MB |
| `DOCUMENT_EXTRACTION_TIMEOUT_SECONDS` | `30` | Timeout en segundos para extracción de texto de documentos |

**Auth — JWT**

| Variable | Por defecto | Propósito |
|---|---|---|
| `SECRET_KEY` | *(requerida)* | Clave de firma JWT. Mín. 32 chars en entornos no locales. **Cambiar en producción** |
| `ALGORITHM` | `HS256` | Algoritmo de firma JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Duración del token JWT en minutos (1 h) |

**Auth — Cookies**

| Variable | Por defecto | Propósito |
|---|---|---|
| `COOKIE_ACCESS_NAME` | `access_token` | Nombre de la cookie HttpOnly con el JWT local |
| `COOKIE_CSRF_NAME` | `csrf_token` | Nombre de la cookie CSRF (double-submit pattern) |
| `COOKIE_SECURE` | `False` | `True` en producción/demo (requiere HTTPS) |
| `COOKIE_SAMESITE` | `Strict` | Política SameSite: `Strict`, `Lax` o `None` |
| `COOKIE_DOMAIN` | *(vacío)* | Dominio de las cookies; vacío = dominio actual del request |
| `COOKIE_PATH` | `/` | Path de las cookies |

**Auth — Clerk**

| Variable | Por defecto | Propósito |
|---|---|---|
| `CLERK_JWKS_URL` | *(ver `.env.example`)* | URL JWKS de Clerk (entornos `demo` y `production` con Clerk activo) |
| `CLERK_AUDIENCE` | *(ver `.env.example`)* | Audience de Clerk (entornos `demo` y `production` con Clerk activo) |

**Rate Limiting**

| Variable | Por defecto | Propósito |
|---|---|---|
| `RATE_LIMIT_ENABLED` | `true` | Activa el middleware. Poner `false` en desarrollo/eval local |
| `RATE_LIMIT_PER_MINUTE` | `30` | Límite base (POST/PATCH/DELETE) por usuario/IP en ventana de 60 s |
| `RATE_LIMIT_LLM_PER_MINUTE` | `5` | Límite para endpoints terminados en `/query` o `/image-generation/build-prompt` |
| `RATE_LIMIT_IMAGE_PER_MINUTE` | `3` | Límite para `/image-generation/generate` |
| `REDIS_URL` | `redis://localhost:6379` | URL de Redis para el sliding window |

> El entorno `test` (`pytest`) omite rate limiting independientemente de `RATE_LIMIT_ENABLED`.

## Base de datos: dev vs producción

La app soporta **SQLite** (dev local, sin servidor) y **PostgreSQL** (producción/staging). El driver se detecta automáticamente a partir del prefijo de `DATABASE_URL`; no hay cambio de código.

### Dev / local (SQLite)

```dotenv
DATABASE_URL=sqlite:///./loremaster.db
```

```bash
make infra      # levanta qdrant + redis
make run        # la app crea loremaster.db automáticamente
```

### Dev / local (PostgreSQL)

```dotenv
DATABASE_URL=postgresql://loremaster:loremaster@localhost:5433/loremaster
POSTGRES_USER=loremaster
POSTGRES_PASSWORD=loremaster
POSTGRES_DB=loremaster
```

```bash
make infra-pg   # levanta qdrant + redis + postgres
make run
```

> El puerto expuesto de PostgreSQL es **5433** (no 5432) para evitar colisión con instalaciones locales.

El modo completo (infra + backend + frontend en ventanas separadas) se lanza desde la raíz del repo:

```powershell
.\dev.ps1            # SQLite
.\dev.ps1 -Postgres  # PostgreSQL
```

---

## Servicios de soporte

| Servicio | Puerto (host) | Propósito | Cuándo arranca |
|---|---|---|---|
| Qdrant | 6333 | Base de datos vectorial | siempre |
| Redis | 6379 | Rate limiting (sliding window) | siempre |
| PostgreSQL | 5433 | Metadatos relacionales | solo con `-Postgres` / `make infra-pg` |

```bash
make infra      # qdrant + redis (SQLite mode)
make infra-pg   # qdrant + redis + postgres
make down       # baja todo
```

## Ejecutar

```bash
make run
# o directamente:
uvicorn app.main:app --reload
```

Swagger UI disponible en `http://localhost:8000/docs`.

## Tests

```bash
make test
# o con opciones:
pytest -v
pytest tests/test_entities.py       # fichero concreto
pytest -k "test_create"             # por nombre
```

| Archivo | Tests | Cobertura |
|---|---|---|
| `test_content_guard.py` | 54 | Patrones regex, Unicode, leet-speak, `check_prompt_length` (min 10 chars), routing de excepciones |
| `test_entity_content.py` | 25 | Ciclo de vida EntityContent: pending → confirmed/discarded, límite de borradores |
| `test_collections.py` | 18 | CRUD de colecciones, ownership, unique constraint por usuario |
| `test_documents.py` | 17 | Upload PDF/TXT, filename > 255 chars → 422, background ingest, Qdrant failure, malformed PDF |
| `test_image_generation_service.py` | 13 | Build-prompt, generación por batch, guardrails de imagen |
| `test_entities.py` | 13 | CRUD de entidades, nombre reservado tras soft-delete |
| `test_auth.py` | 12 | Registro, login, logout (invalida token), versión desfasada → 401, errores de autenticación |
| `test_rag_query.py` | 9 | Consulta RAG, Qdrant caído → 503, LLM failure → semáforo liberado |
| `test_public_feed.py` | 9 | Feed público `/public/feed` e `/public/images`, perfiles públicos, ownership 403 |
| `test_harness_smoke.py` | 9 | Smoke tests del harness de evaluación de prompts (reporter, judge, runner) |
| `test_generation_service.py` | 8 | Generación por categoría, prompt templates, moderación |
| `test_prompt_builder.py` | 7 | Estrategias de contexto, flag `truncated`, ranking de fuentes |
| `test_auth_clerk.py` | 7 | `/sync` sin header → 401, token inválido → 401, user nuevo → creado + cookies, idempotencia, `/verify` soft-deleted → 401 |
| `test_admin.py` | 6 | Listado usuarios, cascade delete de colección y usuario, guardrail auto-eliminación |
| `test_users.py` | 4 | Perfil `/users/me` GET/PATCH, avatar upload/delete |
| `test_models.py` | 3 | Smoke tests de modelos DB (instanciación SQLModel y relaciones básicas) |
| `test_deletion_service.py` | 2 | Cascade soft-delete: documentos, entidades, contenidos, vectores Qdrant |
| `test_content_management_service.py` | 1 | `_discard_sibling_contents` no afecta otras categorías |

**Total: 262 tests.**

## Evaluaciones de integración (baseline)

Ejecuta el golden dataset contra la API real (Qdrant + Ollama) y reporta PASS/FAIL por caso.
**Por defecto usa su propia base de datos `evaluations/evals.db`** — `loremaster.db` no se modifica.

### Prerequisitos

```bash
# 1. Infraestructura levantada (desde la RAÍZ del repo, no desde backend/)
make infra          # Qdrant + Redis

# 2. Ollama corriendo con el modelo configurado
#    (necesario para casos rag_query, entity_content, image_generation)
```

### Modo standalone (recomendado)

El script arranca automáticamente un segundo servidor en `:8001` apuntando a `evals.db`,
corre los tests y lo detiene al finalizar.

```bash
# Desde backend/ con el venv activo:
python evaluations/baseline_evals.py

# Opciones comunes:
python evaluations/baseline_evals.py --categories rag_query guardrail
python evaluations/baseline_evals.py --ids RAG-001 CHAR-005
python evaluations/baseline_evals.py --eval-port 8002   # si 8001 está ocupado
python evaluations/baseline_evals.py --no-seed          # omitir ingesta del doc semilla
python evaluations/baseline_evals.py --keep-collection  # conservar colección al terminar
```

Si el script no consigue arrancar el servidor interno, verifica el arranque manual:

```bash
python -m uvicorn app.main:app --port 8001
```

### Modo conectado (backend externo)

Usa un backend ya corriendo. En este modo los datos van a la DB que tenga configurada ese backend.

```bash
python evaluations/baseline_evals.py --no-standalone --base-url http://localhost:8000
```

### Dataset y semilla

| Archivo | Descripción |
|---|---|
| `evaluations/dataset/golden_dataset.json` | Casos de prueba (categorías: `rag_query`, `entity_crud`, `entity_content`, `guardrail`, `image_generation`, `full_flow`, …) |
| `evaluations/dataset/golden_seed.txt` | Documento de lore ingestado antes de los casos RAG |

> `evaluations/evals.db` está en `.gitignore` y se recrea en cada ejecución standalone.

## Endpoints

Todos bajo `/api/v1/`.

### Autenticación

JWT local (HS256). Hay dos modos de entrada:

- **Modo local** (`ENVIRONMENT=local`): formulario propio (`/auth/login`, `/auth/register`).
- **Modo Clerk** (`ENVIRONMENT=demo` o `production` con `VITE_CLERK_PUBLISHABLE_KEY`): el frontend obtiene un JWT de Clerk y lo intercambia en `/auth/clerk/sync`. El backend valida el JWT de Clerk, crea o recupera el usuario local y emite una cookie de sesión local. A partir de ese punto **todas las requests usan el JWT local**, nunca el JWT de Clerk directamente.

`get_current_user` usa siempre `verify_token()` (JWT local firmado con `SECRET_KEY`) independientemente del entorno.

**Transporte del token:** `get_current_user` acepta el JWT por dos vías:
1. **Cookie HttpOnly** `access_token` (modo normal del frontend — protegido con CSRF double-submit).
2. **Header `Authorization: Bearer <token>`** (herramientas externas, Swagger UI, evals) — exento de CSRF porque no usa cookies.

| Método | Ruta | Auth | Descripción | Status |
|---|---|---|---|---|
| `POST` | `/auth/register` | No | Registrar usuario nuevo (modo local) | 200 |
| `POST` | `/auth/login` | No | Autenticar usuario (modo local) | 200 |
| `POST` | `/auth/logout` | Requerida | Invalidar la sesión activa incrementando `token_version` | 204 |
| `POST` | `/auth/clerk/sync` | No (Clerk JWT en header) | Intercambia un JWT de Clerk por una cookie de sesión local | 200 |
| `GET` | `/auth/clerk/verify` | No (Clerk JWT en header) | Verifica un JWT de Clerk y confirma que el usuario existe en BD | 200 |

**Login/Register response (modo local):** `{ username, access_token }` — el campo `access_token` solo se incluye cuando `ENVIRONMENT=local` (para facilitar el uso de Swagger). La sesión del frontend se establece via cookie HttpOnly `access_token` + cookie `csrf_token`.

**Usar Swagger con Bearer token:**

```
1. POST /auth/login  →  copia el campo access_token de la respuesta
2. Clic en "Authorize" (candado) en la esquina de Swagger
3. Pega el token en el campo BearerAuth → Authorize
4. Todos los endpoints protegidos funcionarán sin CSRF
```

> **Cookie y Bearer son transportes independientes.** Si el navegador tiene una cookie de sesión activa, los endpoints siguen funcionando aunque se revoque el Bearer en Swagger. El botón "Revoke" del diálogo Authorize solo borra el header de la UI — no llama a ningún endpoint. Para invalidar la sesión en el servidor (ambos transportes a la vez), usa `POST /auth/logout`.

Todos los endpoints de la API requieren autenticación salvo `/health`, `/` y los endpoints públicos (`/public/*`, `/users/{username}/profile`).

**Gestión de sesiones:** cada token incluye un claim `version` que se compara contra `token_version` del usuario en DB en cada request autenticado. El logout incrementa `token_version`, invalidando todos los tokens previos del usuario sin importar el transporte (cookie o Bearer). Los tokens tienen una vida útil de **60 minutos**.

> **Dependencias:** el hashing de contraseñas usa `bcrypt` directamente (sin `passlib`), compatible con `bcrypt >= 4.x`.

### Colecciones

Las colecciones son siempre **privadas**: solo el owner puede leerlas o modificarlas. El listado autenticado (`GET /collections/`) devuelve únicamente las del usuario actual. El nombre de colección es único por usuario (`UNIQUE(name, owner_id)`). El contenido compartido de una colección se expone via `/public/feed` e `/public/images`, no exponiendo la colección completa.

| Método | Ruta | Auth | Descripción | Status |
|---|---|---|---|---|
| `POST` | `/collections/` | Requerida | Crear colección (owner = usuario actual) | 201 |
| `GET` | `/collections/` | Requerida | Listar colecciones propias | 200 |
| `GET` | `/collections/{id}` | Requerida | Obtener colección (solo owner) | 200 |
| `PATCH` | `/collections/{id}` | Requerida | Actualizar nombre o descripción (solo owner) | 200 |
| `DELETE` | `/collections/{id}` | Requerida | Eliminar colección (cascade soft-delete, solo owner) | 204 |

### Documentos

| Método | Ruta | Descripción | Status |
|---|---|---|---|
| `POST` | `/collections/{id}/documents` | Subir documento PDF/TXT (máx. 50 MB, nombre máx. 255 chars) | 202 |
| `GET` | `/collections/{id}/documents` | Listar documentos (excluye estado `processing`) | 200 |
| `GET` | `/collections/{id}/documents/{doc_id}` | Obtener documento | 200 |
| `DELETE` | `/collections/{id}/documents/{doc_id}` | Eliminar documento | 204 |

### Entidades

Tipos válidos: `character`, `creature`, `location`, `faction`, `item`.

El nombre de entidad es único por colección con constraint a nivel de DB (`uq_entity_collection_name`). Los nombres de entidades soft-deleted también quedan reservados (coherente con el audit trail).

| Método | Ruta | Descripción | Status |
|---|---|---|---|
| `POST` | `/collections/{id}/entities` | Crear entidad | 201 |
| `GET` | `/collections/{id}/entities` | Listar entidades (paginado, filtrable por `?name=`, `?type=`) | 200 |
| `GET` | `/collections/{id}/entities/{entity_id}` | Obtener entidad | 200 |
| `PATCH` | `/collections/{id}/entities/{entity_id}` | Actualizar entidad (parcial) | 200 |
| `DELETE` | `/collections/{id}/entities/{entity_id}` | Eliminar entidad | 204 |

### Contenido de entidad (RAG)

`EntityContent` es texto narrativo generado por el LLM para una categoría concreta de una entidad. No debe confundirse con `description`, que es metadata escrita directamente por el usuario y solo se modifica via `PATCH` en la ruta de entidades.

Categorías válidas: `backstory`, `extended_description`, `scene`, `chapter`.

Estados posibles: `pending` → `confirmed` | `discarded`. Máximo 5 contenidos `pending` por categoría por entidad. Confirmar uno descarta automáticamente los demás `pending` de esa misma categoría **sin afectar contenidos ya `confirmed`**. Los contenidos en estado `discarded` no se pueden editar.

| Método | Ruta | Descripción | Status |
|---|---|---|---|
| `POST` | `/collections/{id}/entities/{entity_id}/generate/{category}` | Generar contenido RAG para una categoría (prompt específico por categoría) | 201 |
| `GET` | `/collections/{id}/entities/{entity_id}/contents` | Listar contenidos (paginado; `?category=`, `?page=`, `?page_size=`) | 200 |
| `PATCH` | `/collections/{id}/entities/{entity_id}/contents/{content_id}` | Editar contenido (`pending` o `confirmed`) | 200 |
| `POST` | `/collections/{id}/entities/{entity_id}/contents/{content_id}/confirm` | Confirmar contenido | 200 |
| `PATCH` | `/collections/{id}/entities/{entity_id}/contents/{content_id}/discard` | Cambiar estado a descartado | 200 |
| `PATCH` | `/collections/{id}/entities/{entity_id}/contents/{content_id}/share` | Compartir/descompartir contenido confirmado (toggle `is_shared`) | 200 |
| `DELETE` | `/collections/{id}/entities/{entity_id}/contents/{content_id}` | Soft-delete del contenido | 204 |

### Perfiles de usuario

| Método | Ruta | Auth | Descripción | Status |
|---|---|---|---|---|
| `GET` | `/users/me` | Requerida | Perfil del usuario autenticado | 200 |
| `PATCH` | `/users/me` | Requerida | Actualizar `display_name`, `bio`, `email` | 200 |
| `GET` | `/users/me/avatar` | Requerida | Obtener URL del avatar e indicador `has_avatar` | 200 |
| `POST` | `/users/me/avatar` | Requerida | Subir imagen de avatar (multipart/form-data) | 200 |
| `DELETE` | `/users/me/avatar` | Requerida | Eliminar avatar actual | 204 |
| `GET` | `/users/{username}/profile` | No requerida | Perfil público: datos del usuario + `shared_contents` + `shared_images` | 200 |

**Response de `/users/me`:** `{ id, username, email, display_name, bio, avatar_url, created_at }`.

**Response de `/users/me/avatar`:** `{ avatar_url: string | null, has_avatar: bool }`.

**Response de `/users/{username}/profile`:** `{ username, display_name, bio, avatar_url, shared_contents[], shared_images[] }`. Cada `shared_contents` incluye `content` completo, categoría, nombre y tipo de entidad. Cada `shared_images` incluye `image_url`, `storage_path`, `seed`, `auto_prompt`, `final_prompt`, nombre y tipo de entidad.

### Feed público

Endpoints sin autenticación que exponen únicamente contenido con `is_shared=True`.

| Método | Ruta | Auth | Descripción | Status |
|---|---|---|---|---|
| `GET` | `/public/feed` | No requerida | Listado paginado de `EntityContent` compartidos (con `content` completo y `content_preview` de 300 chars) | 200 |
| `GET` | `/public/images` | No requerida | Listado paginado de imágenes compartidas (con `seed`, `auto_prompt`, `final_prompt`) | 200 |

Ambos endpoints soportan `?page=` y `?page_size=`. Respuesta: `PaginatedResponse<T>` con `data` y `meta.{ total, page, page_size, total_pages }`.

### Consulta RAG libre

| Método | Ruta | Descripción | Status |
|---|---|---|---|
| `POST` | `/collections/{id}/query` | Consulta RAG libre contra el lore cargado (requiere ser owner) | 200 |

Respuesta: `{ answer, query, sources_count, source_doc_ids[] }`.

- Requiere autenticación y que el usuario sea owner de la colección (no se puede consultar el lore de otro usuario).
- Si Qdrant no está disponible durante la consulta, devuelve **503 Service Unavailable**.

### Generación de imágenes

Generación de imágenes para entidades mediante prompts visuales. El flujo opera en dos pasos:

1. **build-prompt**: Construye el `auto_prompt` (prompt visual generado por LLM) a partir de un contenido confirmado de la entidad.
2. **generate**: Genera imágenes usando el `auto_prompt` del frontend + `final_prompt` del usuario. No hay regeneración del prompt en backend.

El módulo `app/engine/image_prompt_builder.py` consolida la lógica de construcción de prompts visuales (anteriormente `image_pipeline` + `prompt_builder`).

| Método | Ruta | Descripción | Status |
|---|---|---|---|
| `POST` | `/collections/{id}/entities/{entity_id}/image-generation/build-prompt` | Construye el prompt visual (`auto_prompt`) desde un contenido confirmado | 200 |
| `POST` | `/collections/{id}/entities/{entity_id}/image-generation/generate` | Genera batch de imágenes (1-4) | 201 |
| `GET` | `/collections/{id}/entities/{entity_id}/image-generation` | Lista todas las generaciones de una entidad | 200 |
| `GET` | `/collections/{id}/entities/{entity_id}/image-generation/{generation_id}` | Obtiene una generación con sus imágenes | 200 |
| `PATCH` | `/collections/{id}/entities/{entity_id}/image-generation/{generation_id}/images/{image_id}/share` | Compartir/descompartir imagen (toggle `is_shared`) | 200 |
| `DELETE` | `/collections/{id}/entities/{entity_id}/image-generation/{generation_id}/images/{image_id}` | Elimina una imagen del batch | 204 |

**Request (generate):** `{ content_id, auto_prompt, final_prompt, batch_size }` — donde `auto_prompt` viene del frontend (previamente generado en `build-prompt`).

### Administración

Los endpoints de administración requieren que el usuario tenga `is_admin=True`. Un usuario soft-deleted no puede acceder aunque sea admin.

| Método | Ruta | Descripción | Status |
|---|---|---|---|
| `GET` | `/admin/users` | Listar todos los usuarios paginado (`?page=`, `?page_size=`); incluye `avatar_url` por usuario | 200 |
| `DELETE` | `/admin/collections/{id}` | Cascade soft-delete de cualquier colección (incluye documentos, entidades, contenidos y vectores Qdrant) | 204 |
| `DELETE` | `/admin/users/{id}` | Cascade soft-delete del usuario y de todas sus colecciones. Devuelve **403** si el admin intenta eliminarse a sí mismo | 204 / 403 |

#### Crear un usuario admin

No existe endpoint público para asignar el rol de admin. Se hace desde el servidor con el script `scripts/make_admin.py`:

```bash
# Desde backend/ con el virtualenv activo:
python scripts/make_admin.py <username>
# → User '<username>' is now an admin.
```

El script busca el usuario activo (no soft-deleted) por username y establece `is_admin=True`. El cambio es permanente hasta que se revierta manualmente.

## Moderación de contenido

`app/domain/content_guard.py` aplica filtros de seguridad basados en expresiones regulares en tres puntos del pipeline:

| Función | Dónde se llama | Qué bloquea |
|---|---|---|
| `check_user_input(text)` | Antes de cualquier llamada al LLM (`generation_service`, `rag_query_service`) | Contenido sexual explícito, discurso de odio, instrucciones de armas/drogas, acoso |
| `check_document_content(text)` | Tras extraer el texto del documento (`documents_service`) | Mismo conjunto de patrones |
| `check_generated_output(text)` | Tras recibir la respuesta del LLM | Mismo conjunto de patrones |

Las violaciones de entrada elevan `ContentNotAllowedError` (→ HTTP 422); las de salida elevan `GeneratedContentBlockedError` (→ HTTP 422). Cada rechazo se persiste en la tabla `moderation_log` (`layer`, `snippet`, `created_at`).

## Estructura de `app/`

```
app/
├── main.py              # Punto de entrada FastAPI; ensamblado de routers y middlewares
├── database.py          # Engine SQLAlchemy y get_session()
├── api/
│   ├── middlewares/     # RateLimitMiddleware, SecurityHeadersMiddleware
│   └── routes/
│       ├── admin/       # admin.py — /admin/users, /admin/collections/{id}, /admin/users/{id}
│       ├── auth/        # auth.py (login/register/logout), auth_clerk.py (/sync, /verify)
│       ├── collections/ # collections.py (CRUD), rag_query.py (POST /query)
│       ├── documents/   # documents.py (upload, list, delete, retry, SSE events)
│       ├── entities/    # entities.py (CRUD), content.py (generate, confirm, discard, share)
│       ├── images/      # image_generation.py (build-prompt, generate, list, share, delete)
│       ├── models/      # models.py — GET /models (lista modelos Ollama disponibles)
│       ├── public/      # public.py — /public/feed, /public/images
│       └── users/       # users.py — /users/me, /users/me/avatar, /users/{username}/profile
├── core/
│   ├── auth/            # JWT (create/verify), CSRF, Clerk (JWKS), get_current_user
│   ├── config/          # Settings (Pydantic) — todas las variables de entorno
│   ├── database/        # SoftDeleteMixin, soft_delete(), db_commit(), paginate_with_sort()
│   ├── exceptions/      # Excepciones de dominio tipadas (19 clases)
│   ├── storage/         # FileValidator (magic bytes, EXIF strip, límites de tamaño)
│   ├── api/             # PaginationParams, DateRangeParams, filtros compartidos
│   └── lifespan.py      # Startup/shutdown de Qdrant y colecciones por defecto
├── domain/
│   ├── content_guard.py       # check_user_input, check_generated_output, check_prompt_length
│   ├── category_rules.py      # Categorías válidas por tipo de entidad
│   ├── prompt_templates.py    # Plantillas Jinja2 por categoría
│   └── image_prompt_rules.py  # Reglas de atributos visuales por tipo de entidad
├── engine/
│   ├── llm.py                  # call_ollama() con semáforo y timeout
│   ├── rag.py                  # ingest_chunks, delete_document_chunks, query_qdrant
│   ├── rag_pipeline.py         # rag_query() — orquesta RAG completo
│   ├── extractor.py            # extract_text() — PDF → texto, TXT → texto
│   ├── image_prompt_builder.py # build_visual_prompt(), _truncate_to_tokens()
│   └── comfyui_client.py       # ComfyUIClient — genera imágenes vía WebSocket
├── models/
│   ├── enums.py          # ContentCategory, ContentStatus
│   ├── shared.py         # PaginatedResponse[T]
│   ├── db/               # Modelos SQLModel: User, Collection, Document, Entity,
│   │                     #   EntityContent, GeneratedText, ImageGeneration, ImageRecord,
│   │                     #   ModerationLog
│   └── schemas/          # Pydantic I/O: collection, document, entity, entity_content,
│                         #   image_generation, rag_query, user, public
└── services/
    ├── auth/             # authenticate_user, create_user, get_or_create_clerk_user
    ├── collection/       # collection_service (CRUD) + rag_query_service (execute_rag_query)
    ├── document/         # ingest_document_service, process_ingest_background
    ├── entity/           # CRUD entidades, generación y ciclo de vida de contenidos
    ├── image/            # image_generation_service (orquesta DB) + _backends.py (mock / comfyui puros)
    ├── moderation/       # log_moderation_event()
    ├── profile/          # get/update perfil, avatar upload/delete
    ├── public/           # feed público, perfiles públicos
    ├── cascade_service.py  # Cascade soft-delete de colecciones completas
    └── deletion_service.py # Cascade soft-delete de usuarios
```

## Migraciones

```bash
# Aplicar migraciones pendientes
alembic upgrade head

# Generar nueva migración desde cambios en modelos
alembic revision --autogenerate -m "descripcion"
```