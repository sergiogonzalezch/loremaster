# CLAUDE.md — Backend

Quick reference. Full docs → [README.md](./README.md).

## Commands

```bash
make run        # uvicorn app.main:app --reload
make test       # pytest
make format     # black .
make lint       # ruff check .

pytest tests/test_*.py     # single file
pytest -k "test_name"       # by pattern

alembic upgrade head        # apply migrations
alembic revision --autogenerate -m "message"
```

## Stack

**FastAPI + SQLModel + SQLite/PostgreSQL + Qdrant + Ollama**

- **LLM:** `llama3.2:latest` via Ollama (semáforo: max 1 llamada concurrente)
- **Vectores:** Qdrant (port 6333), embeddings `paraphrase-multilingual-MiniLM-L12-v2`
- **Chunking:** 512 chars, 50 overlap, top_k=4

## Estructura clave

```
app/
├── api/routes/          # Endpoints organizados por dominio
│   ├── auth/            # auth.py, auth_clerk.py
│   ├── collections/     # collections.py
│   ├── documents/       # documents.py
│   ├── entities/        # entities.py, content.py
│   ├── images/          # image_generation.py
│   └── admin.py, metadata.py, public.py, rag_query.py, users.py
├── core/                # auth, common, config, deps, exceptions, soft_delete
├── domain/              # category_rules, content_guard, prompt_templates
├── engine/              # comfyui_client, extractor, llm, rag, rag_pipeline
├── models/
│   ├── db/              # DB models (SQLModel): collection, document, entity, etc.
│   ├── schemas/         # API schemas (Pydantic): collection, document, entity, etc.
│   ├── enums.py         # ContentCategory, ContentStatus
│   └── shared.py        # PaginatedResponse
└── services/            # Lógica de negocio por dominio
    ├── collection/       # collection_service
    ├── document/         # documents_service
    ├── entity/          # entities, content, generation services
    ├── image/           # image_generation_service
    ├── moderation/       # moderation_service
    ├── profile/         # profile_service
    ├── cascade_service.py
    └── deletion_service.py
```

## Image Generation

Flujo de dos pasos:
1. `POST .../image-generation/build-prompt` → genera `auto_prompt` (LLM)
2. `POST .../image-generation/generate` → usa `auto_prompt` del frontend + `final_prompt`

Módulo: `engine/image_prompt_builder.py` (consolidado).

## Testing

- SQLite in-memory, sin servicios externos
- `conftest.py` stub `app.engine.rag` al importar
- Fixtures: `db_session`, `client`, `mock_rag_engine`, `mock_llm`

## Servicios Docker

```bash
docker-compose up -d           # qdrant + redis
docker-compose --profile postgres up -d   # + postgres
```

| Service | Port |
|---------|------|
| Qdrant  | 6333 |
| Postgres| 5433 |

---

**Full documentation:** [README.md](./README.md)
**Documentation:** [../docs/DOCUMENTATION.md](../docs/DOCUMENTATION.md)
**Skills:** [SKILLS.md](./SKILLS.md)