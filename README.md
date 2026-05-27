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
├── dev.ps1           → Arranque completo del entorno local (Windows)
├── loremaster.bat    → Launcher con menu interactivo (Windows)
└── loremaster.sh     → Launcher con menu interactivo (Linux / macOS)
```

## Quick start

### Primera vez

```bash
git clone https://github.com/sergiogonzalezch/loremaster.git
cd loremaster

# Backend — configuración (el venv se crea automáticamente al arrancar)
cd backend
cp .env.example .env           # editar SECRET_KEY y las variables que correspondan
alembic upgrade head

# Frontend — dependencias
cd ../frontend
npm install
```

### Launcher interactivo (recomendado)

```powershell
# Windows
loremaster.bat
```

```bash
# Linux / macOS
chmod +x loremaster.sh
./loremaster.sh
```

Menu con una tecla: Dev SQLite/Postgres, solo infra, tests, prod up/down/rebuild. La opcion 0 cierra backend, frontend e infra Docker.

El launcher valida antes de arrancar: Python, npm, Docker corriendo y Ollama (aviso si no responde). El venv del backend se crea y sincroniza automáticamente en cada arranque.

### Arranque manual

```powershell
# Windows — abre backend y frontend en ventanas separadas
.\dev.ps1            # SQLite
.\dev.ps1 -Postgres  # PostgreSQL
```

```bash
make infra      # solo Qdrant + Redis
make infra-pg   # solo Qdrant + Redis + PostgreSQL
make down       # bajar infra dev (qdrant + redis + postgres)
```

Ver [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md) para la referencia completa de variables de entorno, modos (local/demo/producción) y checklist de despliegue.

## Usuarios y acceso

El registro está abierto. Cualquier usuario puede crear una cuenta via `POST /api/v1/auth/register`. Las colecciones pertenecen al usuario que las crea; otros usuarios no pueden editarlas ni eliminarlas.

La sesión se establece via **cookie HttpOnly** (frontend) o **Bearer token** (`Authorization: Bearer <token>`, para Swagger UI y herramientas externas). Ambos transportes usan el mismo JWT local. `POST /auth/logout` invalida los dos a la vez incrementando `token_version` en la base de datos.

### Crear el primer usuario admin

Los administradores se designan desde el servidor. No existe endpoint público para ello.

```bash
# En demo/producción (stack Docker corriendo):
make make-admin USER=<username>

# En desarrollo local (virtualenv activo en backend/):
python scripts/make_admin.py <username>
```

Los admins tienen acceso a los endpoints `/api/v1/admin/*` (listar todos los usuarios, eliminar cualquier colección o usuario).

## Contenido público

El contenido compartido se expone en dos superficies sin autenticación:

- **`/feed`** — Feed global paginado: galería de imágenes + cards de textos compartidos.
- **`/users/:username`** — Perfil público de cualquier usuario: imágenes y textos compartidos, botón de compartir URL.

## Ambientes

El proyecto define tres entornos. Cambiar entre ellos **no requiere tocar `.env`**:

| | Local (dev) | Demo | Producción |
|---|---|---|---|
| **DB** | SQLite (`loremaster.db`) | PostgreSQL (contenedor) | PostgreSQL |
| **Storage** | disco local (`backend/media/`) | Floci S3 | S3 / R2 real |
| **Auth** | JWT local (formulario propio) | Clerk (acceso privado) | Clerk (acceso público) |
| **Acceso** | solo tú | portafolio — usuarios invitados | lanzamiento público |
| **Config** | `backend/.env` (copiado de `.env.example`) | `.env.production` (copiado de `.env.production.example`) | CI/CD + secrets manager |

**Demo** es el objetivo realista actual: stack containerizado con Floci como emulador S3 y Clerk para controlar quién accede. **Producción** sería un lanzamiento público, aspiracional y sin fecha definida.

## Deploy (demo)

El `docker-compose.prod.yml` levanta el stack completo de demo — PostgreSQL + Qdrant + Redis + Floci (S3) + backend API + frontend Nginx — exponiendo solo el puerto 80:

```bash
# Desde la raíz del repo:
make prod-up         # levanta todo (construye si no existe imagen)
make prod-down       # baja todo
make prod-rebuild    # reconstruye backend + frontend tras cambios de código
make prod-rebuild-api  # solo backend
make prod-rebuild-fe   # solo frontend
```

Copiar `.env.production.example` como `.env.production` en la raíz y editar los valores reales (`SECRET_KEY`, `POSTGRES_PASSWORD`, `ALLOWED_ORIGINS=["http://localhost"]`). Docker Compose lee `.env.production` vía `--env-file` e inyecta las variables en el contenedor; Pydantic las lee desde el entorno del proceso.

Verificar que las variables se resuelven correctamente antes de levantar:

```bash
docker compose -f backend/docker-compose.prod.yml --env-file .env.production config
```

Ver [`docs/DEPLOY.md`](docs/DEPLOY.md) para el runbook completo, checklist y acceso a servicios internos en debug.

Ver [`docs/ENV-ARCHITECTURE.md`](docs/ENV-ARCHITECTURE.md) para el flujo completo de variables: qué lee cada archivo, prioridad Pydantic, clasificación de variables y mejoras pendientes.

Ver [`backend/README.md`](backend/README.md) para la referencia completa de variables, ambientes y opciones del compose.

## Documentación

| Documento | Contenido |
|---|---|
| [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md) | Variables de entorno, modos, arranque, checklist de despliegue |
| [`docs/ENV-ARCHITECTURE.md`](docs/ENV-ARCHITECTURE.md) | Flujo de variables (local vs Docker), mapeo Pydantic, mejoras pendientes |
| [`docs/DEPLOY.md`](docs/DEPLOY.md) | Runbook operacional: arranque, checklist, debug |
| [`docs/LIMITERS.md`](docs/LIMITERS.md) | Flujo de validación, límites input/output/DB y constantes del sistema |
| [`docs/DOCUMENTATION.md`](docs/DOCUMENTATION.md) | Arquitectura, decisiones técnicas y roadmap |
| [`docs/MOD.md`](docs/MOD.md) | Arquitectura del sistema de moderación y guardrails |
| [`docs/FIX.md`](docs/FIX.md) | Tracker de deuda técnica |
| [`docs/STRATEGY.md`](docs/STRATEGY.md) | Estado del proyecto, riesgos, hoja de ruta Semanas 9-12 |
| [`backend/README.md`](backend/README.md) | API, endpoints, tests, ambientes, estructura del backend |
| [`frontend/README.md`](frontend/README.md) | Componentes, pantallas, autenticación, tests |
