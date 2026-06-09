# STRATEGY.md — Evaluación técnica y hoja de ruta hacia producción

**Fecha:** 2026-05-28 (revisado 2026-06-02 — Named Tunnel `loremasterai.site` activo, R2 activo, SafeImage fix, nginx upload limit)
**Contexto:** Evaluación honesta del estado del proyecto. Actualizado tras cierre completo de Semana 9, revisión de items pendientes y sprint de seguridad/calidad (rama `bugfix/issues-security`).

---

## 0. Estado rápido — pendientes y resueltos

> Sección de consulta rápida. Verificado contra el código el 2026-05-27.

### Pendiente Semana 10–11

| # | Item | Esfuerzo | Bloqueante para |
|---|---|---|---|
| P1 | **RunPod — implementar métodos del cliente** — skeleton creado; métodos pendientes de implementar y conectar en `_backends.py` | Medio | Imágenes fuera del host |
| ~~P3~~ | ~~**Deploy Cloudflare**~~ — ✅ Resuelto 2026-06-02 | — | — |

### Pendiente sin fecha urgente (no bloquea demo)

| # | Item | Cuándo |
|---|---|---|
| ~~P2~~ | ~~**Clerk end-to-end**~~ — ✅ Resuelto 2026-06-01 | — |
| ~~P3~~ | ~~**TLS/HTTPS via VPS**~~ — reemplazado por plan Cloudflare Tunnel (gratis, sin VPS) | — |
| ~~P4~~ | ~~**Variables S3/R2 interpolables**~~ — ✅ Resuelto 2026-06-01 | — |
| P5 | **Modelos Ollama configurables** — `${OLLAMA_MODEL:-llama3.2:latest}` en compose | Calidad de vida; sin urgencia |
| P6 | **Cola de generación** — `BackgroundTasks` + job state `pending→running→done` | Si el volumen lo justifica |

### Resuelto (referencia)

| Item | Estado | Dónde |
|---|---|---|
| Dockerfile backend multi-stage (torch CPU-only, ~2.6 GB) | ✅ | `backend/Dockerfile` |
| Dockerfile frontend multi-stage (Nginx, ~63 MB) | ✅ | `frontend/Dockerfile` |
| Stack demo completo (`make prod-up`, 6 servicios, puerto :80) | ✅ | `docker-compose.prod.yml` |
| Storage S3-compatible con boto3 (AWS, R2, Floci) | ✅ | `core/storage/s3_client.py` |
| Semáforo LLM → HTTP 429 + `Retry-After: 30` | ✅ | `rag_query.py`, `content.py`, `image_generation.py` |
| Llama Guard 3 — capa semántica fail-open | ✅ | `app/domain/llama_guard.py` |
| Clerk — end-to-end con tenant real (8 tests, fusión por email, JWT template) | ✅ | `auth_clerk.py`, `clerk.py`, `.env.production` |
| RunPod — skeleton `runpod_client.py` + `IMAGE_BACKEND` interpolable | ✅ skeleton | `engine/runpod_client.py`, `docker-compose.prod.yml` |
| Deploy Cloudflare — Named Tunnel `loremasterai.site` + R2 activo, URL fija, 5 fases completas | ✅ 2026-06-02 | `docs/architecture/DEPLOY-CLOUDFLARE.md` |
| Documentación reorganizada en architecture/ planning/ completed/ | ✅ | `docs/` |
| Migración FK `ix_entities_collection_id` | ✅ | Alembic |
| Path traversal guard en `delete_image_service` | ✅ | `image_generation_service.py` |
| CORS eliminado — todo pasa por Nginx en :80 | ✅ | `nginx.conf` |
| Refresh token (access 15 min + refresh 7 d) + brute-force delay | ✅ | `auth.py`, `apiClient.ts`, `AuthContext.tsx` |
| Cascadas atómicas (`soft_delete(commit=False)`) | ✅ | `soft_delete.py`, `deletion_service.py`, `cascade_service.py` |
| Bug ImageGenerations huérfanas + migración data-fix | ✅ | `image_generation_service.py`, Alembic `782abfe638bf` |
| CSP en `index.html` + S3 CORS restringido + SVG XSS bloqueado | ✅ | `index.html`, `lifespan.py`, `utils/strings.ts` |
| 4 vulnerabilidades npm parchadas (happy-dom RCE, js-cookie, etc.) | ✅ | `package-lock.json` |
| React Doctor 94/100 (subió 81→94 en sesiones sucesivas) | ✅ | Frontend |
| Tests: 309 backend · 121 frontend | ✅ | — |
| Ruff 0 errores · ESLint 0 errores | ✅ | — |
| `npm audit`: 0 vulnerabilidades | ✅ | — |
| Integridad BD verificada (0 huérfanos en 8 relaciones de cascade) | ✅ | — |

---

## 1. Fortalezas reales

### Infraestructura de evaluación
La inversión en harnesses es inusualmente sólida para un proyecto de esta escala. Tener evaluación automatizada en cinco dimensiones (RAG params, LLM params, prompt quality, image prompt, guard harness) con runner/judge/reporter y 83 casos de baseline refleja disciplina de ingeniería real. La mayoría de proyectos similares no tienen nada de esto. Es un activo que protege la calidad a medida que el proyecto evoluciona.

### Calidad de código consistente
0 errores de lint (Ruff + ESLint), **89/100 React Doctor** (subió de 81→89 en sesión 2026-05-27; los 77 warnings de `unused-file` son false positives estructurales — react-doctor no detecta `main.tsx` como entry point de Vite y no tiene config de `entryPoints`), cero `any` en producción, useReducer correctamente aplicado, soft-delete en toda la capa de datos, separación limpia de capas (routes → services → domain/engine). El estándar se mantuvo alto durante todo el desarrollo.

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
- [x] Reporte de costos finalizado — ver `docs/architecture/COST-REPORT.md` (completado 2026-05-27)

### Semana 10 — GPU cloud + Clerk + TLS (cerrada 2026-06-01)

Objetivo: flujo de imágenes en cloud y auth Clerk validada.

- [x] **Variables S3/R2 interpolables** — `${VAR:-fallback}` en compose; demo usa Floci, cloud usa R2
- [x] **Clerk end-to-end con tenant real** — `CLERK_JWKS_URL` + `CLERK_AUDIENCE` activos; JWT template con `email`; fusión de cuentas por email; 8 tests
- [x] **RunPod skeleton** — `engine/runpod_client.py` con interfaz completa (métodos pendientes de implementar); `IMAGE_BACKEND` interpolable en compose; `runpod_api_key` + `runpod_endpoint_id` en Settings
- [x] **TLS/HTTPS → reemplazado** — sin presupuesto para VPS ni dominio; plan alternativo: Cloudflare Tunnel (gratis, HTTPS automático, sin abrir puertos) + R2 (storage gratuito). Ver `docs/architecture/DEPLOY-CLOUDFLARE.md`
- [x] **Documentación reorganizada** — `docs/architecture/`, `docs/planning/`, `docs/completed/`; todos los README actualizados

### Semana 11 — Deploy Cloudflare + RunPod implementado

Objetivo: app accesible públicamente vía Cloudflare Tunnel y generación de imágenes probada en cloud.

- [x] **Activar deploy Cloudflare**: `cloudflared` instalado, bucket R2 `loremaster-media` activo, `.env.production` configurado, tunnel verificado. Ver `DEPLOY-CLOUDFLARE.md`
- [ ] **Implementar RunPod client**: completar métodos `submit_workflow`, `get_status`, `wait_for_completion`, `extract_image_bytes`; conectar en `_backends.py` con `elif params.backend == "runpod"`; fondear wallet RunPod (~$4) y probar generación end-to-end
- [x] ~~Limpiar deuda de documentación: eliminar `entity_relations` de HU-05~~ — resuelto 2026-05-20

### Semana 12 — Demo + Evaluación final ✅ (cerrada 2026-06-08)

Objetivo: entorno de demo funcional y documentación de portafolio.

- [x] **Evaluación final**: baseline evals 83/83 (100 %) + guard harness 54/54 · 2026-06-08
- [x] **Documentación de portafolio**: README actualizado con demo URL, decisiones técnicas, métricas de calidad · 2026-06-08
- [x] **Demo**: en vivo cada sábado (no grabada); flujo end-to-end cubierto por baseline evals 83/83

### Semana 13 (post-roadmap) — Redis + Métricas

Objetivo: implementar las dos features de Semana 12 que quedaron pendientes por priorización.

- [x] **Martes 2026-06-09 — Redis caché semántica**: `engine/semantic_cache.py`; coseno ≥ 0.95; TTL 3600 s; fail-open; 10 tests · 2026-06-09
- [ ] **Miércoles 2026-06-11 — Métricas Prometheus + Grafana**: instrumentar endpoints clave, dashboard básico

### Post-roadmap (sin fecha)

Features complementarias a extender sin bloquear el deploy:
- Feed público y sistema de sharing (ya implementado, extender post-Fase 3)
- Perfiles de usuario extendidos
- Panel de administración avanzado
- WebSocket / polling para generación LLM asíncrona
- Sesiones deslizantes Clerk (Issue #6)
- RunPod — verificación en GPU real cuando haya saldo (~$4)

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
| [`docs/ENV-ARCHITECTURE.md §8`](../architecture/ENV-ARCHITECTURE.md#8-puntos-de-mejora-identificados) | §8 — Puntos de mejora identificados | ~~Variables S3/R2 hardcodeadas~~ resuelto. `IMAGE_BACKEND` interpolable para RunPod (Semana 10). Inconsistencia `rate_limit_enabled` Python default vs compose fallback. Modelos Ollama configurables sin editar el YAML. |
| [`docs/DEPLOY.md`](../architecture/DEPLOY.md) | Checklist de deploy | Estado actualizado del checklist operacional: qué está cubierto, qué falta para un deploy en servidor real (S3/R2, Clerk, dominio HTTPS). |
| [`docs/DOCUMENTATION.md`](../architecture/DOCUMENTATION.md) | Roadmap / Decisiones pendientes | Decisiones de arquitectura diferidas: RunPod vs Replicate, modelo en producción, sesiones deslizantes Clerk. |

### Deuda técnica rápida — ítems sin fecha

Los siguientes ítems de `FIX.md` están documentados, mitigados y no bloquean el deploy, pero representan trabajo conocido antes de un lanzamiento público:

| Ítem | Descripción | Cuando abordar |
|---|---|---|
| FIX-13 | Bases `DomainError`/`InfrastructureError` — solo si se añade middleware global de excepciones | Post-Fase 3 |
| FIX-29 | Log "Auto-discarded" emitido antes de `session.commit()` | Post-Fase 3 |
| FIX-50 | `deletion_service.py` mezcla soft-delete + ficheros + Qdrant | Revisar al activar S3/R2 real en cloud deploy |

---

## 9. React Doctor — pendientes y techo práctico

**Estado actual: 94/100** (subió 81→88→91→93→95→94 a lo largo del proyecto).

La regresión de 95→94 vino del fix del bug visual de `ModelSelector` (tri-state `loading|ready|hidden` para evitar layout shift): el linter detecta 3 `setState` en el `useEffect` aunque sean ramas mutuamente excluyentes (`no-cascading-set-state`). Aceptada conscientemente porque el bug visible al usuario era prioritario.

El techo realista alcanzable sin sprint dedicado de refactor visual es **95-96**. Los 14 issues restantes se dividen entre refactor mayor con riesgo de regresión y falsos positivos de la herramienta.

### 9.1 Refactor mayor — `no-giant-component` ×7

Componentes >300 líneas. Partirlos en sub-componentes daría ~+3 puntos pero requiere validación visual por componente. Cada uno es un refactor con riesgo de regresión.

| Componente | Líneas | Sub-componentes sugeridos |
|---|---|---|
| `DocumentsTab.tsx` | ~770 | `<DocumentFilters>`, `<DocumentList>`, `<UploadSection>`, `<DocumentDetailModal>` |
| `ImagePanel.tsx` | ~700 | `<GenerateTab>`, `<HistoryTab>`, `<ImagePreviewModal>` |
| `CollectionsPage.tsx` | ~620 | `<CollectionFilters>`, `<CollectionGrid>`, `<CollectionModals>` |
| `ContentCard.tsx` | ~570 | `<ContentHeader>`, `<ContentActions>`, `<EditModal>` |
| `EntitiesTab.tsx` | ~440 | `<EntityFilters>`, `<EntityCreateModal>` |
| `ProfilePage.tsx` | ~370 | `<AvatarUploader>` |
| `PublicProfilePage.tsx` | 332 | `<ProfileHeader>`, `<SharedImagesSection>`, `<SharedContentsSection>` |

**Esfuerzo estimado:** 3-5 días total. **Riesgo:** medio — necesita pruebas manuales de UX por componente. **Cuándo:** Post-Fase 3, sprint dedicado.

### 9.2 Falsos positivos documentados (no tocar)

Estos warnings persisten pero no son arreglables sin introducir bugs o cambiar a API experimental:

| Issue | Archivo:Línea | Por qué es falso positivo |
|---|---|---|
| `deslop/unused-file` ×77 | varios | react-doctor no traza routing dinámico de Vite SPA (`main.tsx → App.tsx → React Router`). Los 77 archivos sí se alcanzan en runtime. **Resta ~5-7 puntos del techo**. |
| `no-derived-state` ×2 | `CollectionDetailPage/index.tsx:44`, `AdminPage:62` | `loading` viene de `useEffect → fetchX → setLoading(false)`. NO es estado derivado de props — es estado de fetch async, no se puede computar inline en render |
| `async-defer-await` | `useGenerate.ts:81` | El guard `if (!isMountedRef.current)` **debe** ejecutarse DESPUÉS del await — verifica que el componente sigue montado tras la operación async. Moverlo antes cambia la semántica. |
| `no-pass-live-state-to-parent` | `EntityContentsPanel:54` | Ya refactorizado a event-driven (`onContentMutated`). El linter detecta otro patrón residual, requiere revisión profunda para confirmar. |
| `exhaustive-deps` | `AuthContext:151` | Ya está bien — el cleanup copia `logoutTimerRef.current` a `const timer` antes de usarlo |
| `prefer-use-effect-event` | `DocumentsTab:313` | `useEffectEvent` aún es API experimental en React 19, no usable en producción estable |

### 9.3 Recomendación

**Parar en 95.** Los componentes gigantes son deuda real pero su refactor pertenece a un sprint dedicado de UX/refactor visual, no a un cleanup de mantenibilidad. Los demás warnings son limitaciones de la herramienta que no se pueden cerrar sin introducir bugs o adoptar APIs experimentales.