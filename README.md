# Lore Master

Plataforma RAG para escritores y narradores de rol. Carga documentos de lore, gestiona entidades de tu mundo y genera texto narrativo e imágenes coherentes con tu contexto. Cada usuario tiene sus propias colecciones privadas; el contenido individual (textos e imágenes) se puede compartir selectivamente en el feed público y en perfiles de usuario accesibles sin autenticación.

## Demo

Disponible en **[loremasterai.site](https://loremasterai.site)** (acceso por invitación — contactar al autor).

El stack completo corre en una única máquina personal expuesta via Cloudflare Named Tunnel (TLS en el borde, sin abrir puertos). Costo total de infraestructura: ~$1.98/año (dominio) + electricidad.

## Stack

| Capa | Tecnología |
|---|---|
| Backend | FastAPI · SQLModel · Qdrant · Ollama |
| Frontend | React 19 · TypeScript (strict) · Vite · Bootstrap 5 |
| Auth | JWT local (cookies HttpOnly + CSRF + refresh) · Clerk (RS256) |
| Imagen | ComfyUI (local) · RunPod Serverless (cloud, `IMAGE_BACKEND=runpod`) |
| Storage | S3-compatible boto3 — Floci (demo) · Cloudflare R2 (cloud) |
| Infraestructura | Docker · Nginx · PostgreSQL · Redis · Qdrant · Cloudflare Tunnel |

## Estructura del repo

```
loremaster/
├── backend/          → API REST + pipeline RAG
├── frontend/         → SPA React
├── docs/
│   ├── architecture/ → Referencia técnica (DEPLOY, ENVIRONMENT, DOCUMENTATION, LIMITERS…)
│   ├── planning/     → Seguimiento de tareas (STRATEGY, WEEKLY_CHECKLISTS, FIX)
│   ├── completed/    → Planes de implementación finalizados
│   └── README.md     → Índice completo de documentación
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

Ver [`docs/architecture/ENVIRONMENT.md`](docs/architecture/ENVIRONMENT.md) para la referencia completa de variables de entorno, modos (local/demo/producción) y checklist de despliegue.

## Usuarios y acceso

El registro está abierto. Cualquier usuario puede crear una cuenta via `POST /api/v1/auth/register`. Las colecciones pertenecen al usuario que las crea; otros usuarios no pueden editarlas ni eliminarlas.

La sesión se establece via **cookie HttpOnly** (frontend) o **Bearer token** (`Authorization: Bearer <token>`, para Swagger UI y herramientas externas). Ambos transportes usan el mismo JWT local. `POST /auth/logout` invalida los dos a la vez incrementando `token_version` en la base de datos.

**Refresh token (sesión 2026-05-28):** el access token dura **15 min** por diseño. Cuando expira, el frontend lo rota automáticamente vía `POST /auth/refresh` usando una cookie HttpOnly de refresh token (7 días, `path=/api/v1/auth/refresh`). El `AuthContext` programa el refresh 60 s antes de expirar (proactivo) y `apiClient.ts` reintenta refresh ante un 401 (reactivo, una sola vez por petición). Brute force en login mitigado además con delay progresivo client-side (2 s → 4 s → 8 s → cap 30 s).

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

Ver [`docs/architecture/DEPLOY.md`](docs/architecture/DEPLOY.md) para el runbook completo, checklist y acceso a servicios internos en debug.

Ver [`docs/architecture/ENV-ARCHITECTURE.md`](docs/architecture/ENV-ARCHITECTURE.md) para el flujo completo de variables: qué lee cada archivo, prioridad Pydantic, clasificación de variables y mejoras pendientes.

Ver [`backend/README.md`](backend/README.md) para la referencia completa de variables, ambientes y opciones del compose.

## Decisiones técnicas destacadas

- **Multi-tenant por `owner_id`:** colecciones, entidades y contenidos pertenecen al usuario que los crea. El aislamiento se aplica en capa de servicio (`get_*_or_404_owned`) — no solo en rutas — para que ningún bypass accidental de middleware exponga datos ajenos.
- **Auth dual sin bifurcación de middleware:** modo local (JWT HS256 en cookie HttpOnly + CSRF doble-submit + refresh 7 d) y modo Clerk (RS256). El backend usa siempre `verify_token()` sobre la cookie local; `ClerkBridge` en el frontend intercambia el JWT de Clerk por una sesión local en `/auth/clerk/sync`. Un solo middleware, dos flujos de login.
- **Soft-delete en cascada atómica:** `soft_delete(commit=False)` encadena todas las eliminaciones (colección → documentos + entidades → contenidos + imágenes) y hace un único `db_commit` al final, evitando estados inconsistentes entre DB, Qdrant y filesystem.
- **Moderación multicapa con harness de evaluación:** guardrail léxico (regex + normalización NFKD, leetspeak, separadores) en tres puntos del pipeline (input, texto de documento, output LLM); más Llama Guard 3 como capa semántica fail-open. Calibrado con 54 casos (18 categorías adversariales, 16 técnicas de bypass, 14 casos RPG legítimos).
- **Pipeline de imagen sin RAG (decisión validada):** evaluado experimentalmente en `metadata_harness`: añadir cabeceras de fuente Qdrant al prompt visual no mejoraba la calidad en modelos 3B (Δ D1 < +0.2). El prompt visual se construye directamente desde el texto del contenido confirmado, reduciendo latencia y complejidad sin pérdida de calidad.
- **Self-hosted sin costos de token:** toda la inferencia (texto con Ollama, embeddings con sentence-transformers, imagen con ComfyUI/Flux.2 Klein) corre en el host. Sin llamadas a APIs externas de pago. GPU cloud (RunPod Serverless) disponible como backend alternativo via `IMAGE_BACKEND=runpod` — mismo endpoint, sin cambio de código.

## Métricas de calidad

| Métrica | Resultado |
|---|---|
| Tests backend (`pytest`) | 309 / 309 |
| Tests frontend (`vitest`) | 121 / 121 |
| Baseline evals — 83 casos end-to-end con LLM | **83 / 83** (100 %) · 2026-06-08 |
| Guard harness — adversarial · bypass · RPG | **54 / 54** input correcto · 2026-06-08 |
| Ruff (lint Python) | 0 errores |
| ESLint (lint TypeScript) | 0 errores |
| `npm audit` | 0 vulnerabilidades |
| React Doctor | 94 / 100 |
| Issues de seguridad cerrados | 61 |

## Documentación

| Documento | Contenido |
|---|---|
| [`docs/architecture/ENVIRONMENT.md`](docs/architecture/ENVIRONMENT.md) | Variables de entorno, modos, arranque, checklist de despliegue |
| [`docs/architecture/ENV-ARCHITECTURE.md`](docs/architecture/ENV-ARCHITECTURE.md) | Flujo de variables (local vs Docker), mapeo Pydantic, mejoras pendientes |
| [`docs/architecture/DEPLOY.md`](docs/architecture/DEPLOY.md) | Runbook operacional: arranque, checklist, debug |
| [`docs/architecture/LIMITERS.md`](docs/architecture/LIMITERS.md) | Flujo de validación, límites input/output/DB y constantes del sistema |
| [`docs/architecture/DOCUMENTATION.md`](docs/architecture/DOCUMENTATION.md) | Arquitectura, decisiones técnicas y roadmap |
| [`docs/architecture/MOD.md`](docs/architecture/MOD.md) | Arquitectura del sistema de moderación y guardrails |
| [`docs/planning/FIX.md`](docs/planning/FIX.md) | Tracker de deuda técnica (61 issues, incluye sprint hardening 2026-05-28) |
| [`docs/planning/STRATEGY.md`](docs/planning/STRATEGY.md) | Estado del proyecto, riesgos, hoja de ruta Semanas 9-12, §9 React Doctor pendientes |
| [`backend/README.md`](backend/README.md) | API, endpoints, tests, ambientes, estructura del backend |
| [`frontend/README.md`](frontend/README.md) | Componentes, pantallas, autenticación, tests |
