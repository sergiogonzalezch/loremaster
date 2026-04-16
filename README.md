# Lore Master

Plataforma RAG para escritores, narradores de rol (RPG) y diseñadores de mundos ficticios. Permite cargar documentos de lore y generar texto narrativo coherente con ese contexto usando una arquitectura de Retrieval-Augmented Generation.

## ¿Qué hace?

- Ingesta y vectoriza documentos de lore (PDF/TXT) en colecciones independientes.
- Recupera contexto relevante antes de cada generación de texto.
- Genera texto narrativo expandido, anclado en el lore cargado por el usuario.
- Gestiona entidades del mundo (personajes, escenarios, facciones, ítems).
- Genera borradores de lore para entidades usando RAG y permite confirmarlos o descartarlos.
- (Roadmap) Generación de imágenes con ComfyUI + Flux.2 Klein 4B.

## Stack

| Capa | Tecnología |
|---|---|
| API | FastAPI + Uvicorn |
| Validación | Pydantic v2 |
| RAG | LangChain |
| Embeddings | sentence-transformers (`paraphrase-multilingual-MiniLM-L12-v2`, 384d) |
| Vector DB | Qdrant |
| LLM local | Ollama (`llama3.2:latest`) |
| Caché semántico | Redis (similitud ≥ 0.95, TTL 3600s) |
| BD relacional | PostgreSQL |
| Almacenamiento | LocalStack S3 (dev) / AWS S3 o Cloudflare R2 (prod) |
| Observabilidad | Prometheus + Grafana |
| Contenerización | Docker Compose |

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
cp .env.example .env
```

Variables clave en `backend/.env`:

| Variable | Por defecto |
|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` |
| `OLLAMA_MODEL` | `llama3.2:latest` |
| `QDRANT_URL` | `http://localhost:6333` |
| `QDRANT_COLLECTION` | `loremaster` |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `DATABASE_URL` | `postgresql://loremaster:loremaster@localhost:5432/loremaster` |
| `ALLOWED_ORIGINS` | `["http://localhost:3000"]` |

### Levantar servicios de soporte

```bash
cd backend
docker-compose up -d
```

Servicios disponibles:

| Servicio | Puerto | Propósito |
|---|---|---|
| Qdrant | 6333 | Base de datos vectorial |
| PostgreSQL | 5432 | Metadatos relacionales |
| Redis | 6379 | Caché semántico |
| LocalStack | 4566 | S3 local |
| Prometheus | 9090 | Scraping de métricas |
| Grafana | 3000 | Dashboard (admin/admin) |

### Ejecutar la API

```bash
cd backend
uvicorn app.main:app --reload
```

Swagger UI disponible en: `http://localhost:8000/docs`

## API — Endpoints principales

Todos bajo `/api/v1/`:

### Colecciones
- `POST /collections/` — crear colección → `201`
- `GET /collections/` — listar colecciones
- `GET /collections/{id}` — obtener colección
- `DELETE /collections/{id}` — eliminar colección → `204`

### Documentos
- `POST /collections/{id}/documents` — subir documento (PDF/TXT, max 50 MB) → `201`
- `GET /collections/{id}/documents` — listar documentos
- `GET /collections/{id}/documents/{doc_id}` — obtener documento
- `DELETE /collections/{id}/documents/{doc_id}` — eliminar documento → `204`

### Entidades
- `POST /collections/{id}/entities` — crear entidad → `201`
- `GET /collections/{id}/entities` — listar entidades
- `GET /collections/{id}/entities/{entity_id}` — obtener entidad
- `PUT /collections/{id}/entities/{entity_id}` — actualizar entidad
- `DELETE /collections/{id}/entities/{entity_id}` — eliminar entidad → `204`

### Borradores de entidad
- `POST /collections/{id}/entities/{entity_id}/generate` — generar borrador RAG → `201`
- `GET /collections/{id}/entities/{entity_id}/drafts` — listar borradores
- `PATCH /collections/{id}/entities/{entity_id}/drafts/{draft_id}` — editar contenido
- `POST /collections/{id}/entities/{entity_id}/drafts/{draft_id}/confirm` — confirmar borrador (actualiza la entidad)
- `DELETE /collections/{id}/entities/{entity_id}/drafts/{draft_id}` — descartar borrador

### Generación
- `POST /collections/{id}/generate/text` — generar texto RAG a partir de una query

## Estructura del proyecto

```
loremaster/
├── backend/
│   ├── config.py                   # Settings via pydantic-settings (.env)
│   ├── requirements.txt
│   ├── docker-compose.yml
│   ├── .env.example
│   └── app/
│       ├── main.py                 # FastAPI app, CORS, lifespan, routers
│       ├── database.py             # Engine SQL y sesión (SQLModel)
│       ├── models/
│       │   ├── collections.py
│       │   ├── documents.py
│       │   ├── entities.py
│       │   ├── entity_text_draft.py
│       │   └── generate.py
│       ├── api/
│       │   └── routes/
│       │       ├── collections.py
│       │       ├── documents.py
│       │       ├── entities.py
│       │       ├── entity_text_draft.py
│       │       └── generate.py
│       ├── core/
│       │   ├── rag_engine.py       # Qdrant: ingest, search, delete
│       │   ├── rag_generate.py     # Orquestador RAG → LLM
│       │   ├── llm_client.py       # Ollama via LangChain
│       │   ├── text_extractor.py   # Extracción PDF/TXT
│       │   ├── valid_collection.py # Dependency FastAPI: valida colección activa
│       │   └── common.py           # Helpers genéricos de DB (soft_delete, queries)
│       └── services/
│           ├── collection_service.py
│           ├── documents_service.py
│           ├── entities_service.py
│           ├── entity_text_draft_service.py
│           └── generate_service.py
└── docs/
    ├── DOCUMENTATION.md
    └── WEEKLY_CHECKLISTS.md
```

## Estado actual

> **Pipeline RAG funcional end-to-end.** Ingesta de documentos (PDF/TXT) → chunking → embeddings → Qdrant → búsqueda semántica → Ollama → respuesta. Persistencia en PostgreSQL via SQLModel. Gestión completa de entidades con sistema de borradores RAG confirmables. Tests: 58 passing.

## Desarrollo

```bash
# Formatear código
cd backend && black .

# Ejecutar tests
cd backend && pytest
```
