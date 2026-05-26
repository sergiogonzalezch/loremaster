# STRATEGY.md — Evaluación técnica y hoja de ruta hacia producción

**Fecha:** 2026-05-20
**Contexto:** Evaluación honesta del estado del proyecto. Actualizado con prioridades definidas, roadmap ajustado a Semanas 9-12, y correcciones de deuda de documentación.

---

## 1. Fortalezas reales

### Infraestructura de evaluación
La inversión en harnesses es inusualmente sólida para un proyecto de esta escala. Tener evaluación automatizada en cinco dimensiones (RAG params, LLM params, prompt quality, image prompt, guard harness) con runner/judge/reporter y 83 casos de baseline refleja disciplina de ingeniería real. La mayoría de proyectos similares no tienen nada de esto. Es un activo que protege la calidad a medida que el proyecto evoluciona.

### Calidad de código consistente
0 errores de lint (Ruff + ESLint), 100/100 React Doctor, cero `any` en producción, useReducer correctamente aplicado, soft-delete en toda la capa de datos, separación limpia de capas (routes → services → domain/engine). El estándar se mantuvo alto durante todo el desarrollo.

### Trabajo de seguridad real
53 issues de seguridad cerrados, content guard multi-capa con evaluación cuantitativa, 300 tests. No es seguridad cosmética — los patrones tienen justificación documentada, los casos límite están probados (leetspeak, separadores, multilingüe, NFKD), y las decisiones de producto están anotadas con criterio de revisión futuro.

### Guardrails sobre textos entrantes
El content guard opera en tres puntos del pipeline:
- `check_user_input()` — valida queries y prompts del usuario antes del RAG
- `check_document_content()` — valida el texto extraído de documentos **al momento de la carga** (`document_service.py:116`), antes de chunking e indexado
- `check_generated_output()` — valida la salida del LLM antes de persistir

Los documentos subidos son escaneados automáticamente. Si el texto extraído contiene patrones bloqueados, la ingesta se rechaza con `ContentNotAllowedError` antes de llegar a Qdrant.

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

### 3.1 Cuello de botella: semáforo LLM (riesgo: Alto)

El semáforo de 1 llamada LLM concurrente funciona perfectamente en local para un usuario. Con dos usuarios generando contenido simultáneamente, uno espera bloqueado hasta que el otro termina.

**Síntoma actual:** `PUBLIC-001` falla en eval bajo carga — Ollama retorna 503 cuando el semáforo está ocupado.

**Estrategia recomendada:**
- Corto plazo: exponer `HTTP 429 Too Many Requests` con `Retry-After` en lugar de bloquear el worker.
- Medio plazo: cola de generación con `BackgroundTasks` de FastAPI + estado de job (`pending → running → done`).
- Largo plazo: worker separado (Celery + Redis o ARQ) si el volumen lo justifica.

### 3.2 Guard regex como primera línea, no como única (riesgo: Medio)

Los resultados J2=1 del harness muestran que `llama3.2` rechaza los prompts adversariales por su propio safety training. El guard es válido como segunda línea de defensa, pero con un modelo menos alineado los gaps documentados se vuelven explotables (jailbreaks estructurales, base64/ROT13, inyección vía delimitadores).

**Estrategia recomendada:**
- Documentar en `DEPLOY.md` los modelos validados (llama3.2, mistral:instruct).
- ✅ **Llama Guard 3 implementado (2026-05-25)** — `app/domain/llama_guard.py` integrado como segunda capa semántica tras `content_guard`. Fail-open. Activar con `LLAMA_GUARD_ENABLED=true` + `ollama pull llama-guard3:8b` (~4.9 GB, ~5 GB VRAM).

### 3.3 Features a completar para el deploy

| Feature | Estado real | Impacto |
|---|---|---|
| `backend/Dockerfile` | ✅ Implementado (multi-stage, usuario no-root) | — |
| Storage S3/R2 | Filesystem local funcional; S3 sin implementar | Imágenes no sobreviven restart del servidor |
| RunPod / GPU cloud | `runpod_client.py` no existe | Sin GPU cloud, generación de imágenes atada al host |
| Clerk en producción | Variables no probadas con tenant real | Auth Clerk no funciona en cloud sin validación |
| Redis caché semántica | Abandonado | Solo rate limiting activo — sin impacto en deploy |
| Sesiones deslizantes | Diferido — Issue #6 AUTH-CONTEXT | Diferir hasta que el volumen lo justifique |

### 3.4 Deuda de documentación — `entity_relations` ✅ Resuelta

`entity_relations` aparecía en los criterios de HU-05 y en la tabla ERD de DOCUMENTATION.md como característica planificada, pero **nunca fue implementada ni estuvo en el backlog activo**. Eliminada de DOCUMENTATION.md (HU-05 y tabla ERD) el 2026-05-20.

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

### Semana 9 — Deployable ✅ (completada 2026-05-25)

Objetivo: backend containerizado y concurrencia LLM resuelta.

- [x] `backend/Dockerfile` multi-stage — builder pre-descarga embedding model (~90 MB en imagen), runtime con usuario no-root `loremaster`
- [x] `backend/.dockerignore` — excluye venv, DB, media, tests, evals
- [x] `docker-compose.prod.yml` con servicio `app` — depends_on saludable (PG + Redis + Qdrant), volumen `media_data`, `host.docker.internal` para Ollama/ComfyUI
- [x] Health checks para PostgreSQL, Redis y Qdrant en compose prod
- [x] HTTP 429 + `Retry-After: 30` en el semáforo LLM — `LLMBusyError` en 3 rutas (rag_query, content, image_generation)
- [x] Índice FK `ix_entities_collection_id` — migración Alembic `a1b2c3d4e5f6`
- [x] Llama Guard 3 — implementado (`app/domain/llama_guard.py`); `LLAMA_GUARD_ENABLED=false` por defecto, activar en demo con `ollama pull llama-guard3:8b`

### Semana 9 (continuación) — Deploy storage + reporte de costos

> **Pendiente esta semana (2026-05-25):** completar antes de cerrar la semana.

- [ ] Prueba de despliegue con storage S3-compatible: MinIO (recomendado) o LocalStack — ver `docs/PLAN-DEPLOY-STORAGE.md`
- [ ] Reporte de costos finalizado — ver `docs/COST-REPORT.md` (completar con uso real medido)

### Semana 10 — Persistencia e integración

Objetivo: imágenes persistentes y Clerk validado.

- [ ] Decidir GPU cloud: RunPod Serverless vs Replicate vs filesystem para demo
- [ ] Storage S3/R2 en producción (construye sobre la prueba de Semana 9)
- [ ] Probar Clerk end-to-end con tenant real (`CLERK_JWKS_URL` + `CLERK_AUDIENCE`) — código ya implementado, solo configuración del tenant

### Semana 11 — GPU cloud e imagen en producción

Objetivo: flujo RAG imagen completo fuera del host del desarrollador.

- [ ] `runpod_client.py` si se decidió RunPod (Semana 10) — sino esta semana se redirige a polish
- [ ] Switch `IMAGE_BACKEND=runpod` transparente (mismo endpoint `/image-generation/generate`)
- [x] ~~Limpiar deuda de documentación: eliminar `entity_relations` de HU-05~~ — resuelto 2026-05-20

### Semana 12 — Demo + Evaluación final

Objetivo: entorno de demo funcional y documentación de portafolio.

- [ ] Entorno de demo configurado (Dockerfile + PostgreSQL + S3 o filesystem + ComfyUI/RunPod)
- [ ] Evaluación final: baseline evals + guard harness contra el entorno de demo
- [ ] Documentación de portafolio: README con setup completo, arquitectura, decisiones clave
- [ ] Evaluación final: baseline evals + guard harness contra el entorno de demo

### Post-Fase 3 (después de Semana 12)

Features complementarias a extender sin bloquear el deploy:
- Feed público y sistema de sharing
- Perfiles de usuario extendidos
- Panel de administración avanzado
- Redis caché semántica (si el volumen lo justifica)
- WebSocket / polling para generación LLM asíncrona
- Sesiones deslizantes Clerk (Issue #6)

---

## 6. Evaluación final

Para un prototipo de aprendizaje, el proyecto está en un estado excepcionalmente bueno. La disciplina de evaluación, testing y calidad de código es real y observable.

Para el deploy privado de portafolio, el único bloqueante real esta semana es el `Dockerfile`. Con eso resuelto y el HTTP 429 en el semáforo, el sistema es demostrable con un usuario a la vez usando auth local y filesystem. Clerk y S3 se añaden en Semanas 10-11 para un entorno completamente funcional.

El mayor riesgo no es técnico — es no decidir el GPU cloud a tiempo. Sin esa decisión en Semana 10, el flujo de imágenes queda atado al host del desarrollador para la demo final.
