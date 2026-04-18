# Lore Master

Plataforma RAG para escritores y narradores de rol. Carga documentos de lore, gestiona entidades de tu mundo y genera texto narrativo coherente con tu contexto.

## Stack

| Capa | Tecnología |
|---|---|
| Backend | FastAPI, SQLModel, LangChain, Qdrant, Ollama |
| Frontend | React 19, TypeScript, Vite, Bootstrap 5 |

## Estructura del repo

```
loremaster/
├── backend/          → API REST + pipeline RAG
├── frontend/         → SPA React para interactuar con la API
└── docs/             → Documentación extendida
```

## Quick start

1. Clonar el repo:
   ```bash
   git clone https://github.com/sergiogonzalezch/loremaster.git
   cd loremaster
   ```

2. Levantar servicios de soporte (Qdrant, PostgreSQL, Redis, LocalStack):
   ```bash
   cd backend && docker-compose up -d
   ```

3. Levantar el backend: ver [`backend/README.md`](backend/README.md)

## Documentación

Arquitectura, decisiones técnicas y roadmap en [`docs/DOCUMENTATION.md`](docs/DOCUMENTATION.md).