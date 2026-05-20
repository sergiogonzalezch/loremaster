# STRATEGY.md — Evaluación técnica y hoja de ruta hacia producción

**Fecha:** 2026-05-20
**Contexto:** Evaluación honesta del estado del proyecto tras el sprint de seguridad + React Doctor 100/100.

---

## 1. Fortalezas reales

### Infraestructura de evaluación
La inversión en harnesses es inusualmente sólida para un proyecto de esta escala. Tener evaluación automatizada en cinco dimensiones (RAG params, LLM params, prompt quality, image prompt, guard harness) con runner/judge/reporter y 83 casos de baseline refleja disciplina de ingeniería real. La mayoría de proyectos similares no tienen nada de esto. Es un activo que protege la calidad a medida que el proyecto evoluciona.

### Calidad de código consistente
0 errores de lint (Ruff + ESLint), 100/100 React Doctor, cero `any` en producción, useReducer correctamente aplicado, soft-delete en toda la capa de datos, separación limpia de capas (routes → services → domain/engine). El estándar se mantuvo alto durante todo el desarrollo.

### Trabajo de seguridad real
53 issues de seguridad cerrados, content guard multi-capa con evaluación cuantitativa, 300 tests. No es seguridad cosmética — los patrones tienen justificación documentada, los casos límite están probados (leetspeak, separadores, multilingüe, NFKD), y las decisiones de producto están anotadas con criterio de revisión futuro.

---

## 2. Riesgos identificados

### 2.1 Cuello de botella: semáforo LLM (riesgo: Alto)

El semáforo de 1 llamada LLM concurrente funciona perfectamente en local para un usuario. Con dos usuarios generando contenido simultáneamente, uno espera bloqueado hasta que el otro termina. En producción real esto es inaceptable.

**Síntoma actual:** `PUBLIC-001` falla en eval bajo carga — Ollama retorna 503 cuando el semáforo está ocupado.

**Estrategia recomendada:**
- Corto plazo: exponer `HTTP 429 Too Many Requests` con `Retry-After` en lugar de bloquear el worker. El cliente puede reintentar.
- Medio plazo: cola de generación con `BackgroundTasks` de FastAPI + estado de job (`pending → running → done`). El frontend hace polling o recibe WebSocket event.
- Largo plazo: worker separado (Celery + Redis o ARQ) si el volumen lo justifica.

### 2.2 Guard regex como primera línea, no como única (riesgo: Medio)

Los resultados J2=1 del harness muestran que `llama3.2` rechaza los prompts adversariales por su propio safety training, no por el guard regex. El guard es válido como segunda línea de defensa, pero si alguien configura el sistema con un modelo menos alineado (Mistral sin instruct, un fine-tune sin RLHF), los gaps documentados en las LIMITACIONES del módulo se vuelven explotables:

- Jailbreaks estructurales (roleplay anidado, "DAN mode")
- Codificación base64 o ROT13
- Inyección de prompts vía delimitadores

**Estrategia recomendada:**
- Documentar en `DEPLOY.md` los modelos validados (llama3.2, mistral:instruct) y los no recomendados.
- Añadir Llama Guard 3 como capa semántica opcional en output (latencia ~500ms en GPU, configurable con fail-open). Ver arquitectura propuesta en §7.3 de STATUS.
- Nunca confiar en que el usuario final elegirá un modelo alineado.

### 2.3 Scope creep (riesgo: Medio — mantenimiento futuro)

El proyecto empezó como una herramienta de world-building y acumuló:
- Feed público + sistema de sharing
- Perfiles de usuario con avatar
- Panel de administración
- Integración Clerk (dual-auth)
- Generación de imágenes con ComfyUI
- Rate limiting con Redis
- Almacenamiento S3/R2

Cada una de estas capas es correcta en sí misma, pero juntas crean una superficie de mantenimiento amplia. Si el equipo es pequeño o el tiempo es limitado, el riesgo es que ninguna de ellas esté completamente produccionizada.

**Estrategia recomendada:** Definir explícitamente qué es **core** (RAG + entidades + colecciones) y qué es **extensión** (sharing, perfiles, feed). Priorizar core-completeness sobre feature-breadth antes del primer deploy real.

### 2.4 Features a medio terminar (riesgo: Bajo-Medio)

| Feature | Estado real | Riesgo |
|---|---|---|
| Storage S3/R2 | Filesystem local funcional; S3 sin implementar | Las imágenes generadas no sobreviven un restart del servidor |
| RunPod Serverless | Pendiente — `runpod_client.py` no existe | Sin GPU cloud, no hay generación de imágenes fuera del host del desarrollador |
| Redis caché semántica | Planificado, abandonado | Solo rate limiting activo; el plan de reducción de costos LLM no aplica |
| `entity_relations` | Tabla planeada, sin implementar | Característica prometida en HU-05 que no existe |
| Clerk en producción | `CLERK_JWKS_URL`/`CLERK_AUDIENCE` no probados con tenant real | Auth Clerk no funciona en ningún entorno cloud; solo modo local validado |
| Sesiones deslizantes | Diferido — Issue #6 AUTH-CONTEXT | `scheduleLogout` estabilizado pero sin awareness de tokens renovados por Clerk |

### 2.5 Clerk sin validación en producción (riesgo: Medio)

El flujo Clerk → `POST /auth/clerk/sync` → cookie HttpOnly funciona en local, pero nunca se ha probado con un tenant real de Clerk. Las variables `CLERK_JWKS_URL` y `CLERK_AUDIENCE` están documentadas en `DEPLOY.md` y en `.env.production.example` pero sin valores reales validados.

**Síntoma concreto:** si en producción se activa Clerk y las variables están mal configuradas, todos los usuarios Clerk quedan sin poder autenticarse. El modo local (`VITE_CLERK_PUBLISHABLE_KEY` vacío) sigue funcionando independientemente.

**Estrategia recomendada:**
- Corto plazo: probar el flujo completo con un tenant Clerk real en staging antes de cualquier deploy público.
- Largo plazo: el Issue #6 de AUTH-CONTEXT (sesiones deslizantes) requiere que el backend implemente refresh de expiración de Clerk — diferir hasta que el volumen de usuarios lo justifique.

---

## 3. Decisiones de producto pendientes

Estas decisiones bloquean o condicionan trabajo técnico — no tienen respuesta técnica correcta, dependen de visión de producto:

| Decisión | Opciones | Impacto técnico |
|---|---|---|
| **Público objetivo** | Escritores adultos vs familiar/educativo | Cambia los umbrales del content guard (HARM-15) |
| **Modelo en producción** | llama3.2 (3B, rápido) vs modelos más capaces | Calidad RAG, latencia, VRAM requerida |
| **Core vs extensión** | ¿Qué features son indispensables para el MVP real? | Define qué completar vs qué congelar |
| **GPU cloud** | RunPod vs Replicate vs sin imágenes en MVP | Desbloquea o elimina el flujo de generación de imágenes |

---

## 4. Hoja de ruta hacia producción — ordenada por impacto

> **Distinción importante (de DEPLOY.md):** hay ítems que bloquean solo _producción real_ (usuarios reales, dominio público) pero NO una _demo privada_. La demo privada con auth local, filesystem y ComfyUI local es viable hoy con solo el Dockerfile.

### Fase A — Demo privada funcional

1. **`backend/Dockerfile`** — Sin esto no hay forma de desplegar el backend fuera del host del desarrollador. Multi-stage build recomendado. Es el único bloqueante real para una demo.
2. **Resolver concurrencia LLM** — Al menos HTTP 429 + Retry-After. Sin esto, un segundo usuario rompe la experiencia del primero.

### Fase B — Producción real (usuarios externos)

3. **Clerk end-to-end en staging** — Probar `CLERK_JWKS_URL` + `CLERK_AUDIENCE` con un tenant real antes de cualquier deploy público. Sin esto, auth Clerk no funciona en cloud.
4. **Completar storage S3/R2** — Las imágenes generadas deben persistir entre reinicios. El filesystem local solo sirve para demo.
5. **Decidir sobre GPU cloud** — Sin RunPod (o alternativa), el flujo de imágenes no existe fuera del host del desarrollador. Opciones: RunPod Serverless, Replicate, o eliminar imágenes del MVP.

### Fase C — Solidez de producción

6. **Añadir Llama Guard 3 (opcional, fail-open)** — Capa semántica en output para modelos menos alineados.
7. **Documentar modelos validados en DEPLOY.md** — Qué modelos están validados (llama3.2, mistral:instruct), qué configuraciones son seguras.
8. **Resolver `entity_relations`** — Completar o eliminar de los criterios de aceptación de HU-05.

### Fase D — Calidad de experiencia

9. **WebSocket o polling para generación LLM** — La generación de contenido RAG es síncrona. Si tarda 10s, el usuario no sabe si el sistema responde.
10. **Sesiones deslizantes Clerk** — Issue #6 AUTH-CONTEXT: `scheduleLogout` sin awareness de tokens renovados. Diferir hasta que el volumen lo justifique.

---

## 5. Evaluación final

Para un prototipo de aprendizaje, el proyecto está en un estado excepcionalmente bueno. La disciplina de evaluación, testing y calidad de código es real y observable.

Para una **demo privada**, el único bloqueante real es el `Dockerfile` + concurrencia LLM. El resto (Clerk, S3, RunPod) no bloquea una demo con un usuario a la vez y auth local.

Para **producción real con usuarios externos**, los bloqueantes de Fases A y B son no negociables. El resto es calidad de experiencia que puede crecer iterativamente.

El mayor riesgo no es técnico — es definir claramente qué es este producto para evitar seguir añadiendo capas que lo hacen más complejo sin hacerlo más útil para el usuario que escribe mundos.
