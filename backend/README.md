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
| `CHUNK_OVERLAP` | `50` | Solapamiento entre chunks |
| `TOP_K` | `4` | Chunks de contexto recuperados por RAG |
| `ALLOWED_ORIGINS` | `["http://localhost:3000","http://localhost:5173"]` | Orígenes permitidos por CORS |
| `REDIS_URL` | `redis://redis:6379/0` | Caché semántico (staged) |
| `CACHE_TTL` | `3600` | TTL del caché en segundos (staged) |

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

## Endpoints

Todos bajo `/api/v1/`.

### Colecciones

| Método | Ruta | Descripción | Status |
|---|---|---|---|
| `POST` | `/collections/` | Crear colección | 201 |
| `GET` | `/collections/` | Listar colecciones | 200 |
| `GET` | `/collections/{id}` | Obtener colección | 200 |
| `DELETE` | `/collections/{id}` | Eliminar colección (cascade soft-delete) | 204 |

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

Estados posibles: `pending` → `confirmed` | `discarded`. Máximo 5 contenidos `pending` por categoría por entidad. Confirmar uno descarta automáticamente los demás `pending` y el `confirmed` anterior **de esa misma categoría**. Los contenidos en estado `discarded` no se pueden editar.

| Método | Ruta | Descripción | Status |
|---|---|---|---|
| `POST` | `/collections/{id}/entities/{entity_id}/generate/{category}` | Generar contenido RAG para una categoría (prompt específico por categoría) | 201 |
| `GET` | `/collections/{id}/entities/{entity_id}/contents` | Listar contenidos (paginado; `?category=`, `?page=`, `?page_size=`) | 200 |
| `PATCH` | `/collections/{id}/entities/{entity_id}/contents/{content_id}` | Editar contenido (`pending` o `confirmed`) | 200 |
| `POST` | `/collections/{id}/entities/{entity_id}/contents/{content_id}/confirm` | Confirmar contenido | 200 |
| `PATCH` | `/collections/{id}/entities/{entity_id}/contents/{content_id}/discard` | Cambiar estado a descartado | 200 |
| `DELETE` | `/collections/{id}/entities/{entity_id}/contents/{content_id}` | Soft-delete del contenido | 204 |

### Consulta RAG libre

| Método | Ruta | Descripción | Status |
|---|---|---|---|
| `POST` | `/collections/{id}/query` | Consulta RAG libre contra el lore cargado | 200 |

Respuesta: `{ answer, query, sources_count }`.

## Migraciones

```bash
# Aplicar migraciones pendientes
alembic upgrade head

# Generar nueva migración desde cambios en modelos
alembic revision --autogenerate -m "descripcion"
```