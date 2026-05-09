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
| 36 | `get_collection_or_404_public_or_owned` bypassa Clerk tokens | Backend | ✅ Eliminado | Función borrada como código muerto en 2026-05-08 (endpoint `GET /collections/public` eliminado previamente) |
| 37 | Admin delete sin cascade — vectores Qdrant y registros hijos huérfanos | Backend | ✅ Resuelto | — |
| 38 | RAG query sin ownership check | Backend | ✅ Resuelto | — |
| 39 | ComfyUI partial batch failure silencioso | Backend | 🟢 Cubierto | Solo afecta OPTION_B (en desarrollo); mock siempre completa |
| 40 | URLs hardcodeadas `localhost:8000` en ImagePanel e ImageGallery | Frontend | ✅ Resuelto | — |
| 41 | `CollectionsPage.fetchCollections` sin AbortSignal | Frontend | ✅ Resuelto | — |
| 42 | `AuthContext.decodeUser` no verifica expiración del token | Frontend | 🟢 Cubierto | API interceptor detecta 401 y redirige; solo hay lag de UX |
| 43 | Race condition en límite de pending contents | Backend | ✅ Resuelto | Post-flush recount en `generation_service.py` — rollback si se supera el límite |
| 44 | `list_contents` y `list/get_generation` sin ownership check | Backend | ✅ Resuelto | Cambiado a `get_entity_or_404_owned` en `entity_content.py` e `image_generation.py` |
| 45 | `discard_content` no actualiza `updated_at` | Backend | ✅ Resuelto | `content.updated_at` asignado en `discard_content` igual que en `confirm_content` |
| 46 | Feed público sin tie-breaker en ordenamiento | Backend | ✅ Resuelto | `EntityContent.id.asc()` y `ImageRecord.id.asc()` añadidos como segundo criterio |
| 47 | Admin delete de usuario no es transaccional | Backend | ✅ Resuelto | `cascade_delete_collection` (sin commit) + `session.commit()` único al final |
| 48 | `GET /documents/{doc_id}` sin autenticación ni ownership | Backend | 🔴 Pendiente | Falta `Depends(get_current_user)` — accesible sin token JWT |
| 49 | `GET /entities/{entity_id}` sin ownership check | Backend | 🟠 Pendiente | Usa `get_entity_or_404` en lugar de `get_entity_or_404_owned` |

**Leyenda:** 🔴 Pendiente urgente · 🟠 Alto · 🟡 Pendiente no urgente · 🟢 Cubierto (mitigado, sin acción inmediata) · ✅ Cerrado

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
- ~~Qdrant caído en tiempo de query: `test_rag_query_qdrant_unavailable_503` existe pero acepta `status_code in (200, 503)` — no inyecta fallo de Qdrant explícitamente; el test no verifica el caso de error real. Pendiente test con mock de `VectorStoreError`.~~ ✅ Cubierto en `tests/test_rag_query.py::test_rag_query_qdrant_unavailable_503`: usa `monkeypatch` para hacer fallar `retrieve_context` y verifica `status_code == 503`.
- ~~LLM timeout: verificar que el semáforo se libera correctamente aunque el request falle.~~ ✅ Cubierto en `tests/test_rag_query.py::test_rag_query_llm_failure_releases_semaphore`.

**~~`content_guard.py`~~** ✅ Cubierto  
- ~~Tests directos de los patrones regex: inputs válidos, inválidos, y edge cases (strings vacíos, unicode).~~ — `tests/test_content_guard.py` cubre 32 casos: baseline, full-width Unicode, diacríticos, mayúsculas mixtas, routing de excepciones y edge cases.

### Frontend — Tests faltantes

**Páginas**
- ~~Paginación: al eliminar el último ítem de una página, debe retroceder a la página anterior.~~ ✅ Cubierto en `CollectionsPage.test.tsx`: "retrocede a la última página válida cuando la página actual queda vacía".
- Recuperación de error: `CollectionsPage` verifica que el error se muestra (`muestra alerta de error si getCollections falla`), pero no cubre el botón de reintentar — pendiente.
- ~~Navegación a entidad eliminada: si la entidad no existe (404), redirigir con mensaje claro.~~ ✅ Cubierto en `EntityDetailPage.test.tsx`: "muestra alerta de error si la entidad no existe (404)".

**`ContentCard.tsx`**
- ~~Doble acción rápida: confirmar que la segunda acción no sobreescribe el estado de la primera.~~ ✅ Cubierto en `ContentCard.test.tsx`: "segundo clic mientras busy bloquea la acción (confirmContent llamado solo una vez)".
- ~~Rollback tras fallo de API: el estado debe volver exactamente al valor anterior.~~ ✅ Cubierto en `ContentCard.test.tsx`: "fallo de API en confirm llama onOptimisticUpdate con el contenido original".

**`MarkdownContent.tsx`**
- ~~Sanitización: inputs con `<script>`, atributos `onerror`, y links con `javascript:` deben renderizarse sin ejecutar código.~~ ✅ Cubierto en `MarkdownContent.test.tsx` (5 tests: script removal, onerror removal, javascript: href, standard markdown, https href).

**Hooks**
- ~~`useGenerate`: cancelación en vuelo — al llamar a `abort()`, el estado no debe actualizarse tras la cancelación.~~ ✅ Cubierto en `useGenerate.test.ts`: "cancel() dispara ApiAbortError → isCancelled=true, error=null" + "segunda llamada a run() aborta la primera".
- ~~`useCollectionDocumentsStatus`: verificar que el polling se detiene cuando todos los documentos salen del estado `processing`.~~ ✅ Cubierto en `useCollectionDocumentsStatus.test.ts` (6 tests: sin collectionId, sin docs, con docs completados, polling activo, polling se detiene, ApiAbortError).

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

## 37. Admin delete sin cascade — vectores Qdrant y registros hijos huérfanos

**Capa:** Backend  
**Archivo:** `backend/app/api/routes/admin.py:63-69, 79-85`  
**Impacto:** Alto — eliminar una colección vía admin deja entidades, documentos, contenidos e imágenes como registros huérfanos en BD y vectores en Qdrant sin limpiar.  
**Clasificación:** Error confirmado.

`admin_delete_collection` y `admin_delete_user` hacen un soft-delete manual del nodo raíz sin delegar en los servicios de cascada:

```python
# admin.py:66-69 — solo soft-delete del root
collection.is_deleted = True
collection.deleted_at = datetime.now(timezone.utc)
session.add(collection)
session.commit()
```

Contraste con el route normal que llama `delete_collection_service(session, collection)`, que a su vez invoca `cascade_delete_collection()` en `deletion_service.py` (limpia entidades, documentos, contenidos, imágenes **y** vectores Qdrant).

Consecuencias prácticas:
- Los registros hijos no quedan en soft-delete — siguen con `is_deleted=False`, por lo que consultas directas a esas tablas los devuelven como activos.
- Los vectores de Qdrant permanecen indefinidamente, consumiendo memoria.
- Para `admin_delete_user`: las colecciones del usuario quedan con `owner_id` apuntando a un usuario eliminado, inaccesibles pero sin limpiar.

**Solución sugerida:**
```python
# admin_delete_collection
from app.services.collection_service import delete_collection_service
delete_collection_service(session, collection)

# admin_delete_user — añadir loop sobre sus colecciones activas
collections = session.exec(select(Collection).where(Collection.owner_id == user_id, Collection.is_deleted == False)).all()
for c in collections:
    delete_collection_service(session, c)
```

---

## 38. RAG query sin ownership check

**Capa:** Backend  
**Archivo:** `backend/app/api/routes/rag_query.py:24`  
**Impacto:** Alto — cualquier usuario autenticado que conozca un `collection_id` ajeno puede ejecutar queries RAG y obtener contexto de documentos privados de otro usuario.  
**Clasificación:** Error confirmado.

```python
@router.post("/{collection_id}/query", response_model=RagQueryResponse)
def rag_query(
    ...
    _: Collection = Depends(get_collection_or_404),   # ← sin ownership
    __: dict = Depends(get_current_user),              # ← solo autenticación
    ...
```

`get_collection_or_404` solo verifica que la colección existe y no está eliminada. No compara `collection.owner_id` con el usuario del token. El endpoint requiere autenticación (no es accesible anónimamente), pero cualquier usuario registrado puede querier colecciones de otros usuarios.

Todos los demás endpoints de escritura usan `get_collection_or_404_owned`. El endpoint de query es el único que no enforza ownership.

**Solución sugerida:**
```python
_: Collection = Depends(get_collection_or_404_owned),
# eliminar la dependencia redundante __: dict = Depends(get_current_user)
```

---

## 39. ComfyUI partial batch failure silencioso

**Capa:** Backend  
**Archivo:** `backend/app/services/image_generation_service.py` — `_generate_comfyui_images`  
**Impacto:** Bajo — solo afecta OPTION_B (backend ComfyUI), que está en desarrollo y no en producción.  
**Clasificación:** Parcialmente mitigado.

Si alguna iteración del loop de generación falla, el error se logea como warning y se continúa (`continue`). La respuesta devuelve `batch_size=N` original pero la lista `images` puede contener menos imágenes que lo solicitado. El cliente no tiene forma de distinguir un resultado parcial de uno completo.

**Mitigación:** El backend `mock` siempre completa el batch. El backend ComfyUI no está en uso en producción. El route ya tiene un catch-all que devuelve 500 si `images_result` está vacío.

**Solución sugerida (baja prioridad):** Añadir `actual_batch_size: int` al response, o documentar que `len(images)` puede ser menor que `batch_size` en caso de error parcial.

---

## 40. URLs hardcodeadas `http://localhost:8000` en ImagePanel e ImageGallery

**Capa:** Frontend  
**Archivos:** `frontend/src/components/ImagePanel.tsx:50, 586`, `frontend/src/components/ImageGallery.tsx:52`  
**Impacto:** Medio — las URLs de imágenes servidas desde `/media/` apuntan a `localhost:8000` en lugar de usar `VITE_API_BASE_URL`. En cualquier entorno distinto del local (staging, producción, otro puerto) las imágenes no cargan.  
**Clasificación:** Error confirmado.

```typescript
// ImagePanel.tsx:50 y ImageGallery.tsx:52
return `http://localhost:8000/media/${img.storage_path}`;
```

El resto del proyecto ya usa la variable de entorno correctamente (`apiClient.ts:4`):
```typescript
import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1"
```

**Solución sugerida:**
```typescript
const BASE = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1")
  .replace("/api/v1", "");
return `${BASE}/media/${img.storage_path}`;
```

O centralizar en `apiClient.ts` una función `getMediaUrl(storagePath: string)`.

---

## 41. `CollectionsPage.fetchCollections` sin AbortSignal

**Capa:** Frontend  
**Archivo:** `frontend/src/pages/CollectionsPage.tsx:83`  
**Impacto:** Bajo — si el usuario navega fuera mientras se carga la lista de colecciones, la petición continúa y actualiza el estado de un componente desmontado (warning de React 18).  
**Clasificación:** Error confirmado.

```typescript
const fetchCollections = useCallback(async () => {
  // ...
  const res = await getCollections({ page, page_size: ... });  // sin signal
  setCollections(res.data);  // setState en componente potencialmente desmontado
```

Contraste con otros hooks como `useEntityContents` que sí aceptan y propagan `AbortSignal`.

**Solución sugerida:** Añadir `useEffect` con `AbortController` alrededor de `fetchCollections`:
```typescript
useEffect(() => {
  const controller = new AbortController();
  fetchCollections(controller.signal);
  return () => controller.abort();
}, [fetchCollections]);
```
Y propagar el signal a `getCollections`.

---

## 42. `AuthContext.decodeUser` no valida expiración del token

**Capa:** Frontend  
**Archivo:** `frontend/src/contexts/AuthContext.tsx`  
**Impacto:** Bajo — un token expirado mantiene al usuario con sesión aparentemente activa en la UI hasta que el interceptor de la API detecta un 401 y redirige. Genera lag de UX.  
**Clasificación:** Parcialmente mitigado.

```typescript
function decodeUser(token: string): AuthUser | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    // sin verificación de payload.exp
```

Si el token expira mientras el usuario tiene la app abierta (pestaña sin actividad durante 24 h), la UI mostrará al usuario como autenticado hasta la próxima acción que haga una petición.

**Mitigación:** `apiClient.ts` detecta 401 y llama `removeToken()` + redirige a login. La ventana de inconsistencia es pequeña en uso normal.

**Solución sugerida:**
```typescript
const now = Math.floor(Date.now() / 1000);
if (payload.exp && payload.exp < now) return null;
```

---

## ~~36. `get_collection_or_404_public_or_owned` bypassa Clerk tokens en producción~~ ✅ Eliminado

**Capa:** Backend  
**Resolución (2026-05-08):** La función `get_collection_or_404_public_or_owned` fue eliminada de `backend/app/core/deps.py` como código muerto. El endpoint `GET /collections/public` que la utilizaba había sido removido previamente, dejando esta dependencia sin ningún caller. Al eliminarla se limpiaron también los imports huérfanos (`HTTPBearer`, `HTTPAuthorizationCredentials`, `select`, `EntityContent`, `ImageRecord`, `security`, `verify_token`) que arrastraba. El problema descrito nunca llegó a afectar producción.

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
Actualizado el 2026-05-07 (ítems 31-36 añadidos — revisión del commit `b704c24` Users refactor first stage).
Actualizado el 2026-05-07 (ítems 37-42 añadidos — bug-search completo backend + frontend; 3 confirmados backend, 2 confirmados frontend, 1 parcialmente mitigado en cada capa).
Actualizado el 2026-05-08 (ítems 37, 38, 40, 41 resueltos — admin cascade delete, RAG ownership, ImagePanel/Gallery MEDIA_BASE, CollectionsPage AbortSignal).
Actualizado el 2026-05-08 (cobertura de tests revisada: useGenerate cancelación marcada cubierta; rag_pipeline Qdrant test identificado como débil; resto de tests frontend pendientes confirmados).
Actualizado el 2026-05-08 (ítems 43-47 resueltos — ownership check, race condition, updated_at, tie-breaker, admin atomicity).
Actualizado el 2026-05-08 (bug-search completo: verificados todos los ítems existentes ✅; añadidos ítems 48-49 — missing auth en GET documents, missing ownership en GET entity).*

---

## 43. Race condition en límite de pending contents ✅

**Capa:** Backend  
**Archivo:** `backend/app/services/generation_service.py:37-48`  
**Impacto:** Alto (en concurrencia) — Bajo (en uso single-user/SQLite local)  
**Clasificación:** Resuelto. Post-flush recount con rollback cierra la ventana de race condition.  
**Fix aplicado:** `generation_service.py` — `session.flush()` + recount post-insert; si `recount > max_pending_contents`, `session.rollback()` y excepción.

El check del límite es un patrón check-then-act no atómico:

```python
# generation_service.py:37-48
pending_count = session.exec(select(func.count())...).one()   # paso 1: leer
if pending_count >= settings.max_pending_contents:             # paso 2: chequear
    raise PendingLimitExceededError(...)
# … invoke_generation_pipeline(...) — puede tardar varios segundos (LLM call)
session.commit()                                               # paso 3: escribir
```

Dos requests simultáneos con `pending_count = 4` superan el check simultáneamente, llaman al LLM, y ambos hacen commit. Resultado: 6 contenidos pending en lugar de 5. La ventana de race es amplia porque `invoke_generation_pipeline` puede tardar segundos.

**Solución sugerida:**

```python
# Opción A — verificación post-insert (mínima invasión):
session.add(content)
session.flush()  # asigna ID pero no commitea
recount = session.exec(select(func.count())...).one()
if recount > settings.max_pending_contents:
    session.rollback()
    raise PendingLimitExceededError(...)
session.commit()

# Opción B — constraint de DB (más robusto):
# Añadir un unique partial index en PostgreSQL:
# CREATE UNIQUE INDEX ... WHERE status = 'pending' (solo viable con límite fijo en DB)
```

---

## 44. `list_contents`, `list_generations` y `get_generation` sin ownership check ✅

**Capa:** Backend  
**Archivos:** `backend/app/api/routes/entity_content.py:80`, `backend/app/api/routes/image_generation.py:158,180`  
**Impacto:** Medio — cualquier usuario autenticado que conozca los IDs puede leer contenidos e imágenes privadas de otro usuario.  
**Clasificación:** Resuelto.  
**Fix aplicado:** `get_entity_or_404` reemplazado por `get_entity_or_404_owned` en los tres endpoints de lectura afectados; import `get_current_user` eliminado donde ya no se usa.

Los tres endpoints de lectura usan `get_entity_or_404` (que solo verifica existencia) en lugar de `get_entity_or_404_owned` (que verifica ownership):

```python
# entity_content.py:80 — GET /{collection_id}/entities/{entity_id}/contents
_: Entity = Depends(get_entity_or_404),   # ← sin ownership
__: dict = Depends(get_current_user),     # ← solo autenticación

# image_generation.py:158 — GET .../image-generation/{generation_id}
entity: Entity = Depends(get_entity_or_404),   # ← sin ownership

# image_generation.py:180 — GET .../image-generation
entity: Entity = Depends(get_entity_or_404),   # ← sin ownership
```

Contraste: todos los endpoints de escritura (generate, confirm, discard, share, delete) sí usan `get_entity_or_404_owned`. Solo los endpoints GET de lectura de contenidos e imágenes no verifican ownership.

**Riesgo en práctica:** Los IDs son UUIDs v4 (no adivinables), por lo que la explotación requiere conocer los IDs. Sin embargo, el `content_id` se expone en el feed público (`PublicFeedItem.content_id`), lo que permite a un atacante obtener un content_id válido y luego usarlo para leer el contenido completo de otras entidades de la misma colección.

**Solución sugerida:** Reemplazar `get_entity_or_404` por `get_entity_or_404_owned` en los tres endpoints afectados:

```python
# entity_content.py:80
_: Entity = Depends(get_entity_or_404_owned),
# eliminar: __: dict = Depends(get_current_user) — ya está incluido en _owned

# image_generation.py:158 y 180
entity: Entity = Depends(get_entity_or_404_owned),
# eliminar: _: dict = Depends(get_current_user)
```

---

## 48. `GET /documents/{doc_id}` sin autenticación ni ownership 🔴

**Capa:** Backend  
**Archivo:** `backend/app/api/routes/documents/documents.py:111-115`  
**Impacto:** Crítico — el endpoint es accesible sin token JWT. Cualquier usuario (autenticado o no) que conozca un `collection_id` y `doc_id` puede leer el documento completo.  
**Clasificación:** Error confirmado.

```python
# documents.py:111-115
@router.get("/{collection_id}/documents/{doc_id}", response_model=DocumentResponse)
def get_document(
    doc: Document = Depends(get_document_or_404),
):
    return doc
```

No hay `Depends(get_current_user)`. El endpoint es completamente público. Además, `get_document_or_404` usa `get_collection_or_404` (que solo verifica existencia, no ownership), por lo que tampoco se valida que el usuario autenticado sea el owner de la colección.

**Contraste** con otros endpoints del mismo archivo:
- `ingest` (POST): `get_collection_or_404` + `get_current_user` ✅
- `get_documents` (GET list): `get_collection_or_404` + `get_current_user` ✅
- `retry_ingest` (POST): `get_current_user` ✅
- `delete_document` (DELETE): `get_current_user` ✅
- `get_document` (GET): **sin auth** ❌

**Solución sugerida:**
```python
@router.get("/{collection_id}/documents/{doc_id}", response_model=DocumentResponse)
def get_document(
    doc: Document = Depends(get_document_or_404),
    _: dict = Depends(get_current_user),
):
    return doc
```

---

## 49. `GET /entities/{entity_id}` sin ownership check 🟠

**Capa:** Backend  
**Archivo:** `backend/app/api/routes/entities/entities.py:78-83`  
**Impacto:** Alto — cualquier usuario autenticado que conozca un `collection_id` y `entity_id` ajenos puede leer los datos de esa entidad.  
**Clasificación:** Error confirmado.

```python
# entities.py:78-83
@router.get("/{collection_id}/entities/{entity_id}", response_model=EntityResponse)
def get_entity(
    entity: Entity = Depends(get_entity_or_404),
    _: dict = Depends(get_current_user),
):
    return entity
```

`get_entity_or_404` verifica que la entidad existe y pertenece a la colección (vía `get_active_by_id`), pero **no** verifica que el usuario actual sea owner de esa colección. Solo hay `get_current_user` para autenticación genérica (verificar que el token es válido), no autorización.

**Mitigación parcial:** Los IDs son UUIDs v4 (no adivinables). Sin conocer los IDs, el ataque no es práctico.

**Contraste** con el endpoint de escritura (PATCH):
```python
@router.patch("/{collection_id}/entities/{entity_id}", response_model=EntityResponse)
def update_entity(
    entity: Entity = Depends(get_entity_or_404_owned),  # ✅ owned
    ...
):
```

**Solución sugerida:**
```python
@router.get("/{collection_id}/entities/{entity_id}", response_model=EntityResponse)
def get_entity(
    entity: Entity = Depends(get_entity_or_404_owned),  # ✅ ownership check
):
    return entity
# Eliminar: _: dict = Depends(get_current_user) — ya incluido en _owned
```

---

## 45. `discard_content` no actualiza `updated_at` ✅

**Capa:** Backend  
**Archivo:** `backend/app/services/content_management_service.py:145-164`  
**Impacto:** Bajo — inconsistencia en el audit trail; `updated_at` queda a `NULL` para contenidos descartados, aunque el campo existe y se actualiza en otras operaciones.  
**Clasificación:** Resuelto.  
**Fix aplicado:** `content.updated_at = datetime.now(timezone.utc)` añadido en `discard_content`, igual que en `confirm_content`.

`confirm_content` actualiza `updated_at` al confirmar (línea 116):
```python
content.updated_at = now   # ✓ en confirm_content
```

`discard_content` no lo hace (línea 154):
```python
content.status = ContentStatus.discarded
# falta: content.updated_at = datetime.now(timezone.utc)
session.add(content)
```

Como resultado, `EntityContentResponse.updated_at` retorna `None` para contenidos descartados incluso si fueron previamente editados y luego descartados.

**Solución sugerida:**
```python
def discard_content(...):
    content = _get_pending_content(...)
    if not content:
        return None
    now = datetime.now(timezone.utc)   # añadir
    content.status = ContentStatus.discarded
    content.updated_at = now           # añadir
    session.add(content)
    ...
```

---

## 46. Feed público sin tie-breaker en ordenamiento ✅

**Capa:** Backend  
**Archivos:** `backend/app/api/routes/users.py:134`, `backend/app/api/routes/users.py:179`  
**Impacto:** Bajo — paginación no determinista cuando dos ítems comparten el mismo `confirmed_at`; puede causar que un ítem aparezca en dos páginas o no aparezca en ninguna durante la navegación.  
**Clasificación:** Resuelto.  
**Fix aplicado:** `.order_by(EntityContent.confirmed_at.desc(), EntityContent.id.asc())` en `get_public_feed`; `.order_by(ImageRecord.created_at.desc(), ImageRecord.id.asc())` en `get_public_images`.

```python
# users.py:134 — get_public_feed
.order_by(EntityContent.confirmed_at.desc())   # sin tie-breaker

# users.py:179 — get_public_images
.order_by(ImageRecord.created_at.desc())       # sin tie-breaker
```

En tests de carga o en uso multi-usuario, varios contenidos pueden tener el mismo timestamp de confirmación (resolución de un segundo en la mayoría de DBs). Sin un desempate secundario (p. ej., `id` como campo único), el orden entre páginas es no determinista.

**Solución sugerida:** Añadir un campo único como segundo criterio de ordenamiento:

```python
.order_by(EntityContent.confirmed_at.desc(), EntityContent.id.asc())
# y para imágenes:
.order_by(ImageRecord.created_at.desc(), ImageRecord.id.asc())
```

---

## 47. Admin delete de usuario no es transaccional ✅

**Capa:** Backend  
**Archivo:** `backend/app/api/routes/admin.py:85-97`  
**Impacto:** Bajo-Medio — si el proceso falla entre la eliminación de colecciones y la del usuario, el estado queda inconsistente: colecciones eliminadas pero usuario activo.  
**Clasificación:** Resuelto.  
**Fix aplicado:** Bucle cambiado a `cascade_delete_collection` (sin commit interno) + `user.is_deleted = True` + `session.commit()` único al final del handler.

```python
# admin.py:85-97
for collection in collections:
    delete_collection_service(session, collection)  # commit interno por colección
# ↑ si hay 5 colecciones y falla en la 3ª, las primeras 2 están commiteadas
user.is_deleted = True
user.deleted_at = datetime.now(timezone.utc)
session.add(user)
session.commit()   # commit separado
```

`delete_collection_service` llama `session.commit()` internamente para cada colección. Si ocurre un error de BD entre colecciones o antes del commit del usuario, el resultado es un estado parcial: algunas colecciones eliminadas, el usuario todavía activo, sin forma de reintentar de forma segura.

**Causa raíz:** `delete_collection_service` fue diseñado para ser autónomo (también lo usa el route normal de usuario). El admin debería poder ejecutar todas las operaciones en una sola transacción.

**Solución sugerida:** Crear una función `delete_user_service` en `deletion_service.py` que coordine todo en una sola unidad de trabajo:

```python
def delete_user_service(session: Session, user: User) -> None:
    collections = session.exec(
        select(Collection).where(
            Collection.owner_id == user.id,
            Collection.is_deleted == False,
        )
    ).all()
    for collection in collections:
        cascade_delete_collection(session, collection)  # flush, sin commit
    user.is_deleted = True
    user.deleted_at = datetime.now(timezone.utc)
    session.add(user)
    session.commit()  # un único commit al final
```

Nota: requiere que `cascade_delete_collection` use `session.flush()` en lugar de `session.commit()` cuando se llama desde dentro de una transacción mayor, o que se separe el `commit` a nivel del caller.

---

