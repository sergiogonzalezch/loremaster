# Lore Master — Backend

API REST con pipeline RAG. FastAPI + SQLModel + LangChain + Qdrant + Ollama.

## Requisitos

- Python 3.10+
- Docker + Docker Compose
- Ollama corriendo localmente con `llama3.2:latest`

## Instalación

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
make install-dev                # instala requirements.txt + requirements-dev.txt
```

## Variables de entorno

Copia el archivo de ejemplo y ajusta los valores:

```bash
cp .env.example .env
```

| Variable | Por defecto | Propósito |
|---|---|---|
| `COMPOSE_PROFILES` | *(vacío)* | Perfiles Docker activos. Vacío = solo qdrant+redis. `postgres` = también levanta PostgreSQL |
| `DATABASE_URL` | `sqlite:///./loremaster.db` | SQLite en dev; `postgresql://loremaster:loremaster@localhost:5433/loremaster` en prod |
| `QDRANT_URL` | `http://localhost:6333` | Base de datos vectorial |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Endpoint de Ollama |
| `OLLAMA_MODEL` | `llama3.2:latest` | Modelo LLM |
| `MAX_TOKENS` | `2000` | Máximo de tokens en la respuesta del LLM |
| `TEMPERATURE` | `0.7` | Temperatura del LLM |
| `MAX_CONCURRENT_LLM_CALLS` | `1` | Peticiones simultáneas máximas al LLM (semáforo) |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Modelo de embeddings |
| `EMBEDDING_DIMS` | `384` | Dimensiones del vector de embedding |
| `CHUNK_SIZE` | `512` | Tamaño de chunk en caracteres |
| `CHUNK_OVERLAP` | `50` | Solapamiento entre chunks en caracteres |
| `TOP_K` | `4` | Chunks de contexto recuperados por RAG |
| `ALLOWED_ORIGINS` | `["http://localhost:3000","http://localhost:5173"]` | Orígenes permitidos por CORS |
| `REDIS_URL` | `redis://redis:6379/0` | Caché semántico (staged) |
| `CACHE_TTL` | `3600` | TTL del caché en segundos (staged) |
| `SECRET_KEY` | `your-secret-key` | Clave de firma para tokens JWT. **Cambiar en producción.** |
| `ALGORITHM` | `HS256` | Algoritmo de firma JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Duración del token JWT en minutos (24 h) |
| `CLERK_JWKS_URL` | *(ver `.env.example`)* | URL JWKS de Clerk (solo entorno `production`) |
| `CLERK_AUDIENCE` | *(ver `.env.example`)* | Audience de Clerk (solo entorno `production`) |

> Las variables de S3/LocalStack y ComfyUI aparecen en `.env.example` pero los servicios no están integrados aún.

## Base de datos: dev vs producción

La app soporta **SQLite** (dev local, sin servidor) y **PostgreSQL** (producción). El driver se detecta automáticamente a partir del prefijo de `DATABASE_URL`; no hay cambio de código.

El perfil Docker `postgres` controla si el contenedor de PostgreSQL arranca o no. Ambos valores van en el mismo `.env`:

### Dev / local (SQLite)

```dotenv
COMPOSE_PROFILES=
DATABASE_URL=sqlite:///./loremaster.db
```

```bash
docker-compose up -d    # levanta qdrant + redis (postgres no arranca)
make run                # la app crea loremaster.db automáticamente
```

### Producción (PostgreSQL)

```dotenv
COMPOSE_PROFILES=postgres
DATABASE_URL=postgresql://loremaster:loremaster@localhost:5433/loremaster
```

```bash
docker-compose up -d    # levanta qdrant + redis + postgres
make run
```

> El puerto expuesto de PostgreSQL es **5433** (no 5432) para evitar colisión con instalaciones locales.

---

## Servicios de soporte

| Servicio | Puerto (host) | Propósito | Profile |
|---|---|---|---|
| Qdrant | 6333 | Base de datos vectorial | *(siempre)* |
| Redis | 6379 | Caché semántico (staged) | *(siempre)* |
| PostgreSQL | 5433 | Metadatos relacionales (prod) | `postgres` |
| sqlite-web | 8080 | Visor web SQLite (`loremaster.db`) | `tools` |

```bash
# Solo infra base (dev — qdrant + redis)
docker-compose up -d

# Infra base + postgres (prod-local)
docker-compose --profile postgres up -d

# Infra base + visor SQLite (dev con UI)
docker-compose --profile tools up -d
```

`sqlite-web` abre `http://localhost:8080` directamente sobre `loremaster.db`. No requiere credenciales.

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
| `test_content_guard.py` | 32 | Patrones regex: inputs válidos/inválidos, Unicode, routing de excepciones |
| `test_entity_content.py` | 25 | Ciclo de vida EntityContent: pending → confirmed/discarded, límite de borradores |
| `test_collections.py` | 18 | CRUD de colecciones, ownership, unique constraint por usuario |
| `test_documents.py` | 16 | Upload PDF/TXT, background ingest, Qdrant failure, malformed PDF |
| `test_image_generation_service.py` | 13 | Build-prompt, generación por batch, guardrails de imagen |
| `test_entities.py` | 13 | CRUD de entidades, nombre reservado tras soft-delete |
| `test_rag_query.py` | 9 | Consulta RAG, Qdrant caído → 503, LLM failure → semáforo liberado |
| `test_generation_service.py` | 8 | Generación por categoría, prompt templates, moderación |
| `test_public_feed.py` | 9 | Feed público `/public/feed` e `/public/images`, perfiles públicos, ownership 403 |
| `test_prompt_builder.py` | 7 | Estrategias de contexto, flag `truncated`, ranking de fuentes |
| `test_admin.py` | 5 | Listado usuarios, cascade delete de colección y usuario |
| `test_users.py` | 4 | Perfil `/users/me` GET/PATCH |
| `test_deletion_service.py` | 2 | Cascade soft-delete: documentos, entidades, contenidos, vectores Qdrant |
| `test_content_management_service.py` | 1 | `_discard_sibling_contents` no afecta otras categorías |

**Total: 162 tests.**

## Endpoints

Todos bajo `/api/v1/`.

### Autenticación

Autenticación local con JWT. En desarrollo (`ENVIRONMENT=local`) se usa `verify_token` (HS256). En producción (`ENVIRONMENT=production`) se delega en Clerk via `decode_clerk_token`.

| Método | Ruta | Descripción | Status |
|---|---|---|---|
| `POST` | `/auth/register` | Registrar usuario nuevo y devolver token JWT | 200 |
| `POST` | `/auth/login` | Autenticar usuario y devolver token JWT | 200 |

**Request:** `{ username, password }` — **Response:** `{ access_token, token_type: "bearer" }`.

El token se envía en cabecera `Authorization: Bearer <token>`. Todos los endpoints de la API requieren autenticación salvo `/health` y `/`.

> **Dependencias:** el hashing de contraseñas usa `bcrypt` directamente (sin `passlib`), lo que lo hace compatible con `bcrypt >= 4.x`.

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
| `POST` | `/collections/{id}/documents` | Subir documento PDF/TXT (máx. 50 MB) | 201 |
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
| `PATCH` | `/users/me` | Requerida | Actualizar `display_name`, `bio`, `avatar_url`, `email` | 200 |
| `GET` | `/users/{username}/profile` | No requerida | Perfil público: datos del usuario + `shared_contents` + `shared_images` | 200 |

**Response de `/users/me`:** `{ id, username, email, display_name, bio, avatar_url, created_at }`.

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

Respuesta: `{ answer, query, sources_count }`.

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
| `GET` | `/admin/users` | Listar todos los usuarios (paginado con `?page=` y `?page_size=`) | 200 |
| `DELETE` | `/admin/collections/{id}` | Cascade soft-delete de cualquier colección (incluye documentos, entidades, contenidos y vectores Qdrant) | 204 |
| `DELETE` | `/admin/users/{id}` | Cascade soft-delete del usuario y de todas sus colecciones | 204 |

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

## Migraciones

```bash
# Aplicar migraciones pendientes
alembic upgrade head

# Generar nueva migración desde cambios en modelos
alembic revision --autogenerate -m "descripcion"
```