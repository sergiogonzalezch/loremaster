# Problemas pendientes de corrección

Lista de tech debt identificado y aún no corregido. Ordenado por impacto estimado.

---

## Tabla de estado rápido

| # | Descripción | Capa | Estado | Acción |
|---|-------------|------|--------|--------|
| 1 | Sin autenticación | Backend | ✅ Resuelto | — |
| 2 | Ingest de documentos síncrono | Backend | ✅ Resuelto | — |
| 3 | Sin optimistic updates en contenidos | Frontend | ✅ Resuelto | — |
| 4 | Token counter aproximado | Backend + Frontend | ✅ Resuelto | — |
| 5 | Extracción de documentos sin timeout | Backend | ✅ Resuelto | — |
| 6 | Cascading delete no atómico / `ImageRecord` excluido | Backend | ✅ Resuelto | — |
| 7 | Background task sin recuperación | Backend | ✅ Resuelto | — |
| 8 | Race condition en optimistic updates | Frontend | ✅ Resuelto | — |
| 9 | `EntityDetailPage` excede SRP (~720 líneas) | Frontend | ✅ Resuelto | — |
| 10 | Paginación duplicada en frontend | Frontend | ✅ Resuelto | — |
| 11 | `MAX_PENDING_CONTENTS` hardcodeado | Backend + Frontend | ✅ Resuelto | — |
| 12 | Validación de categoría duplicada | Backend | ✅ Incorrecto | — (no había duplicación real) |
| 13 | Jerarquía de excepciones plana | Backend | 🟢 Cubierto | Observación — todos los primitivos eliminados; bases `DomainError`/`InfrastructureError` solo si se necesita middleware global |
| 14 | `ValueError("discarded")` como señal de dominio | Backend | ✅ Resuelto | — |
| 15 | `RuntimeError` en `check_generated_output` conflado con infra | Backend | ✅ Resuelto | — |
| 16 | Función privada `_fetch_counts` importada en route | Backend | ✅ Resuelto | — |
| 17 | Guardrails sin normalización Unicode ni tests adversariales | Backend | ✅ Resuelto | — |
| 18 | Páginas excluidas del coverage de tests (`vitest.config.ts`) | Frontend | ✅ Resuelto | — |
| 19 | Sin auditoría de contenido moderado | Backend | ✅ Resuelto | — |
| 20 | Polling de 3 s en `useCollectionDocumentsStatus` | Frontend | 🟡 Pendiente | Candidato a SSE/WebSocket — no urgente con volumen actual |
| 21 | `ImageRecord` excluido del cascade soft-delete | Backend | ✅ Resuelto | — |
| 22 | Guardrail semánticamente incorrecto en image service | Backend | ✅ Resuelto | — |
| 23 | `NoContextAvailableError` reutilizada para regla de negocio | Backend | ✅ Resuelto | — |
| 24 | Flag `truncated` incorrecto en estrategia `entity_only` | Backend | ✅ Resuelto | — |
| 25 | `image_url` `str` en response schema pero `Optional` en modelo | Backend | ✅ Resuelto | — |
| 26 | Info leak en handlers catch-all de `image_generation.py` | Backend | ✅ Resuelto | — |
| 27 | `UpdateContentRequest` sin `max_length` | Backend | ✅ Resuelto | — |
| 28 | Cache JWKS sin lock en `auth_clerk.py` | Backend | ✅ Resuelto | — |
| 29 | Log "Auto-discarded" emitido antes de commit | Backend | 🟢 Cubierto | Impacto muy bajo; confunde en caso de rollback |
| 30 | `delete_image_service` no valida `collection_id` directamente | Backend | 🟢 Cubierto | Protegido indirectamente vía `get_entity_or_404` |
| 31 | Paginación hardcodeada en `GET /admin/users` | Backend | ✅ Resuelto | — |
| 32 | `get_admin_user` no verifica `is_deleted` | Backend | ✅ Resuelto | — |
| 33 | `User.email` sin `unique=True` en modelo SQLModel | Backend | ✅ Resuelto | — |
| 34 | FK constraint faltante en migración `add_owner_id_to_collections` | Backend | 🟢 Cubierto | Sin FK en SQL; integridad referencial solo a nivel de aplicación |
| 35 | Constraint `(name, owner_id)` no protege colecciones con `owner_id=NULL` | Backend | 🟢 Cubierto | SQL `NULL != NULL` en UNIQUE; solo afecta datos migrados sin backfill |
| 36 | `get_collection_or_404_public_or_owned` bypassa Clerk tokens | Backend | 🟢 Cubierto | Llama `verify_token` directo; Clerk solo activo en producción con config explícita |

**Leyenda:** 🔴 Pendiente urgente · 🟡 Pendiente no urgente · 🟢 Cubierto (mitigado, sin acción inmediata) · ✅ Cerrado

---

## ~~1. Sin autenticación~~ ✅ Resuelto

**Capa:** Backend  
**Solución aplicada:** Autenticación JWT implementada completamente:

- `app/api/routes/auth.py` — endpoints `POST /auth/register` y `POST /auth/login`. Registro crea usuario + devuelve token directamente (login implícito). Login valida credenciales y devuelve token. Ambos responden con `{ access_token, token_type: "bearer" }`.
- `app/core/auth.py` — `create_access_token` (HS256, `python-jose`), `verify_token`, `hash_password` y `verify_password`. Hash con `bcrypt` directo (sin `passlib`, incompatible con `bcrypt >= 4.x`).
- `app/core/auth_deps.py` — dependencia `get_current_user` que extrae y valida el Bearer token. Inyectada en todos los routers protegidos.
- En producción (`ENVIRONMENT=production`) la dependencia se reemplaza por `decode_clerk_token` (`auth_clerk.py`) que valida tokens RS256 via JWKS de Clerk.
- Variables de entorno: `SECRET_KEY`, `ALGORITHM` (HS256), `ACCESS_TOKEN_EXPIRE_MINUTES` (1440 = 24 h), `CLERK_JWKS_URL`, `CLERK_AUDIENCE`.
- Frontend: `LoginPage.tsx` con tabs login/registro, `ProtectedRoute.tsx` como guard de rutas, utilidades `getToken`/`setToken`/`removeToken`/`isAuthenticated` en `utils/token.ts`, y cabecera `Authorization: Bearer <token>` en `apiFetch`.

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

## ~~6. Cascading delete — `ImageRecord` excluido del cascade~~ ✅ Resuelto

**Capa:** Backend  
**Solución aplicada:** Añadidos `_cascade_delete_images_by_entity(session, entity_id)` y `_cascade_delete_images_by_collection(session, collection_id)` como helpers privados en `deletion_service.py`. `cascade_delete_entity` los llama antes de hacer soft-delete de la entidad. `cascade_delete_collection` llama a `_cascade_delete_images_by_collection` tras el paso de orphan contents para capturar cualquier imagen huérfana restante. Ambos helpers reutilizan `soft_delete` de `core/common.py`.

**Nota sobre OPTION_B:** La eliminación de archivos físicos desde `MEDIA_ROOT` deberá añadirse en `_cascade_delete_images_by_entity` cuando se implemente el backend real de imágenes.

---

## ~~7. Background task de ingestión sin recuperación~~ ✅ Resuelto

**Capa:** Backend  
**Solución aplicada:**

- Añadidos dos campos a `Document` (y migración Alembic `c7e4d1f82a3b`):
  - `processing_error: Optional[str]` — registra el mensaje de error cuando el background task falla; se expone en `DocumentResponse`.
  - `raw_text: Optional[str]` — almacena el texto extraído al momento del ingest inicial para permitir el retry sin re-subir el archivo.
- `process_ingest_background` escribe el error en `processing_error` al fallar y lo limpia al completar con éxito.
- `ingest_document_service` persiste `raw_text=content` al crear el documento.
- Nuevo `retry_document_service(session, document)` en `documents_service.py`: verifica que el documento esté en `status=failed` y tenga `raw_text`, resetea a `processing`, limpia `processing_error`, y devuelve `(document, raw_text)` para el background task. Lanza `DocumentNotRetryableError` si las condiciones no se cumplen.
- Nuevo endpoint `POST /collections/{collection_id}/documents/{doc_id}/retry` (202) que delega en `retry_document_service` y lanza `process_ingest_background` como `BackgroundTask`. Devuelve 409 si el documento no es retriable.

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

## ~~17. Guardrails sin normalización Unicode ni tests adversariales~~ ✅ Resuelto

**Capa:** Backend  
**Solución aplicada:** Añadida función `_normalize(text)` en `content_guard.py` que aplica NFKD + eliminación de combining marks (categoría Unicode `Mn`) + `.lower()`. Esto colapsa caracteres de ancho completo (`ｐｏｒｎ` → `porn`), elimina diacríticos evasivos (`pórn` → `porn`, `séxo` → `sexo`) y normaliza capitalización. `_check_text` opera ahora sobre el texto normalizado en vez del input crudo.

Creado `tests/test_content_guard.py` con 32 tests: baseline (inputs limpios y palabras clave directas), full-width Unicode, diacríticos con combining marks, mayúsculas mixtas, routing correcto de excepciones (`ContentNotAllowedError` vs `GeneratedContentBlockedError`), y edge cases (strings vacíos, palabras embebidas en oración).

---

## ~~18. Páginas excluidas del coverage de tests (`vitest.config.ts`)~~ ✅ Resuelto

**Capa:** Frontend  
**Solución aplicada:** `"src/pages/**"` añadido a `coverage.include` y eliminado de `coverage.exclude` en `vitest.config.ts`. Los tests existentes de páginas (`CollectionsPage.test.tsx`, `EntityDetailPage.test.tsx`, `GeneratePage.test.tsx`) ahora contribuyen al informe de cobertura sin cambios adicionales.

---

## ~~19. Sin auditoría de contenido moderado~~ ✅ Resuelto

**Capa:** Backend  
**Solución aplicada:**

- `ContentNotAllowedError` y `GeneratedContentBlockedError` exponen ahora un atributo `snippet: str` (primeros 200 chars del texto bloqueado), poblado en `content_guard.py` al construir la excepción.
- Nueva tabla `moderation_log` (id, layer, snippet, created_at) con migración Alembic `b1c2d3e4f5a6`. `layer` toma los valores `"input"` (query/prompt del usuario), `"document"` (texto extraído del documento) u `"output"` (respuesta del LLM).
- `app/services/moderation_service.py` expone `log_moderation_event(session, layer, snippet)` que persiste la entrada; en caso de fallo de BD solo emite `WARNING` para no enmascarar el error original al cliente.
- Los tres routes que capturan excepciones de moderación llaman a `log_moderation_event` antes de relanzar `HTTPException`: `documents.py` (layer=document), `entity_content.py` (layer=input y layer=output), `rag_query.py` (layer=input y layer=output, con `Session` añadida como dependencia).

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
| P1 | ~~Sin autenticación/autorización (ver ítem 1)~~ | ✅ Resuelto |
| P2 | Sin rate limiting — un usuario puede saturar la cola del LLM | Alto |
| P3 | ~~CORS configurado solo para `localhost` — requiere revisión antes de deploy~~ | ✅ Resuelto |
| P4 | Sin detección de documentos duplicados — el vector store crece con contenido repetido | Medio |
| P5 | Sin health check granular — `/health` no verifica Qdrant ni el modelo LLM | Medio |
| P6 | Sin audit trail de usuario — `updated_at`/`deleted_at` existen, pero no `updated_by` | Bajo |
| P7 | Sin operaciones bulk — no se puede eliminar múltiples colecciones o entidades a la vez | Bajo |
| P8 | Modelo LLM y embeddings no cambiables en runtime desde la UI | Bajo |
| P9 | ~~Sin auditoría de contenido moderado — rechazos de guardrail no persisten (ver ítem 19)~~ | ✅ Resuelto |
| P10 | `/media/**` sirve imágenes sin autenticación — cualquier URL es accesible sin token | Medio |

**Notas sobre gaps cerrados:**

### P10 — `/media/**` sin autenticación

**Capa:** Backend  
**Archivo:** `backend/app/main.py` líneas 67-69  
**Impacto:** Medio — cualquier URL de imagen es accesible sin token JWT desde un navegador o cliente externo.

`StaticFiles` se monta como sub-aplicación de ASGI. Al ser un sub-app independiente, **no hereda el `CORSMiddleware` ni ninguna otra dependencia** del `app` padre. Esto significa que el middleware de autenticación nunca se ejecuta sobre `/media/**`.

La protección actual es únicamente por oscuridad: la ruta incluye cuatro UUIDs anidados (`{collection_id}/{entity_id}/{generation_id}/{image_id}.png`), lo que hace estadísticamente imposible adivinar una URL. No obstante, quien posea un enlace (p. ej. via historial del navegador, logs de red, o un usuario que comparte una URL) puede acceder a la imagen sin autenticar.

**Solución sugerida:** Reemplazar el mount estático por un endpoint autenticado:

```python
@router.get("/images/{image_id}/file")
def serve_image(image_id: str, _: dict = Depends(get_current_user), session: Session = Depends(get_session)):
    record = session.get(ImageRecord, image_id)
    if not record or record.is_deleted:
        raise HTTPException(404)
    return FileResponse(Path(settings.media_root) / record.storage_path)
```

No urgente mientras el proyecto sea de uso interno local. Abordar antes de cualquier despliegue donde las imágenes puedan ser datos sensibles.

---

- **P1:** Auth JWT implementado (ver ítem 1). Todos los endpoints protegidos excepto `/health` y `/`.
- **P3:** `main.py` lee `settings.allowed_origins` dinámicamente desde `config.py`. Configurable vía variable de entorno `ALLOWED_ORIGINS` en `.env` — no requiere cambio de código para producción, solo configurar los dominios del deploy.
- **P9:** Tabla `moderation_log` implementada (ver ítem 19). Registra snippet + layer para cada rechazo de guardrail.

---

## Cobertura de Tests

### Backend — Tests faltantes

**`deletion_service.py`**
- ~~Fallo de Qdrant durante el delete (post-commit): verificar que los vectores huérfanos se detectan y se loguean.~~ ✅ Cubierto en `tests/test_deletion_service.py::test_delete_vectors_with_retry_logs_orphans_on_final_failure`.
- ~~Retry logic: confirmar que se reintenta el número correcto de veces y que el backoff funciona.~~ ✅ Cubierto en `tests/test_deletion_service.py::test_delete_vectors_with_retry_retries_until_success`.
- ~~**Nuevo** (ítem 21): cascade entity delete no limpia `ImageRecord` — añadir test que verifique que al eliminar una entidad sus `generated_images` quedan soft-deleted.~~ ✅ Cubierto en `tests/test_entities.py::test_delete_entity_cascades_generated_images`.

**`image_generation_service.py`**
- ~~Guardrail semánticamente incorrecto (ítem 22): test que verifique que contenido LLM bloqueado lanza la excepción correcta.~~ ✅ Cubierto en `tests/test_image_generation.py::test_img_09_blocked_generated_content_returns_422`.
- ~~`NoContextAvailableError` para content no confirmado (ítem 23): test que verifique que content en estado `pending` retorna 422 con mensaje de negocio apropiado (ya cubierto en `test_img_05`, pero el tipo de excepción interno no se valida).~~ ✅ Cubierto en `tests/test_image_generation.py::test_img_08_pending_content_error_has_business_message`.

**`content_management_service.py`**
- ~~`_discard_sibling_contents` en isolation: verificar que solo descarta contenidos de la misma categoría, no de otras.~~ ✅ Cubierto en `tests/test_content_management_service.py::test_discard_sibling_contents_only_affects_same_category`.

**`entities_service.py` / `collection_service.py`**
- ~~Soft-delete + nombre reservado: una entidad eliminada (soft) no puede recrearse con el mismo nombre. Caso documentado en `CLAUDE.md` pero sin test.~~ ✅ Cubierto en `tests/test_entities.py::test_deleted_entity_name_cannot_be_reused`.

**`documents_service.py`**
- ~~Ingestión con PDF malformado: verificar que el documento queda en `status=failed` y no bloquea otros.~~ ✅ Cubierto en `tests/test_documents.py::test_ingest_malformed_pdf_marks_422_and_allows_following_ingest` (no bloquea ingestas posteriores).
- ~~Timeout de Qdrant durante el background task: verificar manejo de error.~~ ✅ Cubierto en `tests/test_documents.py::test_ingest_qdrant_failure_sets_processing_error` (marca `failed` y persiste `processing_error`).

**`rag_pipeline.py`**
- Qdrant caído en tiempo de query: debe devolver error controlado, no 500 sin detalle.
- ~~LLM timeout: verificar que el semáforo se libera correctamente aunque el request falle.~~ ✅ Cubierto en `tests/test_rag_query.py::test_rag_query_llm_failure_releases_semaphore`.

**~~`content_guard.py`~~** ✅ Cubierto  
- ~~Tests directos de los patrones regex: inputs válidos, inválidos, y edge cases (strings vacíos, unicode).~~ — `tests/test_content_guard.py` cubre 32 casos: baseline, full-width Unicode, diacríticos, mayúsculas mixtas, routing de excepciones y edge cases.

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

## ~~21. `ImageRecord` excluido del cascade soft-delete~~ ✅ Resuelto

Ver solución aplicada en **ítem 6**.

---

## ~~22. Guardrail semánticamente incorrecto en image generation service~~ ✅ Resuelto

**Capa:** Backend  
**Solución aplicada:** `check_user_input(content.content[:500])` reemplazado por `check_generated_output(content.content[:500])` en `image_generation_service.py`. Import de `check_user_input` eliminado. Route actualizado: `except GeneratedContentBlockedError` → 422 (era 403), y eliminado el bloque muerto `except NoContextAvailableError` junto a su import.

---

## ~~23. `NoContextAvailableError` reutilizada para regla de negocio de imagen~~ ✅ Resuelto

**Capa:** Backend  
**Solución aplicada:** Añadida `ContentNotConfirmedError` a `exceptions.py`. `image_generation_service.py` lanza `ContentNotConfirmedError()` en lugar de `NoContextAvailableError`. Route captura `except ContentNotConfirmedError as e` → 422 con `str(e)`.

---

## ~~24. Flag `truncated` incorrecto en estrategia `entity_only`~~ ✅ Resuelto

**Capa:** Backend  
**Solución aplicada:** Extraída `narrative_source_text = confirmed_content if source.startswith("content") else entity_description` antes de la rama de truncado en `prompt_builder.py`. `truncated` ahora compara tokens de `narrative_source_text` en vez de `confirmed_content` directamente, corrigiendo el falso positivo en estrategia `entity_only`.

---

## ~~25. `image_url` `str` en response schema pero `Optional[str]` en modelo DB~~ ✅ Resuelto

**Capa:** Backend  
**Solución aplicada:** `GenerateImageResponse.image_url` cambiado de `str` a `Optional[str] = None` en `models/image_generation.py`. Ahora el schema Pydantic es consistente con `ImageRecord.image_url: Optional[str] = None` y no lanzará `ValidationError` en OPTION_B cuando la URL aún no esté disponible.

---

## ~~26. Info leak en handlers catch-all de `image_generation.py`~~ ✅ Resuelto

**Capa:** Backend  
**Solución aplicada:** Añadido `logger = logging.getLogger(__name__)` en `app/api/routes/image_generation.py`. Los cinco bloques `except Exception as e: raise HTTPException(status_code=500, detail=str(e))` reemplazados por `except Exception: logger.exception("<nombre_handler>"); raise HTTPException(status_code=500, detail="Error interno del servidor.")`. El error completo (con traza) queda en los logs del servidor; el cliente solo recibe el mensaje genérico.

---

## ~~27. `UpdateContentRequest` sin `max_length`~~ ✅ Resuelto

**Capa:** Backend  
**Solución aplicada:** `content: str = Field(..., min_length=1, max_length=10000)` en `app/models/entity_content.py`. El schema Pydantic ahora rechaza payloads mayores de 10 000 caracteres con 422 antes de llegar a la BD, alineando la validación con la columna `EntityContent.content`.

---

## ~~28. Cache JWKS sin lock en `auth_clerk.py`~~ ✅ Resuelto

**Capa:** Backend  
**Solución aplicada:** Añadido `_jwks_lock = threading.Lock()` en `app/api/routes/auth_clerk.py`. `get_jwks()` ahora envuelve la comprobación y el refresco del cache dentro de `with _jwks_lock:`, garantizando que solo un thread ejecuta la llamada HTTP a Clerk cuando el cache ha expirado. El `return _jwks_cache` se movió dentro del bloque `with` para evitar la lectura fuera del lock.

---

## 29. Log "Auto-discarded" emitido antes de commit

**Capa:** Backend  
**Archivo:** `backend/app/services/content_management_service.py` — función `confirm_content`  
**Impacto:** Muy bajo — el log puede aparecer en los registros aunque el commit posterior falle, generando entradas misleading.  
**Clasificación:** Confirmado, impacto muy bajo.

`logger.info("Auto-discarded %d sibling...")` se emite después de `session.flush()` pero antes de `session.commit()`. Si el commit falla (p. ej. fallo de BD en el momento del write), el log queda registrado pero la acción no ocurrió.

**Solución sugerida:** Mover el log al bloque `after_commit` o simplemente colocarlo después del `session.commit()`.

---

## 30. `delete_image_service` no valida `collection_id` directamente

**Capa:** Backend  
**Archivo:** `backend/app/services/image_generation_service.py` — función `delete_image_service`  
**Impacto:** Muy bajo — la validación se realiza indirectamente.  
**Clasificación:** Parcialmente mitigado.

`delete_image_service(session, entity_id, generation_id, image_id)` no recibe ni valida `collection_id`. Sin embargo, el route llama antes a `get_entity_or_404(session, collection_id, entity_id)`, que verifica que la entidad pertenece a la colección, haciendo imposible acceder a imágenes de otra colección en el flujo normal.

El riesgo real se materializa solo si se llama al servicio directamente (e.g., desde tests o futuras integraciones) sin pasar por el route. No requiere acción inmediata, pero documentar la invariante mejoraría la mantenibilidad.

---

*Generado el 2026-04-25. Actualizado el 2026-04-28 (ítems 17, 18). 
Actualizado el 2026-04-30 (ítems 6 revisado, 21-25 nuevos — análisis del módulo image generation). 
Actualizado el 2026-04-30 (ítems 22-25 resueltos — correcciones en image generation service, route y models). 
Actualizado el 2026-04-30 (ítems 6 y 21 resueltos — cascade soft-delete de ImageRecord en deletion_service.py). 
Actualizado el 2026-04-30 (ítem 7 resuelto — retry endpoint + processing_error + raw_text en documents). 
Actualizado el 2026-04-30 (ítem 19 resuelto — tabla moderation_log + log_moderation_event en los tres routes de moderación). 
Actualizado el 2026-05-01 (cobertura de tests backend en deletion_service, content_management_service e image_generation/tests de cascade). 
Actualizado el 2026-05-06 (ítem 1 resuelto — auth JWT implementado; gaps P1 y P9 cerrados; ítems 26-30 añadidos — análisis bug-search completo). 
Actualizado el 2026-05-06 (ítems 26-28 resueltos — info leak, max_length, JWKS lock). 
Actualizado el 2026-05-06 (gap P3 cerrado — CORS configurable vía ALLOWED_ORIGINS env var; revisión completa del estado de gaps P2–P8). Actualizado el 2026-05-06 (gap P10 añadido — `/media/**` sin autenticación). Ver historial de correcciones aplicadas en los commits del branch `main`.
Actualizado el 2026-05-07 (ítems 31-36 añadidos — revisión del commit `b704c24` Users refactor first stage).*

---

## ~~31. Paginación hardcodeada en `GET /admin/users`~~ ✅ Resuelto

**Capa:** Backend  
**Archivo:** `backend/app/api/routes/admin.py:21`  
**Impacto:** Alto funcional — los query params `?page=X&page_size=Y` son ignorados silenciosamente.  
**Clasificación:** Error no resuelto.

El parámetro de paginación se declara con una lambda que no acepta argumentos:

```python
pagination: Annotated[dict, Depends(lambda: {"page": 1, "page_size": 20})],
```

Siempre devuelve los valores por defecto. La paginación del endpoint admin es funcionalidad rota desde el commit inicial.

**Solución sugerida:** Usar `PaginationParams` como el resto de routes:

```python
pagination: Annotated[PaginationParams, Depends()],
```

---

## ~~32. `get_admin_user` no verifica `is_deleted`~~ ✅ Resuelto

**Capa:** Backend  
**Archivo:** `backend/app/core/auth_deps.py:30`  
**Impacto:** Bajo-Medio — un admin soft-deleted con token JWT aún válido puede ejecutar operaciones de administración.  
**Clasificación:** Error no resuelto.

```python
if not user or not user.is_admin:   # falta: or user.is_deleted
    raise HTTPException(status_code=403, detail="Acceso denegado.")
```

**Solución sugerida:**

```python
if not user or user.is_deleted or not user.is_admin:
    raise HTTPException(status_code=403, detail="Acceso denegado.")
```

---

## ~~33. `User.email` sin `unique=True` en el modelo SQLModel~~ ✅ Resuelto

**Capa:** Backend  
**Archivos:** `backend/app/models/users.py:12`, `backend/alembic/versions/add_user_profile_fields.py:27`  
**Impacto:** Bajo en runtime, Medio en mantenimiento — riesgo de drift entre modelo y schema de DB.  
**Clasificación:** Error no resuelto.

La migración crea el índice como único (`unique=True`), pero el campo del modelo no:

```python
# models/users.py
email: Optional[str] = SQLField(default=None, max_length=255)  # falta unique=True

# migración — crea índice único
batch_op.create_index("ix_users_email", ["email"], unique=True)
```

`alembic revision --autogenerate` detectará el índice único como ausente en el modelo y generará una migration que lo elimina.

**Solución sugerida:**

```python
email: Optional[str] = SQLField(default=None, max_length=255, unique=True)
```

---

## 34. FK constraint faltante en migración `add_owner_id_to_collections`

**Capa:** Backend  
**Archivo:** `backend/alembic/versions/add_owner_id_to_collections.py:22`  
**Impacto:** Bajo en SQLite (FK no enforzados por defecto), Medio en PostgreSQL (sin integridad referencial a nivel DB).  
**Clasificación:** Parcialmente mitigado.

La migración añade la columna sin FK:

```python
batch_op.add_column(sa.Column("owner_id", sa.String(36), nullable=True))
# falta: sa.ForeignKey("users.id")
```

El modelo SQLAlchemy sí declara `ForeignKey("users.id")`, pero ese metadato no se propaga a una migration que usa `add_column` explícito.

**Mitigación:** La lógica de ownership en `get_collection_or_404_owned` y `create_collection_service` enforza la relación a nivel de aplicación. En entorno SQLite de desarrollo, los FK no se enforzan por defecto.

---

## 35. Constraint `(name, owner_id)` no protege colecciones con `owner_id=NULL`

**Capa:** Backend  
**Archivo:** `backend/alembic/versions/add_owner_id_to_collections.py:26`  
**Impacto:** Bajo — solo afecta datos pre-refactor sin backfill de `owner_id`.  
**Clasificación:** Parcialmente mitigado.

En SQL, `NULL != NULL` en constraints UNIQUE. Dos filas con el mismo `name` y `owner_id=NULL` no violan el constraint. Las colecciones antiguas sin owner asignado quedan sin protección de nombre.

**Mitigación:** Todas las colecciones creadas tras el refactor reciben `owner_id` del usuario autenticado. El camino `NULL` es inalcanzable desde las rutas actuales. El riesgo se limita a instancias pre-refactor hasta que se ejecute un backfill (documentado en `USERS-PROFILE.md`, pendiente).

---

## 36. `get_collection_or_404_public_or_owned` bypassa Clerk tokens en producción

**Capa:** Backend  
**Archivo:** `backend/app/core/deps.py:47`  
**Impacto:** Medio — usuarios autenticados con Clerk en producción reciben 403 al acceder a sus propias colecciones privadas.  
**Clasificación:** Parcialmente mitigado.

La dependencia llama `verify_token()` directamente (JWT local HS256) en vez de reutilizar `get_current_user`, que en producción enruta a `decode_clerk_token` (RS256 vía JWKS):

```python
if credentials:
    payload = verify_token(credentials.credentials)  # solo JWT local — falla con Clerk
    if collection.owner_id == payload.get("sub"):
        return collection
```

**Mitigación:** Clerk solo se activa con `settings.environment == "production"`. En desarrollo, el entorno actual, la dependencia funciona correctamente.

**Solución sugerida:** Añadir `get_optional_current_user` a `auth_deps.py` que retorne `None` en lugar de lanzar 401 cuando no hay credenciales, y usarlo en esta dependencia en vez de llamar `verify_token` directamente.
