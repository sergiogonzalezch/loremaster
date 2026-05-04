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
├── api/routes/          # Endpoints (delegan a services/)
├── core/                # config, deps, common, lifespan
├── domain/              # category_rules, content_guard, prompt_templates
├── engine/              # rag, rag_pipeline, llm, extractor, image_prompt_builder
├── models/              # SQLModel + Pydantic schemas
└── services/            # Lógica de negocio
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