# Lore Master

Plataforma RAG para escritores y narradores de rol. Carga documentos de lore, gestiona entidades de tu mundo y genera texto narrativo coherente con tu contexto. Cada usuario tiene sus propias colecciones; las colecciones públicas son visibles para cualquiera sin autenticación.

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

4. Levantar el frontend: ver [`frontend/README.md`](frontend/README.md)

## Usuarios y acceso

El registro está abierto. Cualquier usuario puede crear una cuenta via `POST /api/v1/auth/register`. Las colecciones pertenecen al usuario que las crea; otros usuarios no pueden editarlas ni eliminarlas.

### Crear el primer usuario admin

Los administradores se designan desde el servidor con el script `make_admin.py`. No existe endpoint público para ello.

```bash
# 1. Registrar la cuenta (API o frontend)
# 2. Desde backend/ con el virtualenv activo:
python scripts/make_admin.py <username>
# → User '<username>' is now an admin.
```

Los admins tienen acceso a los endpoints `/api/v1/admin/*` (listar todos los usuarios, eliminar cualquier colección o usuario).

## Documentación

Arquitectura, decisiones técnicas y roadmap en [`docs/DOCUMENTATION.md`](docs/DOCUMENTATION.md).