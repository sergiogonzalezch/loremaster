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
| `DATABASE_URL` | `sqlite:///./loremaster.db` | SQLite (dev) / PostgreSQL (prod): `postgresql://loremaster:loremaster@localhost:5432/loremaster` |
| `QDRANT_URL` | `http://localhost:6333` | Base de datos vectorial |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Endpoint de Ollama |
| `OLLAMA_MODEL` | `llama3.2:latest` | Modelo LLM |
| `MAX_TOKENS` | `500` | Máximo de tokens en la respuesta del LLM |
| `TEMPERATURE` | `0.7` | Temperatura del LLM |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Modelo de embeddings |
| `EMBEDDING_DIMS` | `384` | Dimensiones del vector de embedding |
| `CHUNK_SIZE` | `512` | Tamaño de chunk en caracteres |
| `CHUNK_OVERLAP` | `50` | Solapamiento entre chunks |
| `TOP_K` | `4` | Chunks de contexto recuperados por RAG |
| `ALLOWED_ORIGINS` | `["http://localhost:3000","http://localhost:5173"]` | Orígenes permitidos por CORS |
| `REDIS_URL` | `redis://redis:6379/0` | Caché semántico (staged) |
| `CACHE_TTL` | `3600` | TTL del caché en segundos (staged) |

> Las variables de S3/LocalStack y ComfyUI aparecen en `.env.example` pero los servicios no están integrados aún.

## Servicios de soporte

```bash
# Infra base
docker-compose up -d

# Infra base + visor SQLite (dev)
docker-compose --profile tools up -d
```

| Servicio | Puerto (host) | Propósito | Profile |
|---|---|---|---|
| Qdrant | 6333 | Base de datos vectorial | — |
| PostgreSQL | 5433 | Metadatos relacionales | — |
| Redis | 6379 | Caché semántico (staged) | — |
| sqlite-web | 8080 | Visor web SQLite (`loremaster.db`) | `tools` |

El servicio `sqlite-web` solo arranca con `--profile tools` y abre `http://localhost:8080` directamente sobre el fichero `loremaster.db` local. No requiere credenciales.

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

| Método | Ruta | Descripción | Status |
|---|---|---|---|
| `POST` | `/collections/{id}/entities` | Crear entidad | 201 |
| `GET` | `/collections/{id}/entities` | Listar entidades | 200 |
| `GET` | `/collections/{id}/entities/{entity_id}` | Obtener entidad | 200 |
| `PATCH` | `/collections/{id}/entities/{entity_id}` | Actualizar entidad (parcial) | 200 |
| `DELETE` | `/collections/{id}/entities/{entity_id}` | Eliminar entidad | 204 |

### Contenido de entidad (RAG)

`EntityContent` es texto narrativo generado por el LLM para una categoría concreta de una entidad. No debe confundirse con `description`, que es metadata escrita directamente por el usuario y solo se modifica via `PATCH` en la ruta de entidades.

Categorías válidas: `backstory`, `extended_description`, `scene`, `chapter`.

Estados posibles: `pending` → `confirmed` | `discarded`. Máximo 5 contenidos `pending` por categoría por entidad. Confirmar uno descarta automáticamente los demás `pending` y el `confirmed` anterior **de esa misma categoría**, y actualiza el campo `description` de la entidad. Los contenidos en estado `discarded` no se pueden editar.

| Método | Ruta | Descripción | Status |
|---|---|---|---|
| `POST` | `/collections/{id}/entities/{entity_id}/generate/{category}` | Generar contenido RAG para una categoría | 201 |
| `GET` | `/collections/{id}/entities/{entity_id}/contents` | Listar contenidos (filtrables por `?category=`) | 200 |
| `PATCH` | `/collections/{id}/entities/{entity_id}/contents/{content_id}` | Editar contenido (`pending` o `confirmed`) | 200 |
| `POST` | `/collections/{id}/entities/{entity_id}/contents/{content_id}/confirm` | Confirmar contenido (actualiza entidad, descarta hermanos de la categoría) | 200 |
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