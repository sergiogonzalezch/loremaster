# Lore Master

Plataforma RAG para escritores, narradores de rol (RPG) y diseñadores de mundos ficticios. Permite cargar documentos de lore y generar texto narrativo coherente con ese contexto usando una arquitectura de Retrieval-Augmented Generation.

## ¿Qué hace?

- Ingesta y vectoriza documentos de lore (PDF/TXT) en colecciones independientes.
- Recupera contexto relevante antes de cada generación de texto.
- Genera texto narrativo expandido, anclado en el lore cargado por el usuario.
- Gestiona entidades del mundo (personajes, escenarios, facciones, ítems).
- Genera borradores de lore para entidades usando RAG y permite confirmarlos o descartarlos.

## Stack

| Capa | Tecnología | Estado |
|---|---|---|
| API | FastAPI + Uvicorn | ✅ activo |
| Validación | Pydantic v2 + SQLModel | ✅ activo |
| RAG | LangChain | ✅ activo |
| Embeddings | sentence-transformers (`paraphrase-multilingual-MiniLM-L12-v2`, 384d) | ✅ activo |
| Vector DB | Qdrant | ✅ activo |
| LLM local | Ollama (`llama3.2:latest`) | ✅ activo |
| BD relacional | PostgreSQL (SQLModel) | 🔜 staged |
| Caché semántico | Redis (similitud ≥ 0.95, TTL 3600s) | 🔜 staged |
| Almacenamiento | LocalStack S3 (dev) / AWS S3 (prod) | 🔜 staged |
| Observabilidad | Prometheus + Grafana | 🔜 staged |
| Contenerización | Docker Compose | 🔜 staged |

## Puesta en marcha local

### Requisitos

- Python 3.10+
- Docker + Docker Compose
- Ollama corriendo localmente con `llama3.2:latest`

### Instalación

```bash
git clone https://github.com/sergiogonzalezch/loremaster.git
cd loremaster/backend

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Variables de entorno

```bash
cp backend/.env.example backend/.env
```

Variables clave en `backend/.env`:

| Variable | Por defecto | Propósito |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Endpoint de Ollama |
| `OLLAMA_MODEL` | `llama3.2:latest` | Modelo LLM |
| `QDRANT_URL` | `http://localhost:6333` | Base de datos vectorial |
| `REDIS_URL` | `redis://localhost:6379/0` | Caché semántico (no integrado aún) |
| `DATABASE_URL` | `postgresql://loremaster:loremaster@localhost:5432/loremaster` | PostgreSQL |
| `ALLOWED_ORIGINS` | `["http://localhost:3000"]` | CORS |

### Levantar servicios de soporte

```bash
cd backend
docker-compose up -d
```

| Servicio | Puerto | Propósito |
|---|---|---|
| Qdrant | 6333 | Base de datos vectorial |
| PostgreSQL | 5432 | Metadatos relacionales |
| Redis | 6379 | Caché semántico (staged) |
| LocalStack | 4566 | S3 local (staged) |
| Prometheus | 9090 | Scraping de métricas (staged) |
| Grafana | 3000 | Dashboard — admin/admin (staged) |

### Ejecutar la API

```bash
cd backend
uvicorn app.main:app --reload
```

Swagger UI disponible en: `http://localhost:8000/docs`

## API — Endpoints

Todos bajo `/api/v1/`:

### Colecciones

| Método | Ruta | Descripción | Status |
|---|---|---|---|
| `POST` | `/collections/` | Crear colección | 201 |
| `GET` | `/collections/` | Listar colecciones | 200 |
| `GET` | `/collections/{id}` | Obtener colección | 200 |
| `DELETE` | `/collections/{id}` | Eliminar colección (cascade) | 204 |

### Documentos

| Método | Ruta | Descripción | Status |
|---|---|---|---|
| `POST` | `/collections/{id}/documents` | Subir documento PDF/TXT (max 50 MB) | 201 |
| `GET` | `/collections/{id}/documents` | Listar documentos | 200 |
| `GET` | `/collections/{id}/documents/{doc_id}` | Obtener documento | 200 |
| `DELETE` | `/collections/{id}/documents/{doc_id}` | Eliminar documento | 204 |

### Entidades

| Método | Ruta | Descripción | Status |
|---|---|---|---|
| `POST` | `/collections/{id}/entities` | Crear entidad | 201 |
| `GET` | `/collections/{id}/entities` | Listar entidades | 200 |
| `GET` | `/collections/{id}/entities/{entity_id}` | Obtener entidad | 200 |
| `PUT` | `/collections/{id}/entities/{entity_id}` | Actualizar entidad | 200 |
| `DELETE` | `/collections/{id}/entities/{entity_id}` | Eliminar entidad | 204 |

Tipos de entidad: `character`, `scene`, `faction`, `item`.

### Borradores de entidad (RAG)

| Método | Ruta | Descripción | Status |
|---|---|---|---|
| `POST` | `/collections/{id}/entities/{entity_id}/generate` | Generar borrador con RAG | 201 |
| `GET` | `/collections/{id}/entities/{entity_id}/drafts` | Listar borradores | 200 |
| `PATCH` | `/collections/{id}/entities/{entity_id}/drafts/{draft_id}` | Editar contenido | 200 |
| `POST` | `/collections/{id}/entities/{entity_id}/drafts/{draft_id}/confirm` | Confirmar borrador → actualiza la entidad | 200 |
| `DELETE` | `/collections/{id}/entities/{entity_id}/drafts/{draft_id}` | Descartar borrador | 200 |

Máximo 5 borradores pendientes por entidad. Confirmar uno descarta automáticamente los demás.

### Generación

| Método | Ruta | Descripción | Status |
|---|---|---|---|
| `POST` | `/collections/{id}/generate/text` | Generar texto RAG a partir de una query | 200 |

## Estructura del proyecto

```
loremaster/
├── backend/
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── docker-compose.yml
│   ├── .env.example
│   └── app/
│       ├── main.py                     # FastAPI app, CORS, lifespan, routers
│       ├── database.py                 # Engine SQL y sesión (SQLModel)
│       ├── models/
│       │   ├── collections.py          # Collection + schemas de request/response
│       │   ├── documents.py            # Document + DocumentStatus
│       │   ├── entities.py             # Entity + EntityType + EntityRequest
│       │   ├── entity_text_draft.py    # EntityTextDraft + DraftStatus
│       │   └── generate.py             # GenerateTextRequest/Response
│       ├── api/routes/
│       │   ├── collections.py
│       │   ├── documents.py
│       │   ├── entities.py
│       │   ├── entity_text_draft.py
│       │   └── generate.py
│       ├── core/
│       │   ├── config.py               # Pydantic Settings — carga desde .env
│       │   ├── lifespan.py             # Health checks al arrancar (Qdrant, Ollama)
│       │   ├── rag_engine.py           # Qdrant: ingest, search, delete, ping
│       │   ├── rag_generate.py         # Orquestador RAG → LLM
│       │   ├── llm_client.py           # OllamaLLM + LangChain chain
│       │   ├── text_extractor.py       # Extracción de texto PDF/TXT
│       │   ├── valid_collection.py     # Dependencies FastAPI: get_collection_or_404, get_entity_or_404, get_document_or_404
│       │   └── common.py              # Helpers genéricos de DB (soft_delete, get_active_by_id, list_active_by_collection)
│       └── services/
│           ├── collection_service.py   # CRUD + cascade soft-delete
│           ├── documents_service.py    # Ingest (PDF/TXT), list, delete
│           ├── entities_service.py     # CRUD con unicidad de nombre por colección
│           ├── entity_text_draft_service.py  # Generación, confirmación y descarte de borradores RAG
│           └── generate_service.py     # Generación de texto libre vía RAG
└── tests/
    ├── conftest.py                     # Fixtures: DB in-memory, client, mocks LLM/RAG
    ├── test_collections.py
    ├── test_documents.py
    ├── test_entities.py
    ├── test_entity_drafts.py
    └── test_generate.py
```

## Flujo de datos

```
Usuario → POST /documents  →  text_extractor  →  chunking  →  embeddings  →  Qdrant
Usuario → POST /generate   →  Qdrant search   →  LangChain prompt  →  Ollama  →  respuesta
Usuario → POST /entities/{id}/generate  →  entity context + Qdrant  →  Ollama  →  draft
```

## Desarrollo

```bash
# Formatear código
cd backend && black .

# Ejecutar tests
cd backend && pytest

# Tests con detalle
cd backend && pytest -v
```

## Estado actual

Pipeline RAG funcional end-to-end. Ingesta de documentos → chunking → embeddings → Qdrant → búsqueda semántica → Ollama → respuesta. Persistencia relacional en PostgreSQL via SQLModel. Gestión completa de entidades con sistema de borradores RAG confirmables. **58 tests passing.**

Redis, LocalStack S3 y Prometheus/Grafana están presentes en el stack Docker pero pendientes de integración en la capa de servicios.