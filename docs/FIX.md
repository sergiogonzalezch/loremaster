# Problemas pendientes de corrección

Lista de tech debt identificado y aún no corregido. Ordenado por impacto estimado.

---

## Tabla de estado rápido

| # | Descripción | Capa | Estado | Acción |
|---|-------------|------|--------|--------|
| 1 | Sin autenticación | Backend | 🔴 Pendiente | Implementar — crítico pre-deploy |
| 2 | Ingest de documentos síncrono | Backend | ✅ Resuelto | — |
| 3 | Sin optimistic updates en contenidos | Frontend | ✅ Resuelto | — |
| 4 | Token counter aproximado | Backend + Frontend | ✅ Resuelto | — |
| 5 | Extracción de documentos sin timeout | Backend | 🟡 Pendiente | Implementar después — `ThreadPoolExecutor` + `asyncio.wait_for(30s)` |
| 6 | Cascading delete no atómico | Backend | 🟢 Cubierto | Observación — retry existente suficiente; revisar si `cascade_delete_collection` se vuelve async |
| 7 | Background task sin recuperación | Backend | 🔴 Pendiente | Implementar — endpoint `POST /documents/{id}/retry` + campo `processing_error` |
| 8 | Race condition en optimistic updates | Frontend | ✅ Resuelto | — |
| 9 | `EntityDetailPage` excede SRP (~720 líneas) | Frontend | 🟡 Pendiente | Implementar después — extraer `EntityEditForm` y `EntityContentsPanel` |
| 10 | Paginación duplicada en frontend | Frontend | 🟡 Pendiente | Implementar después — hook `usePagination(totalItems, pageSize)` |
| 11 | `MAX_PENDING_CONTENTS` hardcodeado | Backend + Frontend | 🟡 Pendiente | Implementar después — plan 4 pasos: `config.py` → `generation_service` → `metadata` endpoint → frontend |
| 12 | Validación de categoría duplicada | Backend | ✅ Incorrecto | — (no había duplicación real) |
| 13 | Jerarquía de excepciones plana | Backend | 🟢 Cubierto | Observación — todos los primitivos eliminados; bases `DomainError`/`InfrastructureError` solo si se necesita middleware global |
| 14 | `ValueError("discarded")` como señal de dominio | Backend | ✅ Resuelto | — |
| 15 | `RuntimeError` en `check_generated_output` conflado con infra | Backend | ✅ Resuelto | — |
| 16 | Función privada `_fetch_counts` importada en route | Backend | 🟡 Pendiente | Implementar después — renombrar a pública o crear `get_collection_with_counts_service` |

**Leyenda:** 🔴 Pendiente urgente · 🟡 Pendiente no urgente · 🟢 Cubierto (mitigado, sin acción inmediata) · ✅ Cerrado

---

## 1. Sin autenticación

**Capa:** Backend  
**Impacto:** Alto — crítico para cualquier despliegue fuera de entorno local.

Todos los endpoints son públicos. No hay API keys, JWT ni ningún mecanismo de identidad. Cualquier cliente con acceso a la red puede leer, escribir o borrar colecciones, entidades y documentos.

**Solución sugerida:** Añadir autenticación HTTP Basic o JWT con middleware de FastAPI. Para un proyecto single-user, un API key estático configurado vía `.env` es suficiente en primera iteración.

---

## ~~2. Ingest de documentos síncrono~~ ✅ Resuelto

**Capa:** Backend  
**Solución aplicada:** El endpoint `POST /documents` ahora devuelve `202 Accepted` inmediatamente tras crear el registro en DB con `status=processing`. La fase pesada (`ingest_chunks` → Qdrant → embeddings) se ejecuta como `BackgroundTask` de FastAPI usando la misma sesión de BD inyectada por dependencia. El frontend ya tenía polling de estado (`useCollectionDocumentsStatus`) que soporta esta UX sin cambios.

---

## ~~3. Sin optimistic updates en la lista de contenidos~~ ✅ Resuelto

**Capa:** Frontend  
**Solución aplicada:** `ContentCard` aplica ahora actualizaciones optimistas antes de cada llamada a la API (confirm → `status: confirmed` + descarte de hermanos; discard → `status: discarded`; delete → eliminación inmediata; edit → actualiza `content` y `updated_at`). Si la API falla, revierte al estado anterior. El `handleContentAction` en `EntityDetailPage` usa `{ silent: true }` en `refreshContents` para la sincronización en background, eliminando el parpadeo del spinner.

---

## ~~4. Token counter aproximado~~ ✅ Resuelto

**Capa:** Backend + Frontend  
**Solución aplicada:** `EntityContent` incluye ahora el campo `token_count` (heurística `len(answer) // 4` calculada en el backend tras generar). Se añadió migración Alembic (`a1b2c3d4e5f6`). El frontend muestra `~N tokens` como badge en el `ContentCard`, junto al badge de fuentes, cuando el valor es mayor que 0.

---

---

## 5. Extracción de documentos sin timeout

**Capa:** Backend  
**Archivo:** `backend/app/engine/extractor.py`, `backend/app/services/documents_service.py`  
**Impacto:** Medio — el límite de tamaño mitiga el caso más común, pero un PDF válido en tamaño y malformado en estructura puede aún colgar el proceso.

`documents_service.py:26` ya define `MAX_BYTES = 50 * 1024 * 1024` y lo valida en la línea 42 antes de llamar al extractor. Esto descarta archivos demasiado grandes. Sin embargo, `extract_text()` se invoca sin timeout: un PDF dentro del límite pero con estructura corrupta puede hacer que PyPDF itere indefinidamente.

**Solución sugerida:** Ejecutar la extracción en un `ThreadPoolExecutor` con `asyncio.wait_for(..., timeout=30)` para acotar el tiempo máximo independientemente del contenido del archivo.

---

## 6. Cascading delete no es atómico

**Capa:** Backend  
**Archivo:** `backend/app/services/deletion_service.py`  
**Impacto:** Bajo — la implementación existente ya mitiga el riesgo con retry y logging.

Ya existe `_delete_vectors_with_retry` con 3 intentos y 0.5s entre intentos. Si los 3 fallan, loguea `ERROR` con `"Orphan vectors remain"` y retorna `False`. La ruta de colecciones loguea `WARNING` si recibe `False`. El único problema real es `time.sleep()` bloqueando el event loop, pero al ser sync y máximo 1.5s total es aceptable para este volumen.

**Solución sugerida:** Cambio mínimo — reemplazar `time.sleep(_QDRANT_RETRY_DELAY)` por `asyncio.sleep()` si en algún momento `cascade_delete_collection` se convierte en función async. Por ahora no requiere acción.

---

## 7. Background task de ingestión sin recuperación

**Capa:** Backend  
**Archivo:** `backend/app/services/documents_service.py`  
**Impacto:** Alto — documentos quedan en estado `failed` permanentemente sin forma de reintentar.

Si `process_ingest_background` falla (timeout de Qdrant, error de embeddings), el documento queda en `status=failed` sin mecanismo de retry ni notificación al usuario más allá del polling de estado.

**Solución sugerida:** Añadir un endpoint `POST /documents/{id}/retry` que permita reintentar la ingestión. Registrar el error detallado en el campo `processing_error` del documento.

---

## ~~8. Race condition en optimistic updates~~ ✅ Resuelto

**Capa:** Frontend  
**Solución verificada:** `ContentCard.tsx:48` ya tiene `const [busy, setBusy] = useState(false)`. Todos los botones de acción tienen `disabled={busy}`, y `setBusy(true)` se llama al inicio de cada handler (confirm, discard, delete). El modal de edición usa `saving` de forma separada y bloquea la UI durante la operación. En la práctica la race condition descrita no puede ocurrir.

---

## 9. `EntityDetailPage.tsx` excede responsabilidad única

**Capa:** Frontend  
**Archivo:** `frontend/src/pages/EntityDetailPage.tsx` (~720 líneas, ~20 `useState`)  
**Impacto:** Medio — dificulta el testing y el mantenimiento.

El componente mezcla lógica de generación, edición de contenidos, paginación y display en un solo archivo. Hay ~20 `useState` directos sin ninguna composición.

**Solución sugerida:** Extraer el formulario de edición a `EntityEditForm.tsx` y la sección de contenidos generados a `EntityContentsPanel.tsx`. Agrupar el estado relacionado con `useReducer` o mover la lógica a hooks especializados.

---

## 10. Lógica de paginación duplicada en frontend

**Capa:** Frontend  
**Archivos:** `CollectionsPage.tsx`, `CollectionDetailPage.tsx`, `EntityDetailPage.tsx`  
**Impacto:** Medio — DRY violation; un cambio en el comportamiento de paginación debe hacerse en tres sitios.

Cada página implementa su propia lógica de control de página (botones anterior/siguiente, cálculo de total de páginas, reset al filtrar).

**Solución sugerida:** Crear un hook `usePagination(totalItems, pageSize)` que centralice el estado y los handlers.

---

## 11. `MAX_PENDING_CONTENTS` hardcodeado en frontend y backend

**Capa:** Backend + Frontend  
**Archivos afectados:**
- `backend/app/services/generation_service.py:18` — constante de módulo `MAX_PENDING_CONTENTS = 5`
- `backend/app/api/routes/metadata.py` — endpoint solo expone `ENTITY_CATEGORY_MAP`
- `frontend/src/utils/constants.ts:34` — `export const MAX_PENDING_CONTENTS = 5` duplicado
- `frontend/src/pages/EntityDetailPage.tsx` — consume la constante local en líneas 116, 407, 453, 505  
**Impacto:** Bajo — si el backend cambia el límite, el frontend muestra información incorrecta.

El valor `5` está duplicado sin sincronización. `config.py` ya usa `pydantic-settings` con `BaseSettings`; añadir el campo es trivial y lo haría configurable desde `.env`.

**Plan de implementación:**

1. `backend/app/core/config.py` — añadir `max_pending_contents: int = 5` a `Settings`.
2. `backend/app/services/generation_service.py` — eliminar la constante de módulo y reemplazar los usos por `settings.max_pending_contents`.
3. `backend/app/api/routes/metadata.py` — extender el endpoint `/entity-categories` (o añadir `/limits`) para devolver también `max_pending_contents` desde `settings`.
4. Frontend — al inicializar, consumir el valor del endpoint de metadata en lugar de la constante local. Eliminar `MAX_PENDING_CONTENTS` de `constants.ts`.

**Fricción conocida:** `backend/tests/test_generation_service.py` importa `MAX_PENDING_CONTENTS` directamente del servicio. Tras el cambio hay que actualizar esa importación a `settings.max_pending_contents` o usar el valor numérico directamente en los fixtures.

---

## ~~12. Validación de categoría duplicada~~ ✅ Observación incorrecta

**Capa:** Backend  
**Verificado:** El route handler solo tiene la validación automática de enum de FastAPI (`category: ContentCategory` en el path — rechaza valores que no sean un `ContentCategory` válido con 422). La regla de negocio (¿es esta categoría válida para este tipo de entidad?) únicamente existe en `generation_service.py:30–33`. No hay duplicación real.

---

## 13. Jerarquía de excepciones plana

**Capa:** Backend  
**Archivo:** `backend/app/core/exceptions.py`  
**Impacto:** Muy bajo — el problema práctico original ya está resuelto; lo pendiente es arquitectura de conveniencia.

**Estado tras refactor de try-catch (2026-04-26):** Se eliminaron la mayoría de primitivos. Ahora cada categoría tiene su tipo explícito:

| Categoría | Excepciones |
|-----------|-------------|
| Infraestructura | `DatabaseError`, `VectorStoreError` |
| Regla de negocio | `DuplicateEntityNameError`, `DuplicateCollectionNameError`, `PendingLimitExceededError`, `InvalidCategoryError` |
| Validación de entrada | `UnsupportedFileTypeError`, `FileTooLargeError`, `MissingFilenameError`, `ContentNotAllowedError` |
| Estado RAG | `NoContextAvailableError`, `DocumentExtractionError` |

La jerarquía sigue siendo plana (todas heredan de `Exception`), pero los routes ya capturan cada tipo explícitamente y mapean al HTTP code correcto.

**Estado tras refactor completo (2026-04-26):** Todos los primitivos (`ValueError`, `RuntimeError`) eliminados como señales de dominio. Los dos remanentes identificados en la revisión posterior fueron resueltos en los ítems 14 y 15. El mapa de excepciones queda:

| Categoría | Excepciones |
|-----------|-------------|
| Infraestructura | `DatabaseError`, `VectorStoreError` |
| Regla de negocio | `DuplicateEntityNameError`, `DuplicateCollectionNameError`, `PendingLimitExceededError`, `InvalidCategoryError`, `ContentDiscardedError` |
| Validación de entrada | `UnsupportedFileTypeError`, `FileTooLargeError`, `MissingFilenameError`, `ContentNotAllowedError` |
| Estado RAG | `NoContextAvailableError`, `DocumentExtractionError`, `GeneratedContentBlockedError` |

**Lo que queda (opcional):** Añadir `DomainError` e `InfrastructureError` como bases intermedias permitiría un `exception_handler` global en `main.py`. Solo justificado si se añaden muchas más excepciones o se quiere limpiar el boilerplate de los routes.

---

## ~~14. `ValueError("discarded")` como señal de dominio~~ ✅ Resuelto

**Capa:** Backend  
**Solución aplicada:** Añadida `ContentDiscardedError` a `exceptions.py`. `content_management_service.edit_content` lanza `ContentDiscardedError()` en lugar de `ValueError("discarded")`. El route `entity_content.py` captura `except ContentDiscardedError as e` → 409 con `str(e)`, eliminando el mensaje hardcodeado en el route.

---

## ~~15. `RuntimeError` en `check_generated_output` conflado con errores de infraestructura~~ ✅ Resuelto

**Capa:** Backend  
**Solución aplicada:** Añadida `GeneratedContentBlockedError` a `exceptions.py`. `content_guard.check_generated_output` lanza `GeneratedContentBlockedError()` en lugar de `RuntimeError`. Ambos routes (`entity_content.py` y `rag_query.py`) capturan `except GeneratedContentBlockedError as e` → 422 antes del `except RuntimeError` → 503. Ahora el cliente puede distinguir entre contenido moderado (422) e infraestructura caída (503).

---

## 16. Función privada `_fetch_counts` importada en route

**Capa:** Backend  
**Archivo:** `backend/app/api/routes/collections.py:25`, `backend/app/services/collection_service.py`  
**Impacto:** Muy bajo — viola la convención de que el prefijo `_` indica uso interno del módulo.

`collections.py` importa `_fetch_counts` directamente del servicio para enriquecer la respuesta del endpoint `GET /{collection_id}`. La función existe porque `list_collections_service` la usa internamente, pero la misma lógica se necesita también en el GET de una colección individual.

**Solución sugerida:** Renombrar `_fetch_counts` a `fetch_counts` (sin guión), o crear una función `get_collection_with_counts_service(session, collection)` que encapsule el enriquecimiento y sea la única API pública del servicio para este caso.

---

---

## Gaps de Producción

Aspectos que deben resolverse antes de cualquier despliegue fuera de entorno local.

| # | Gap | Impacto |
|---|---|---|
| P1 | Sin autenticación/autorización (ver ítem 1) | Crítico |
| P2 | Sin rate limiting — un usuario puede saturar la cola del LLM | Alto |
| P3 | CORS configurado solo para `localhost` — requiere revisión antes de deploy | Alto |
| P4 | Sin detección de documentos duplicados — el vector store crece con contenido repetido | Medio |
| P5 | Sin health check granular — `/healthz` no verifica Qdrant ni el modelo LLM | Medio |
| P6 | Sin audit trail — no hay registro de quién modificó qué ni cuándo | Bajo |
| P7 | Sin operaciones bulk — no se puede eliminar múltiples colecciones o entidades a la vez | Bajo |
| P8 | Modelo LLM y embeddings hardcodeados — no hay forma de cambiarlos desde la UI | Bajo |

---

## Cobertura de Tests

### Backend — Tests faltantes

**`deletion_service.py`**
- Fallo de Qdrant durante el delete (post-commit): verificar que los vectores huérfanos se detectan y se loguean.
- Retry logic: confirmar que se reintenta el número correcto de veces y que el backoff funciona.

**`content_management_service.py`**
- `_discard_sibling_contents` en isolation: verificar que solo descarta contenidos de la misma categoría, no de otras.

**`entities_service.py` / `collection_service.py`**
- Soft-delete + nombre reservado: una entidad eliminada (soft) no puede recrearse con el mismo nombre. Caso documentado en `CLAUDE.md` pero sin test.

**`documents_service.py`**
- Ingestión con PDF malformado: verificar que el documento queda en `status=failed` y no bloquea otros.
- Timeout de Qdrant durante el background task: verificar manejo de error.

**`rag_pipeline.py`**
- Qdrant caído en tiempo de query: debe devolver error controlado, no 500 sin detalle.
- LLM timeout: verificar que el semáforo se libera correctamente aunque el request falle.

**`content_guard.py`**
- Tests directos de los patrones regex: inputs válidos, inválidos, y edge cases (strings vacíos, unicode).

### Frontend — Tests faltantes

**Páginas**
- Paginación: al eliminar el último ítem de una página, debe retroceder a la página anterior.
- Recuperación de error: si la API falla en el fetch inicial, debe mostrar el mensaje de error y ofrecer reintentar.
- Navegación a entidad eliminada: si la entidad no existe (404), redirigir con mensaje claro.

**`ContentCard.tsx`**
- Doble acción rápida: confirmar que la segunda acción no sobreescribe el estado de la primera.
- Rollback tras fallo de API: el estado debe volver exactamente al valor anterior.

**`MarkdownContent.tsx`**
- Sanitización: inputs con `<script>`, atributos `onerror`, y links con `javascript:` deben renderizarse sin ejecutar código.

**Hooks**
- `useGenerate`: cancelación en vuelo — al llamar a `abort()`, el estado no debe actualizarse tras la cancelación.
- `useCollectionDocumentsStatus`: verificar que el polling se detiene cuando todos los documentos salen del estado `processing`.

---

*Generado el 2026-04-25. Actualizado el 2026-04-26. Ver historial de correcciones aplicadas en los commits del branch `main`.*