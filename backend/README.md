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
pip install -r requirements.txt
```

## Variables de entorno

Copia el archivo de ejemplo y ajusta los valores:

```bash
cp .env.example .env
```

| Variable | Por defecto | Propósito |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Endpoint de Ollama |
| `OLLAMA_MODEL` | `llama3.2:latest` | Modelo LLM |
| `QDRANT_URL` | `http://localhost:6333` | Base de datos vectorial |
| `DATABASE_URL` | `postgresql://loremaster:loremaster@localhost:5432/loremaster` | PostgreSQL |
| `ALLOWED_ORIGINS` | `["http://localhost:5173"]` | Orígenes permitidos por CORS |

## Servicios de soporte

```bash
docker-compose up -d
```

| Servicio | Puerto | Propósito |
|---|---|---|
| Qdrant | 6333 | Base de datos vectorial |
| PostgreSQL | 5432 | Metadatos relacionales |
| Redis | 6379 | Caché semántico (staged) |
| LocalStack | 4566 | S3 local (staged) |

## Ejecutar

```bash
uvicorn app.main:app --reload
```

Swagger UI disponible en `http://localhost:8000/docs`.

## Tests

```bash
pytest -v
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
| `GET` | `/collections/{id}/documents` | Listar documentos | 200 |
| `GET` | `/collections/{id}/documents/{doc_id}` | Obtener documento | 200 |
| `DELETE` | `/collections/{id}/documents/{doc_id}` | Eliminar documento | 204 |

### Entidades

Tipos válidos: `character`, `scene`, `faction`, `item`.

| Método | Ruta | Descripción | Status |
|---|---|---|---|
| `POST` | `/collections/{id}/entities` | Crear entidad | 201 |
| `GET` | `/collections/{id}/entities` | Listar entidades | 200 |
| `GET` | `/collections/{id}/entities/{eid}` | Obtener entidad | 200 |
| `PATCH` | `/collections/{id}/entities/{eid}` | Actualizar entidad (parcial) | 200 |
| `DELETE` | `/collections/{id}/entities/{eid}` | Eliminar entidad | 204 |

### Borradores de entidad (RAG)

Máximo 5 borradores `pending` por entidad. Confirmar uno descarta automáticamente los demás. La descripción de la entidad solo la modifica el usuario — confirmar un borrador no la sobreescribe.

| Método | Ruta | Descripción | Status |
|---|---|---|---|
| `POST` | `/collections/{id}/entities/{eid}/generate` | Generar borrador con RAG | 201 |
| `GET` | `/collections/{id}/entities/{eid}/drafts` | Listar borradores (excluye soft-deleted y discarded) | 200 |
| `PATCH` | `/collections/{id}/entities/{eid}/drafts/{did}` | Editar contenido del borrador (pending o confirmed) | 200 |
| `POST` | `/collections/{id}/entities/{eid}/drafts/{did}/confirm` | Confirmar borrador (status → confirmed, descarta hermanos) | 200 |
| `PATCH` | `/collections/{id}/entities/{eid}/drafts/{did}/discard` | Cambiar estado a descartado | 200 |
| `DELETE` | `/collections/{id}/entities/{eid}/drafts/{did}` | Soft-delete del borrador | 204 |

### Generación libre

| Método | Ruta | Descripción | Status |
|---|---|---|---|
| `POST` | `/collections/{id}/generate/text` | Consulta RAG libre contra el lore cargado | 200 |

## Migraciones

```bash
# Aplicar migraciones pendientes
alembic upgrade head

# Generar nueva migración desde cambios en modelos
alembic revision --autogenerate -m "descripcion"
```