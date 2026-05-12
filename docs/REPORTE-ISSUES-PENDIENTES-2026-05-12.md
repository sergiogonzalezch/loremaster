# Reporte de Issues Pendientes — Análisis de Riesgo y Recomendación

**Fecha:** 2026-05-12  
**Rama:** `bugfix/security-concers`  
**Commit base:** `74ebb03`  
**Restricción:** Este documento es solo análisis. No modifica código.

---

## Contexto

Tras los commits `894126f` (mitigación feedback) y `2b45a07` (batch docstrings), quedan **~315 issues** detectados por `ruff --select ALL` distribuidos en tres categorías principales.

Este reporte analiza:
1. Si la corrección afecta la **lógica de negocio**.
2. Si puede **generar nuevos issues** (regresiones, bugs).
3. Si puede **afectar los fixes del AUDIT-SECURITY** (C-1 a C-8, H-1 a H-14, etc.).

---

## 1. FAST002 + B008 — Dependencias FastAPI sin `Annotated`

### Métricas
- **Cantidad:** ~225 issues (pares FAST002+B008)
- **Archivos afectados:** ~20 archivos de rutas (`api/routes/**/*.py`)
- **Distribución estimada:**
  - `auth.py` (~20)
  - `auth_clerk.py` (~4)
  - `admin.py` (~12)
  - `collections.py` (~20)
  - `documents.py` (~20)
  - `entities.py` / `content.py` (~30)
  - `image_generation.py` (~20)
  - `users.py` (~10)
  - `public.py` (~8)
  - `media.py` (~4)
  - Otros routers menores

### Qué es

```python
# Patrón actual (funciona, B008 lo marca)
def login(
    request: LoginRequest,
    response: Response,
    session: Session = Depends(get_session),
):

# Patrón moderno (FAST002 lo exige)
def login(
    request: LoginRequest,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
):
```

### Impacto en lógica de negocio

**NINGUNO.** Es un cambio exclusivamente de tipo/sintaxis.

FastAPI interpreta ambos patrones de forma idéntica en runtime. `Annotated[T, Depends(...)]` es azúcar sintáctico que FastAPI resuelve igual que el default argument. No hay cambio en:
- Inyección de dependencias.
- Orden de resolución.
- Cacheo de `Depends`.
- Valores por defecto reales.

### Riesgo de regresión si se resuelve

| Riesgo | Severidad | Justificación |
|---|---|---|
| Error de tipeo al escribir `Annotated` | Baja | Fácilmente detectable por ruff y mypy. Los tests cubren todos los endpoints. |
| Import faltante de `typing.Annotated` | Baja | Detectable por ruff (F401/F821). |
| Líneas más largas (E501) | Media | `Annotated[Session, Depends(get_session)]` es más largo que `Session = Depends(get_session)`. Puede crear nuevos E501 en rutas ya ajustadas. |
| Git blame ensuciado en archivos auditados | Media | `auth.py`, `auth_clerk.py`, `documents.py`, `entities.py` fueron modificados en el audit (C-3, C-4, C-5, H-10, etc.). Un refactor masivo dificulta `git blame` para rastrear los fixes de seguridad. |
| Confusión en code review | Baja | 225 líneas cambiadas en 20 archivos es ruido que oscurece cambios funcionales futuros. |

### Relación con AUDIT-SECURITY

**Sin riesgo directo.** Las dependencias auditadas (`get_current_user`, `get_admin_user`, `get_collection_or_404_owned`, `get_document_or_404_owned`, `get_session`) conservarían exactamente la misma semántica de ejecución. El cambio es puramente declarativo.

**Riesgo indirecto:** Si al refactorizar se tocan líneas adyacentes a fixes de seguridad (ej. el `hmac.compare_digest` en `dependencies.py`, el `_owned` en `documents.py`), existe la posibilidad humana de error de copiar/pegar. Mitigable con herramientas de refactor automatizado (ej. `sed` o script) en vez de manual.

### Veredicto

✅ **Técnicamente seguro de resolver.**  
⚠️ **Recomendación: diferir o aplicar con script automatizado en un único commit masivo** para no ensuciar la historia de fixes de seguridad. No aporta valor funcional inmediato.

---

## 2. E501 — Líneas largas (>88 columnas)

### Métricas
- **Cantidad:** 74 issues
- **Archivos afectados:** ~25
- **Distribución por criticidad:**

#### 🔴 Archivos de seguridad crítica (alto riesgo de regresión)

| Archivo | Líneas | Contenido | Riesgo si se parte mal |
|---|---|---|---|
| `app/api/middlewares/security_headers.py:56` | 90 cols | String CSP (`font-src 'self' https://fonts.googleapis.com https://fonts.gstatic.com`) | **ALTO** — un salto de línea mal colocado en una string CSP puede romper el header, dejando la app sin protección CSP o con CSP inválido. |
| `app/api/middlewares/security_headers.py:69` | 90 cols | String CSP (`style-src 'self' 'unsafe-inline' https://fonts.googleapis.com`) | **ALTO** — mismo riesgo. |
| `app/api/routes/auth/auth.py:77` | 98 cols | Docstring con backslashes (`\, etc.`) | **BAJO** — ya resuelto como `r"""`. Es un E501 residual en línea de docstring. Partir docstring no afecta lógica. |
| `app/core/config/__init__.py:118` | 108 cols | Validador Pydantic (`model_validator` con `mode="after"`) | **MEDIO** — los validators son críticos para seguridad (C-7: `secret_key`, M-12: `environment`). Partir mal una firma de validator puede romper la validación. |
| `app/core/config/__init__.py:161` | 94 cols | Validator CORS (`https://` en producción) | **MEDIO** — validador de CORS (M-9). Lógica sensible pero solo es una comparación string. |
| `app/core/config/__init__.py:174` | 94 cols | Lógica similar | **MEDIO** |
| `app/core/storage/__init__.py:59` | 99 cols | `is_relative_to(media_root_resolved)` | **ALTO** — `save_file` implementa defensa de path traversal (C-5, L-4). Partir mal esta línea no debería afectar, pero cualquier alteración en `storage/__init__.py` debe revisarse. |
| `app/core/storage/__init__.py:61` | 100 cols | Lógica similar | **ALTO** |
| `app/api/routes/documents/documents.py:118` | 90 cols | Logger warning | **BAJO** — ya fue modificado en `2b45a07`. Es un string de log. |

#### 🟡 Archivos de lógica de negocio (riesgo medio)

| Archivo | Líneas | Contenido | Riesgo |
|---|---|---|---|
| `app/domain/content_guard.py` | 29, 52, 53, 80, 81, 101 | Regex patterns de bloqueo de contenido | **MEDIO** — las regex son strings raw (`r"..."`). Partirlas en múltiples líneas con paréntesis es seguro, pero si se usa concatenación implícita (`"a" "b"`) en lugar de agrupación con paréntesis, se puede romper el pattern. |
| `app/domain/image_prompt_rules.py` | 31, 35, 52–56, 70, 76 | Prompt templates largos | **BAJO** — strings multilinea de prompts. Seguro de partir con paréntesis. |
| `app/core/exceptions/__init__.py` | 109, 133 | Docstrings con descripciones largas | **BAJO** |
| `app/core/lifespan.py:21` | 100 cols | Docstring de `_run_migrations` | **BAJO** |

#### 🟢 Archivos triviales (riesgo bajo)

| Archivo | Líneas | Contenido | Riesgo |
|---|---|---|---|
| `app/core/__init__.py:4` | 89 cols | Re-export | Ninguno |
| `app/core/api/filters.py:1` | 92 cols | Docstring de módulo | Ninguno |

### Impacto en lógica de negocio

**Ninguno si se resuelve correctamente.** E501 es puramente cosmético.

El riesgo surge de **cómo** se parte la línea:
- **Strings CSP:** Deben mantenerse como strings continuas. Partir con `"..." \` o `"..." + "..."` puede introducir espacios o romper la sintaxis del header.
- **Regex raw:** Deben agruparse con paréntesis `(` `)` para concatenación implícita de strings, no con `+` que puede cambiar la precedencia de escapes.
- **Validators Pydantic:** Partir la firma del método es seguro; partir la lógica interna requiere cuidado.

### Riesgo de regresión si se resuelve

| Riesgo | Severidad | Mitigación |
|---|---|---|
| CSP header roto | **ALTO** | No tocar `security_headers.py` sin tests de integración que validen el header exacto. |
| Regex de `content_guard.py` rota | **MEDIO** | Tests unitarios de `content_guard.py` verifican que los patterns matchean. Ejecutar antes y después. |
| Validator de config roto | **MEDIO** | Tests de arranque verifican que Settings carga correctamente. |
| Nuevos E501 creados | **BAJO** | Al partir una línea, los parámetros indentados pueden superar 88 cols. |

### Relación con AUDIT-SECURITY

| Fix auditado | Archivo E501 | Riesgo de afectación |
|---|---|---|
| C-5 (path traversal) | `core/storage/__init__.py` | **ALTO** — `save_file` con `is_relative_to` es la defensa. No tocar sin revisión de seguridad. |
| C-6 (media controller) | `api/middlewares/security_headers.py` | **ALTO** — CSP es parte de la defensa XSS. |
| C-7 (secret_key validator) | `core/config/__init__.py` | **MEDIO** — validators de Settings. |
| M-9 (CORS HTTPS) | `core/config/__init__.py` | **MEDIO** — validador de orígenes. |
| H-9 (security headers) | `api/middlewares/security_headers.py` | **ALTO** — mismo que C-6. |
| M-2 (ReDoS mitigation) | `domain/content_guard.py` | **MEDIO** — regex de bloqueo. |

### Veredicto

⚠️ **Parcialmente seguro.** Los E501 en `core/__init__.py`, `core/api/filters.py`, `core/lifespan.py` y docstrings son triviales.  
🔴 **Los E501 en `security_headers.py`, `storage/__init__.py` y `config/__init__.py` son de ALTO riesgo** porque tocan código auditado de seguridad con strings sensibles (CSP, path traversal, secret validation).  
💡 **Recomendación:** Resolver solo los E501 en archivos no críticos (`domain/image_prompt_rules.py`, `core/exceptions/`, `core/lifespan.py`, docstrings). Dejar los de seguridad para un ciclo de audit dedicado.

---

## 3. PLR0913 — Demasiados argumentos (>5)

### Métricas
- **Cantidad:** 16 issues
- **Archivos afectados:** 10

### Desglose completo

| # | Archivo | Función | Args | Args >5 | Qué hace | Riesgo si se reestructura |
|---|---|---|---|---|---|---|
| 1 | `api/routes/documents.py:100` | `list_documents` | 7 | `pagination, dates, filename, file_type, status, _, __, session` | Lista documentos con filtros. Tiene `_: Collection = Depends(...)` y `__: dict = Depends(get_current_user)` que no se usan directamente en la firma. | **MEDIO** — Los `_` y `__` son dependencias de auth/ownership. Si se agrupan en un DTO, FastAPI podría no inyectarlas correctamente. |
| 2 | `api/routes/entities/content.py:82` | `generate_content` | 6 | `session, collection, entity, user, body` | Genera contenido para entidad. | **BAJO** — 6 args es levemente excedido. |
| 3 | `api/routes/entities/content.py:111` | `edit_content` | 6 | `session, collection, entity, user_id, content_id, body` | Edita contenido confirmado. | **BAJO** |
| 4 | `api/routes/entities/entities.py:55` | `list_entities` | 6 | `collection_id, pagination, name, entity_type, created_after, created_before, _, __, session` | Lista entidades con filtros. Igual que documents: dependencias de auth ocupan slots. | **MEDIO** — `_` y `__` son dependencias FastAPI. |
| 5 | `core/database/utils.py:36` | `paginate_with_sort` | 7 | `session, model, conditions, page, page_size, order_col, order` | Utilidad de paginación genérica. | **BAJO** — es una utility interna. |
| 6 | `engine/rag_pipeline.py:64` | `invoke_rag_pipeline` | 6 | `collection_id, query, threshold, rag, llm_chain, render_fn` | Pipeline RAG. | **BAJO** — interno del engine. |
| 7 | `services/collection/collection_service.py:116` | `list_collections_service` | 8 | `session, owner_id, page, page_size, name, created_after, created_before, order` | Lista colecciones con filtros. | **BAJO-MEDIO** — firma pública usada por router. Cambiar requiere ajustar caller. |
| 8 | `services/document/documents_service.py:173` | `list_documents_service` | 10 | `session, collection_id, page, page_size, filename, file_type, status, created_after, created_before, order` | Lista documentos con filtros. | **MEDIO** — firma pública. Cambiar a DTO requiere actualizar router y tests. |
| 9 | `services/entity/content_service.py:25` | `list_contents` | 8 | `session, entity_id, collection_id, category, status, page, page_size, order` | Lista contenidos de entidad. | **BAJO-MEDIO** |
| 10 | `services/entity/content_service.py:83` | `edit_content` | 6 | `session, content_id, new_text, user_id, entity_id, collection_id` | Edita contenido. | **BAJO** |
| 11 | `services/entity/content_service.py:327` | `soft_delete_content` | 6 | `session, content_id, entity_id, collection_id, user_id, reason` | Soft-delete de contenido. | **BAJO** |
| 12 | `services/entity/entities_service.py:67` | `list_entities_service` | 9 | `session, collection_id, page, page_size, name, entity_type, created_after, created_before, order` | Lista entidades con filtros. | **MEDIO** — firma pública. |
| 13 | `services/image/image_generation_service.py:66` | `generate_images_service` | 8 | `session, entity, content_id, collection_id, user_id, width, height, batch_size` | Genera imágenes. | **BAJO-MEDIO** |
| 14 | `services/image/image_generation_service.py:109` | `delete_image_service` | 9 | `session, image_id, collection_id, entity_id, user_id, delete_vectors, delete_files, reason` | Elimina imagen. | **BAJO-MEDIO** |
| 15 | `services/image/image_generation_service.py:173` | `share_image_service` | 9 | `session, image_id, collection_id, entity_id, user_id, is_shared, shared_title, shared_description` | Comparte imagen. | **BAJO-MEDIO** |
| 16 | `services/image/image_generation_service.py:306` | `list_generations_service` | 8 | `session, entity_id, collection_id, user_id, page, page_size, status, order` | Lista generaciones. | **BAJO-MEDIO** |

### Qué es

PLR0913 es una regla de pylint que marca funciones con más de 5 argumentos posicionales/keyword. La razón es que funciones con muchos argumentos son difíciles de usar, testear y mantener. El patrón de solución es agrupar argumentos relacionados en clases/DTOs.

### Impacto en lógica de negocio

**NINGUNO** si se resuelve correctamente. Es puramente reestructuración de firma.

**ALTO** si se resuelve mal:
- Cambiar `list_documents_service(session, collection_id, page, ...)` a `list_documents_service(session, filters: DocumentFilters)` requiere:
  1. Crear la clase `DocumentFilters`.
  2. Actualizar el router para construir `DocumentFilters`.
  3. Actualizar todos los tests que llaman a `list_documents_service`.
  4. Asegurar que los valores por defecto (`page=1`, `page_size=20`) se mantengan.

### Riesgo de regresión si se resuelve

| Riesgo | Severidad | Justificación |
|---|---|---|
| Router no pasa argumentos correctamente | **ALTO** | Si se introduce un DTO pero el router sigue pasando argumentos sueltos, falla en runtime. |
| Valores por defecto perdidos | **ALTO** | `page=1`, `page_size=20`, `order="desc"` deben replicarse en el DTO. |
| Tests rotos | **MEDIO** | Todos los tests unitarios de servicios deben reescribirse para usar el DTO. |
| Type hints rotos | **BAJO** | FastAPI necesita que el DTO sea un Pydantic model o dataclass para la documentación OpenAPI. Si es solo una dataclass interna, no afecta la API pública. |
| Dependencias FastAPI confundidas | **MEDIO** | En routers, `_` y `__` son `Depends()` de auth. No pueden ir en un DTO porque FastAPI no inyecta `Depends` dentro de modelos Pydantic. Deben permanecer como parámetros de endpoint. |

### Relación con AUDIT-SECURITY

| Fix auditado | Función PLR0913 | Riesgo |
|---|---|---|
| C-3 (IDOR documents) | `list_documents` (router) | **ALTO** — este endpoint usa `get_collection_or_404_owned`. Si se reestructuran los parámetros, hay que asegurar que `_` (la dependencia de ownership) no se pierda ni se desordene. |
| C-4 (IDOR entities) | `list_entities` (router) | **ALTO** — mismo riesgo. `get_collection_or_404_owned` es la defensa. |
| C-5 (path traversal) | `list_documents_service` | **MEDIO** — no directamente, pero está en la misma capa de servicios. |
| H-6 (magic bytes) | `generate_images_service` | **BAJO** — el fix de magic bytes está en `validator.py`, no en la firma del servicio. |
| M-13 (cleanup físico) | `delete_image_service` | **MEDIO** — este servicio borra archivos físicos. Si se reestructura y se pierde un parámetro (ej. `delete_files=True`), el cleanup se rompe. |

### Veredicto

🔴 **No recomendado resolver en este ciclo.**  
PLR0913 requiere diseño de DTOs y actualización coordinada de routers + tests. Es un refactor arquitectónico, no una limpieza de código. El beneficio (legibilidad) no justifica el riesgo de romper endpoints auditados de seguridad.

**Si en el futuro se decide resolver:**
1. Empezar por `paginate_with_sort` (utility interna, 0 impacto en API pública).
2. Luego `list_collections_service`, `list_entities_service`, `list_documents_service` — crear `Filter` dataclasses.
3. **Nunca** agrupar dependencias FastAPI (`Depends(get_current_user)`, `Depends(get_collection_or_404_owned)`) dentro de DTOs.

---

## Matriz de riesgo resumida

| Categoría | Cantidad | Impacto lógica | Riesgo regresión | Riesgo AUDIT | Recomendación |
|---|---|---|---|---|---|
| FAST002 + B008 | ~225 | Ninguno | Bajo-Medio | Ninguno directo | **Diferir** o script masivo |
| E501 (seguridad) | ~15 | Ninguno | Alto | Alto | **NO tocar** (security_headers, storage, config) |
| E501 (resto) | ~59 | Ninguno | Bajo | Ninguno | **Seguro** de resolver (domain, exceptions, docstrings) |
| PLR0913 | 16 | Ninguno | Alto | Alto | **NO tocar** sin diseño de DTOs |

---

## Conclusión ejecutiva

De los ~315 issues restantes:

- **~225 FAST002/B008** son cosméticos puros, seguros pero masivos. El feedback original ya los clasificó como "diferir". No afectan ni lógica ni seguridad.
- **~74 E501** son mayoritariamente seguros, **excepto ~15 en archivos auditados de seguridad** (`security_headers.py`, `storage/__init__.py`, `config/__init__.py`, `auth.py`). Resolver los E501 en `domain/`, `exceptions/` y docstrings es seguro.
- **16 PLR0913** requieren rediseño arquitectónico (DTOs). No son limpieza de código; son refactor de diseño. El riesgo de romper endpoints con dependencias de ownership (C-3, C-4) es real.

**Ninguno de estos issues, si se dejan sin tocar, introduce riesgo funcional o de seguridad.** Son deuda técnica de bajo impacto, acorde con la clasificación original del feedback.
