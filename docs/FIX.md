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
| 5 | Extracción de documentos sin timeout | Backend | ✅ Resuelto | — |
| 6 | Cascading delete no atómico | Backend | 🟢 Cubierto | Observación — retry existente suficiente; revisar si `cascade_delete_collection` se vuelve async |
| 7 | Background task sin recuperación | Backend | 🔴 Pendiente | Implementar — endpoint `POST /documents/{id}/retry` + campo `processing_error` |
| 8 | Race condition en optimistic updates | Frontend | ✅ Resuelto | — |
| 9 | `EntityDetailPage` excede SRP (~720 líneas) | Frontend | ✅ Resuelto | — |
| 10 | Paginación duplicada en frontend | Frontend | ✅ Resuelto | — |
| 11 | `MAX_PENDING_CONTENTS` hardcodeado | Backend + Frontend | ✅ Resuelto | — |
| 12 | Validación de categoría duplicada | Backend | ✅ Incorrecto | — (no había duplicación real) |
| 13 | Jerarquía de excepciones plana | Backend | 🟢 Cubierto | Observación — todos los primitivos eliminados; bases `DomainError`/`InfrastructureError` solo si se necesita middleware global |
| 14 | `ValueError("discarded")` como señal de dominio | Backend | ✅ Resuelto | — |
| 15 | `RuntimeError` en `check_generated_output` conflado con infra | Backend | ✅ Resuelto | — |
| 16 | Función privada `_fetch_counts` importada en route | Backend | ✅ Resuelto | — |
| 17 | Guardrails sin normalización Unicode ni tests adversariales | Backend | 🔴 Pendiente | Implementar — lower() + NFKD antes de regex + batería adversarial |
| 18 | Páginas excluidas del coverage de tests (`vitest.config.ts`) | Frontend | 🟡 Pendiente | Añadir `src/pages/**` al `include` de coverage |
| 19 | Sin auditoría de contenido moderado | Backend | 🟡 Pendiente | Tabla `moderation_log` o campo en `EntityContent` + migración |
| 20 | Polling de 3 s en `useCollectionDocumentsStatus` | Frontend | 🟡 Pendiente | Candidato a SSE/WebSocket — no urgente con volumen actual |

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

## ~~5. Extracción de documentos sin timeout~~ ✅ Resuelto

**Capa:** Backend  
**Solución aplicada:** `extract_text()` se ejecuta ahora en el executor de asyncio (`loop.run_in_executor(None, ...)`) envuelto en `asyncio.wait_for(..., timeout=_EXTRACTION_TIMEOUT_SECONDS)` (30 s). Un `asyncio.TimeoutError` se captura y convierte en `DocumentExtractionError`, que el route ya mapeaba a 422. La constante `_EXTRACTION_TIMEOUT_SECONDS` es parcheable en tests; se añadió DOC-13 que monkeypatchea el timeout a 0.01 s y verifica el 422.

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

## ~~9. `EntityDetailPage.tsx` excede responsabilidad única~~ ✅ Resuelto

**Capa:** Frontend  
**Solución aplicada:** Extraídos dos componentes de `EntityDetailPage.tsx` (~720 → ~280 líneas):
- `components/EntityEditForm.tsx` — Modal de edición autocontenido; internaliza `editForm` y `saving`; props: `show`, `entity`, `collectionId`, `entityId`, `onClose`, `onSaved`, `onError`.
- `components/EntityContentsPanel.tsx` — Sección completa de contenidos generados (tabs, filtros, lista, paginación); internaliza `useEntityContents`, estado de filtros y paginación, `handleOptimisticUpdate`, `handleContentAction`; comunica `pendingInCategoryCount` al padre via `onPendingCountChange`. Usa `usePagination` (ítem 10).

---

## ~~10. Lógica de paginación duplicada en frontend~~ ✅ Resuelto

**Capa:** Frontend  
**Solución aplicada:** Creado `hooks/usePagination(page, totalPages)` que centraliza el algoritmo de páginas con elipsis (antes duplicado 4 veces: `EntityDetailPage`, `CollectionsPage`, `CollectionDetailPage` DocumentsTab y EntitiesTab). Cada página sigue gestionando su propio estado de `page` y `totalPages` (local o URL params), y delega solo el cálculo del array de items al hook.

---

## ~~11. `MAX_PENDING_CONTENTS` hardcodeado en frontend y backend~~ ✅ Resuelto

**Capa:** Backend + Frontend  
**Solución aplicada:** `max_pending_contents: int = 5` añadido a `Settings` en `config.py` (configurable vía `MAX_PENDING_CONTENTS` en `.env`). `generation_service.py` elimina la constante de módulo y lee `settings.max_pending_contents`. Nuevo endpoint `GET /limits` en `metadata.py` expone el valor. `EntityDetailPage.tsx` llama `getLimits()` en el mismo `useEffect` que `getEntityCategories()`, almacena el resultado en estado local (fallback 5 si el backend no responde) y lo usa en la lógica del formulario. `MAX_PENDING_CONTENTS` eliminado de `constants.ts` y su test asociado.

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

## ~~16. Función privada `_fetch_counts` importada en route~~ ✅ Resuelto

**Capa:** Backend  
**Solución aplicada:** Añadida `get_collection_with_counts_service(session, collection)` a `collection_service.py`. Encapsula la llamada a `_fetch_counts` y devuelve el dict enriquecido con `document_count` y `entity_count`. El route `GET /{collection_id}` ahora importa y llama esta función pública; `_fetch_counts` permanece privada al módulo.

---

## 17. Guardrails sin normalización Unicode ni tests adversariales

**Capa:** Backend  
**Archivo:** `backend/app/domain/content_guard.py`  
**Impacto:** Alto — los cinco patrones regex usan `re.IGNORECASE` pero no normalizan el texto. Variantes triviales (p0rn, s3x0, espacios entre caracteres, homoglifos Unicode) eluden todos los guardrails sin esfuerzo.

Los patrones actuales en `_BLOCKED_PATTERNS` aplican `re.I` pero reciben el texto sin preprocesar. Un atacante puede sortear cualquier patrón con sustituciones básicas de caracteres o con Unicode de ancho completo.

**Solución sugerida:** Antes de iterar los patrones en `_check_text`, aplicar:
```python
import unicodedata
text = unicodedata.normalize("NFKD", text).lower()
```
Añadir una batería de tests adversariales en `tests/test_content_guard.py`: inputs con números intercalados (s3x), caracteres Unicode similares (ｐｏｒｎ), espacios entremedios, y strings vacíos.

---

## 18. Páginas excluidas del coverage de tests (`vitest.config.ts`)

**Capa:** Frontend  
**Archivo:** `frontend/vitest.config.ts`  
**Impacto:** Medio — `coverage.include` cubre `src/utils/**`, `src/hooks/**` y `src/components/**`, pero excluye explícitamente `src/pages/**`. Los informes de cobertura muestran 0% para páginas aunque los tests de `src/test/` sí se ejecuten, generando una falsa sensación de seguridad.

La lógica de UX más compleja (filtros de contenidos, paginación, polling de documentos, gating de generación) vive en las páginas y no aparece en los métricas de coverage.

**Solución sugerida:** Añadir `"src/pages/**"` al array `include` en `vitest.config.ts`. Los tests ya existentes (`EntityDetailPage.test.tsx`, etc.) empezarán a contribuir al informe sin cambios adicionales. Complementar con tests de happy path donde la cobertura sea baja.

---

## 19. Sin auditoría de contenido moderado

**Capa:** Backend  
**Impacto:** Medio — cuando un guardrail rechaza una query o un documento, no queda ningún registro persistente. Es imposible revisar falsos positivos, analizar patrones de abuso ni demostrar cumplimiento.

`check_user_input`, `check_document_content` y `check_generated_output` lanzan excepciones que el route convierte en 422/503, pero no escriben nada en base de datos.

**Solución sugerida:** Añadir tabla `moderation_log` (id, layer `[input|document|output]`, snippet (primeros 200 chars), pattern_matched, created_at) con migración Alembic. Alternativamente, añadir campo `moderation_reason: str | None` a `EntityContent` para el caso de output bloqueado. La versión mínima (solo logging a fichero estructurado) puede ser suficiente en primera iteración.

---

## 20. Polling de 3 s en `useCollectionDocumentsStatus`

**Capa:** Frontend  
**Archivo:** `frontend/src/hooks/useCollectionDocumentsStatus.ts`  
**Impacto:** Bajo (con el volumen actual) — genera una request al backend cada 3 s por pestaña activa mientras existan documentos en estado `processing`. Escala mal con muchos usuarios o colecciones grandes.

El hook se auto-cancela cuando todos los documentos salen de `processing`, lo que mitiga el problema en condiciones normales. El coste real es bajo mientras el proyecto sea single-user local.

**Solución sugerida:** Reemplazar el polling con SSE (Server-Sent Events) o WebSocket para notificaciones en tiempo real desde el backend. No urgente — abordar antes de cualquier despliegue multi-usuario.

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
| P9 | Sin auditoría de contenido moderado — rechazos de guardrail no persisten (ver ítem 19) | Bajo |

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

*Generado el 2026-04-25. Actualizado el 2026-04-28. Ver historial de correcciones aplicadas en los commits del branch `main`.*