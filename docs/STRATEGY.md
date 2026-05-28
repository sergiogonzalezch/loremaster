# STRATEGY.md — Evaluación técnica y hoja de ruta hacia producción

**Fecha:** 2026-05-27 (revisado 2026-05-27 — verificación contra código)
**Contexto:** Evaluación honesta del estado del proyecto. Actualizado tras cierre completo de Semana 9 y revisión de items pendientes contra el código fuente real.

---

## 1. Fortalezas reales

### Infraestructura de evaluación
La inversión en harnesses es inusualmente sólida para un proyecto de esta escala. Tener evaluación automatizada en cinco dimensiones (RAG params, LLM params, prompt quality, image prompt, guard harness) con runner/judge/reporter y 83 casos de baseline refleja disciplina de ingeniería real. La mayoría de proyectos similares no tienen nada de esto. Es un activo que protege la calidad a medida que el proyecto evoluciona.

### Calidad de código consistente
0 errores de lint (Ruff + ESLint), **89/100 React Doctor** (77 false positives de `unused-file` — react-doctor no detecta `main.tsx` como entry point de Vite; los 60 issues restantes bajaron de 56 a 60 issues reales tras la sesión de 2026-05-27), cero `any` en producción, useReducer correctamente aplicado, soft-delete en toda la capa de datos, separación limpia de capas (routes → services → domain/engine). El estándar se mantuvo alto durante todo el desarrollo.

### Trabajo de seguridad real
53 issues de seguridad cerrados + 1 finding del security review externo cerrado, content guard multi-capa con evaluación cuantitativa, 309 tests. No es seguridad cosmética — los patrones tienen justificación documentada, los casos límite están probados (leetspeak, separadores, multilingüe, NFKD), y las decisiones de producto están anotadas con criterio de revisión futuro.

### Guardrails sobre textos entrantes
El content guard opera en tres puntos del pipeline:
- `check_user_input()` — valida queries y prompts del usuario antes del RAG
- `check_document_content()` — valida el texto extraído de documentos **al momento de la carga** (`document_service.py:116`), antes de chunking e indexado
- `check_generated_output()` — valida la salida del LLM antes de persistir

Los documentos subidos son escaneados automáticamente. Si el texto extraído contiene patrones bloqueados, la ingesta se rechaza con `ContentNotAllowedError` antes de llegar a Qdrant.

### Stack de demo completamente containerizado
El stack de producción/demo corre entero en Docker con un único puerto expuesto al host (`:80`). Nginx actúa como reverse proxy: `/api/` → backend, `/media/` → Floci S3 interno. Backend, base de datos, vector store, caché y storage son invisibles al host. Las migraciones Alembic corren automáticamente en startup.

---

## 2. Prioridades definidas

El proyecto tiene tres niveles de prioridad claros:

| Nivel | Componentes | Razón |
|---|---|---|
| **Core** | RAG texto + RAG imagen (ComfyUI/GPU) | Es la propuesta de valor del producto |
| **Importante** | Usuarios + Auth (local + Clerk) | Trazabilidad de contenido subido y acciones del usuario; necesario para responsabilidad en entorno con acceso controlado |
| **Complementario** | Feed público, perfiles, admin, sharing | Funcional pero no define el producto; extender post-Fase 3 |

**Alcance del deploy:** el proyecto no se lanza a producción pública. El objetivo es un despliegue privado de calidad equivalente a producción, para portafolio con acceso aprobado por el propietario. Features complementarias se añaden después de la Semana 12.

---

## 3. Riesgos identificados

### 3.1 Cuello de botella: semáforo LLM ✅ Resuelto (corto plazo)

El semáforo de 1 llamada LLM concurrente funciona perfectamente en local para un usuario.

**Resuelto (2026-05-25):** HTTP 429 + `Retry-After: 30` implementado en las 3 rutas que usan el semáforo (`rag_query`, `content`, `image_generation`). El worker ya no bloquea — devuelve 429 inmediatamente si el semáforo está ocupado.

**Pendiente (medio/largo plazo):**
- Medio plazo: cola de generación con `BackgroundTasks` + estado de job (`pending → running → done`).
- Largo plazo: worker separado (Celery + Redis o ARQ) si el volumen lo justifica.

### 3.2 Guard regex como primera línea, no como única ✅ Resuelto

**Resuelto (2026-05-25):** Llama Guard 3 implementado como capa semántica adicional (`app/domain/llama_guard.py`). Fail-open. Activar con `LLAMA_GUARD_ENABLED=true` + `ollama pull llama-guard3:8b` (~4.9 GB, ~5 GB VRAM).

### 3.3 Features a completar para el deploy

| Feature | Estado real | Impacto |
|---|---|---|
| `backend/Dockerfile` | ✅ Multi-stage, usuario no-root, torch CPU-only (~2.6 GB) | — |
| `frontend/Dockerfile` | ✅ Multi-stage Vite + Nginx (~63 MB) | — |
| Storage S3-compatible | ✅ **Implementado** — `core/storage/s3_client.py` con boto3 funciona con AWS S3 real, Cloudflare R2 y Floci. En demo usa Floci; en cloud solo requiere credenciales en `.env.production` | Para cloud deploy: configurar `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_ENDPOINT_URL` y `STORAGE_BASE_URL` |
| RunPod / GPU cloud | ❌ `runpod_client.py` no existe — solo ComfyUI on-premise | Sin GPU cloud, generación de imágenes atada al host del desarrollador |
| Clerk en producción | ⚠️ **Código completo en main** — `auth_clerk.py`, `clerk.py`, 6 tests. Vars comentadas en compose. Solo falta configurar tenant real | Descomentar `CLERK_JWKS_URL` + `CLERK_AUDIENCE` en `.env.production` |
| Redis caché semántica | Abandonado | Solo rate limiting activo — sin impacto en deploy |
| Sesiones deslizantes | Diferido — Issue #6 AUTH-CONTEXT | Diferir hasta que el volumen lo justifique |

### 3.4 Deuda de documentación — `entity_relations` ✅ Resuelta

`entity_relations` aparecía en los criterios de HU-05 y en la tabla ERD de DOCUMENTATION.md como característica planificada, pero **nunca fue implementada ni estuvo en el backlog activo**. Eliminada de DOCUMENTATION.md el 2026-05-20.

---

## 4. Decisiones de producto

| Decisión | Estado |
|---|---|
| **Público objetivo** | ✅ Resuelto — herramienta narrativa para adultos (HARM-15 calibrado) |
| **Core vs extensión** | ✅ Resuelto — core: RAG + usuarios/auth; extensión: feed/perfiles/admin (post-Fase 3) |
| **GPU cloud para imágenes** | ⏳ Pendiente — RunPod Serverless vs Replicate vs filesystem para demo |
| **Modelo en producción** | ⏳ Pendiente — llama3.2 (3B, validado) vs modelos más capaces |

---

## 5. Hoja de ruta — Semanas 9-12

### Semana 9 — Deployable ✅ (completada 2026-05-27)

Objetivo: backend containerizado, concurrencia LLM resuelta, stack demo completo.

**Plan original:**
- [x] `backend/Dockerfile` multi-stage — builder pre-descarga embedding model, runtime con usuario no-root `loremaster`
- [x] `backend/.dockerignore` — excluye venv, DB, media, tests, evals
- [x] `docker-compose.prod.yml` con servicio `app` — depends_on saludable, volumen `media_data`, `host.docker.internal` para Ollama/ComfyUI
- [x] Health checks para PostgreSQL, Redis y Qdrant en compose prod
- [x] HTTP 429 + `Retry-After: 30` en el semáforo LLM — `LLMBusyError` en 3 rutas
- [x] Índice FK `ix_entities_collection_id` — migración Alembic
- [x] Llama Guard 3 — `app/domain/llama_guard.py`; fail-open, activar con `LLAMA_GUARD_ENABLED=true`

**Adicional implementado esta semana:**
- [x] `backend/Dockerfile` — torch CPU-only (`--index-url .../whl/cpu`), imagen reducida de ~6.6 GB a ~2.6 GB
- [x] `frontend/Dockerfile` + `nginx.conf` — multi-stage Vite + Nginx; 63 MB; único puerto 80 al host
- [x] `frontend/.dockerignore`
- [x] `docker-compose.prod.yml` — frontend service añadido; Floci y backend sin puertos al host; `STORAGE_BASE_URL=http://localhost/media` vía Nginx
- [x] `backend/docker-compose.debug.yml` — override local (gitignored) que expone puertos para inspección
- [x] Floci S3 integrado como storage de demo — imágenes servidas vía proxy Nginx `/media/`
- [x] CORS eliminado — toda comunicación pasa por Nginx en puerto 80
- [x] `make prod-rebuild` / `make prod-rebuild-api` / `make prod-rebuild-fe` — targets de rebuild selectivo
- [x] `make make-admin USER=<username>` — promueve usuario admin en stack Docker
- [x] Launchers actualizados: opción 9=prod-rebuild, opción 0=salir
- [x] Fix imagen URL en páginas públicas — `resolveImageUrl()` centralizado en `utils/media.ts`
- [x] Fix descarga de imagen con CORS fallback — `downloadImage()` con `cache: 'reload'`
- [x] Security review finding cerrado — `is_relative_to()` en `delete_image_service()`
- [x] Documentación actualizada: DEPLOY.md, README, frontend/README, ENVIRONMENT.md, WEEKLY_CHECKLISTS

**Pendiente de semana 9 continuación:**
- [ ] Reporte de costos finalizado — ver `docs/COST-REPORT.md`

### Semana 10 — GPU cloud + Clerk + TLS

Objetivo: flujo de imágenes en cloud y auth Clerk validada.

- [ ] **Decidir e implementar GPU cloud**: RunPod Serverless vs Replicate vs filesystem — `runpod_client.py` no existe aún
- [x] ~~Storage S3/R2 en producción real~~ — **ya implementado** (`core/storage/s3_client.py` con boto3; soporta AWS, R2 y Floci). Para cloud: solo configurar credenciales en `.env.production`
- [ ] **Clerk end-to-end con tenant real**: código completo en main; descomentar `CLERK_JWKS_URL` + `CLERK_AUDIENCE` en compose y `.env.production`
- [ ] **TLS/HTTPS**: Nginx solo tiene `listen 80`; necesario certbot o proxy externo antes de URL pública

### Semana 11 — GPU cloud e imagen en producción

Objetivo: flujo RAG imagen completo fuera del host del desarrollador.

- [ ] `runpod_client.py` si se decidió RunPod (Semana 10) — sino esta semana se redirige a polish
- [ ] Switch `IMAGE_BACKEND=runpod` transparente (mismo endpoint `/image-generation/generate`)
- [x] ~~Limpiar deuda de documentación: eliminar `entity_relations` de HU-05~~ — resuelto 2026-05-20

### Semana 12 — Demo + Evaluación final

Objetivo: entorno de demo funcional y documentación de portafolio.

- [ ] Evaluación final: baseline evals + guard harness contra el entorno de demo
- [ ] Documentación de portafolio: README con setup completo, arquitectura, decisiones clave

### Post-Fase 3 (después de Semana 12)

Features complementarias a extender sin bloquear el deploy:
- Feed público y sistema de sharing
- Perfiles de usuario extendidos
- Panel de administración avanzado
- Redis caché semántica (si el volumen lo justifica)
- WebSocket / polling para generación LLM asíncrona
- Sesiones deslizantes Clerk (Issue #6)

---

## 6. Deuda de infraestructura local/producción

Identificada en la revisión de arquitectura del 2026-05-27. Los cuatro puntos siguientes no bloquean el demo privado pero sí la mantenibilidad y el despliegue en un servidor diferente.

| # | Área | Descripción | Impacto | Prioridad |
|---|---|---|---|---|
| **INF-01** | `.env.production.example` raíz | ✅ Resuelto (2026-05-27) — `.env.production.example` creado en raíz con variables obligatorias y opcionales documentadas. `.env` añadido a `.gitignore` raíz. | **Alto** — bloqueaba el primer deploy en servidor limpio | ~~Semana 10~~ |
| **INF-02** | `STORAGE_BASE_URL` hardcodeado en compose | ✅ Resuelto (2026-05-27) — `docker-compose.prod.yml` cambiado a `${STORAGE_BASE_URL:-http://localhost/media}`. Demo local usa el fallback; cloud deploy sobreescribe via `.env`. | **Medio** — solo afectaba si el dominio cambiaba | ~~Semana 10~~ |
| **INF-03** | Triplicación de launchers | `.bat`, `.ps1`, `.sh` implementan la misma lógica de arranque en tres sitios. Cada fix de launcher requiere tres cambios. La solución canónica: `.ps1` como fuente de verdad; `.bat` como shim de una línea (`powershell.exe -File dev.ps1`); `.sh` detecta `pwsh` y delega. | **Bajo** — solo impacta mantenibilidad; el código funciona correctamente | **Post-Fase 3** — solo si hay más fixes de launcher |
| **INF-04** | PID stale en launchers | Si el terminal se cierra sin usar "salir", el PID guardado puede quedar huérfano. En Windows, un PID reutilizado por el sistema podría matar el proceso equivocado. Mitigación trivial: verificar que el proceso siga siendo `uvicorn` antes de `Stop-Process`. | **Muy bajo** — edge case en uso personal/demo con un usuario | **Post-Fase 3** — riesgo negligible en el alcance actual |

---

## 7. Evaluación final

Para un prototipo de aprendizaje, el proyecto está en un estado excepcionalmente bueno. La disciplina de evaluación, testing y calidad de código es real y observable.

El stack de demo es completamente funcional: un solo comando (`make prod-up`) levanta 6 servicios, aplica migraciones automáticamente, sirve el frontend compilado vía Nginx en el puerto 80, y almacena imágenes en Floci S3 con volúmenes persistentes. Esto es un deploy real, no un sketch.

El mayor riesgo para las semanas restantes sigue siendo la decisión de GPU cloud. Sin esa decisión en Semana 10, el flujo de imágenes queda atado al host del desarrollador para la demo final.

---

## 8. Referencias de consulta — mejoras pendientes

Documentos donde se registran puntos de mejora identificados pero no implementados todavía. Consultar aquí antes de planificar cada semana.

| Documento | Sección de mejoras | Contenido |
|---|---|---|
| [`docs/FIX.md`](FIX.md) | Tabla de estado rápido + Cobertura de tests | Deuda técnica activa (ítems 🟢 Cubierto sin acción inmediata): 13, 29, 30, 34, 35, 39, 42, 50. Tests pendientes de frontend: botón reintentar en error `CollectionsPage`. |
| [`docs/ENV-ARCHITECTURE.md §8`](ENV-ARCHITECTURE.md#8-puntos-de-mejora-identificados) | §8 — Puntos de mejora identificados | ~~Variables S3/R2 hardcodeadas~~ resuelto. `IMAGE_BACKEND` interpolable para RunPod (Semana 10). Inconsistencia `rate_limit_enabled` Python default vs compose fallback. Modelos Ollama configurables sin editar el YAML. |
| [`docs/DEPLOY.md`](DEPLOY.md) | Checklist de deploy | Estado actualizado del checklist operacional: qué está cubierto, qué falta para un deploy en servidor real (S3/R2, Clerk, dominio HTTPS). |
| [`docs/DOCUMENTATION.md`](DOCUMENTATION.md) | Roadmap / Decisiones pendientes | Decisiones de arquitectura diferidas: RunPod vs Replicate, modelo en producción, sesiones deslizantes Clerk. |

### Deuda técnica rápida — ítems sin fecha

Los siguientes ítems de `FIX.md` están documentados, mitigados y no bloquean el deploy, pero representan trabajo conocido antes de un lanzamiento público:

| Ítem | Descripción | Cuando abordar |
|---|---|---|
| FIX-13 | Bases `DomainError`/`InfrastructureError` — solo si se añade middleware global de excepciones | Post-Fase 3 |
| FIX-29 | Log "Auto-discarded" emitido antes de `session.commit()` | Post-Fase 3 |
| FIX-50 | `deletion_service.py` mezcla soft-delete + ficheros + Qdrant | Revisar al activar S3/R2 real en cloud deploy |