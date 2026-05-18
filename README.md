# Lore Master

Plataforma RAG para escritores y narradores de rol. Carga documentos de lore, gestiona entidades de tu mundo y genera texto narrativo e imágenes coherentes con tu contexto. Cada usuario tiene sus propias colecciones privadas; el contenido individual (textos e imágenes) se puede compartir selectivamente en el feed público y en perfiles de usuario accesibles sin autenticación.

## Stack

| Capa | Tecnología |
|---|---|
| Backend | FastAPI, SQLModel, Qdrant, Ollama |
| Frontend | React 19, TypeScript, Vite, Bootstrap 5 |

## Estructura del repo

```
loremaster/
├── backend/          → API REST + pipeline RAG
├── frontend/         → SPA React
├── docs/             → Documentación extendida
├── Makefile          → Targets de infra y arranque
└── dev.ps1           → Arranque completo del entorno local (Windows)
```

## Quick start

### Primera vez

```bash
git clone https://github.com/sergiogonzalezch/loremaster.git
cd loremaster

# Backend — venv y dependencias
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows
make install-dev
cp .env.example .env          # editar SECRET_KEY y las variables que correspondan
alembic upgrade head

# Frontend — dependencias
cd ../frontend
npm install
```

### Arrancar el entorno

```powershell
# Desde la raíz del proyecto (Windows)
.\dev.ps1            # SQLite + Qdrant + Redis + backend + frontend
.\dev.ps1 -Postgres  # PostgreSQL + Qdrant + Redis + backend + frontend
```

Se abre una ventana por proceso. Para bajar la infraestructura Docker:

```bash
make down
```

### Solo infraestructura (sin abrir backend/frontend)

```bash
make infra      # Qdrant + Redis
make infra-pg   # Qdrant + Redis + PostgreSQL
```

Ver [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md) para la referencia completa de variables de entorno, modos (local/demo/producción) y checklist de despliegue.

## Usuarios y acceso

El registro está abierto. Cualquier usuario puede crear una cuenta via `POST /api/v1/auth/register`. Las colecciones pertenecen al usuario que las crea; otros usuarios no pueden editarlas ni eliminarlas.

### Crear el primer usuario admin

Los administradores se designan desde el servidor con el script `make_admin.py`. No existe endpoint público para ello.

```bash
# Desde backend/ con el virtualenv activo:
python scripts/make_admin.py <username>
# → User '<username>' is now an admin.
```

Los admins tienen acceso a los endpoints `/api/v1/admin/*` (listar todos los usuarios, eliminar cualquier colección o usuario).

## Contenido público

El contenido compartido se expone en dos superficies sin autenticación:

- **`/feed`** — Feed global paginado: galería de imágenes + cards de textos compartidos.
- **`/users/:username`** — Perfil público de cualquier usuario: imágenes y textos compartidos, botón de compartir URL.

## Documentación

| Documento | Contenido |
|---|---|
| [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md) | Variables de entorno, modos, arranque, checklist de despliegue |
| [`docs/DOCUMENTATION.md`](docs/DOCUMENTATION.md) | Arquitectura, decisiones técnicas y roadmap |
| [`backend/README.md`](backend/README.md) | API, endpoints, tests, estructura del backend |
| [`frontend/README.md`](frontend/README.md) | Componentes, pantallas, autenticación, tests |
