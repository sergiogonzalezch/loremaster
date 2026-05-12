# Resultados de Auditoría de Seguridad — Lore Master

**Fecha de validación:** 2026-05-11  
**Auditoría original:** `docs/AUDIT-SECURITY.md` (2026-05-09)  
**Branch:** `main`  

---

## Resumen ejecutivo

La validación del código fuente frente a los 53 hallazgos reportados en la auditoría original revela el siguiente estado:

| Estado | Total |
|---|---:|
| **Resueltos** | **15** |
| **Parcialmente resueltos** | **18** |
| **No resueltos** | **17** |
| **No verificados / pendientes** | **3** |
| **Total** | **53** |

> **Conclusión:** Los problemas de mayor impacto (IDOR en documentos, path traversal parcial, secretos por defecto, headers de seguridad, magic bytes) han recibido atención, pero persisten **gaps críticos en autorización de documentos**, **validación de usuarios eliminados en Clerk**, **limpieza de archivos físicos** y **protección CSRF/storage de tokens**.

---

## Problemas Resueltos (15)

### 🔴 Críticos (2)

| ID | Problema | Archivo(s) involucrado(s) |
|---|---|---|
| **C-1** | Import incorrecto de Clerk en producción | `backend/app/core/auth/dependencies.py` |
| **C-4** | IDOR cross-tenant en listado de entidades | `backend/app/api/routes/entities/entities.py` |

### 🟠 Altos (6)

| ID | Problema | Archivo(s) involucrado(s) |
|---|---|---|
| **H-6** | `validate_document` confiaba solo en `content_type` del cliente | `backend/app/core/storage/validator.py` |
| **H-7** | `PdfReader` sin cap de páginas (PDF bombs) | `backend/app/engine/extractor.py` |
| **H-9** | Sin headers de seguridad (HSTS, CSP, X-Frame-Options, etc.) | `backend/app/api/middlewares/security_headers.py` |
| **H-10** | Clerk JWT decodificado sin `issuer=` ni allowlist de algoritmos | `backend/app/api/routes/auth/auth_clerk.py` |
| **H-11** | `requirements.txt` sin pin ni lockfile | `backend/requirements.txt` |
| **H-12** | `python-jose` no pineado | `backend/requirements.txt` |

### 🟡 Medios (4)

| ID | Problema | Archivo(s) involucrado(s) |
|---|---|---|
| **M-7** | `/docs`, `/redoc`, `/openapi.json` siempre expuestos | `backend/app/main.py` |
| **M-11** | `RequestValidationError` exponía input del cliente | `backend/app/main.py` |
| **M-14** | Log injection con CR/LF + XSS vía filename | `backend/app/services/document/documents_service.py` |
| **M-15** | `storage_path` filtrado en API pública | `backend/app/models/schemas/public.py`, `backend/app/models/schemas/user_schemas.py` |

### 🟢 Bajos (3)

| ID | Problema | Archivo(s) involucrado(s) |
|---|---|---|
| **L-4** | `save_file` sin assert de containment bajo `media_root` | `backend/app/core/storage/__init__.py` |
| **L-5** | Aislamiento de servicios internos vía settings | Reportado como limpio en auditoría original |
| **L-6** | Aislamiento Qdrant por nombre prefijado | Reportado como limpio en auditoría original |

---

## Problemas Parcialmente Resueltos (18)

### 🔴 Críticos (5)

| ID | Problema | Qué está hecho | Qué falta |
|---|---|---|---|
| **C-3** | IDOR cross-tenant en endpoints de documentos | `ingest`, `list_documents` y `document_events` usan `get_collection_or_404_owned`. | `get_document`, `retry_ingest` y `delete_document` siguen usando `get_document_or_404` **sin verificar ownership**. Cualquier usuario autenticado puede leer, reintentar o borrar documentos de otros iterando UUIDs. |
| **C-5** | Path traversal vía username en upload de avatar | Username ahora valida con regex `^[A-Za-z0-9_-]{3,50}$`. `save_file` tiene defensa `is_relative_to`. | `delete_profile_image` sigue usando `shutil.rmtree(profile_dir)` — borrado arbitrario de directorios si se bypassa el regex. `build_storage_path` no tiene assert `is_relative_to`. |
| **C-6** | Mount `/media` público sin auth | Reemplazado por `media_router` con protección contra path traversal y `X-Content-Type-Options: nosniff`. | Sigue siendo **público** (sin auth), sin `Content-Disposition: attachment`, sin verificación de `is_shared`, sin lista blanca estricta de Content-Type. |
| **C-7** | JWT secret por defecto `"your-secret-key"` aceptado en local | `requirements.txt` pinea `python-jose[cryptography]==3.5.0`. Validador Pydantic rechaza el default en entornos no locales y exige `len >= 32`. | El default `"your-secret-key"` sigue existiendo en el código (`config/__init__.py:114`). Falta chequeo explícito de `payload["alg"]` en `verify_token` para prevenir alg-confusion. |
| **C-8** | Postgres con credenciales hardcodeadas | — | `docker-compose.yml` sigue con `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-loremaster}` (default hardcodeado) y puerto `5433:5432` expuesto al host sin bind a `127.0.0.1`. |

### 🟠 Altos (4)

| ID | Problema | Qué está hecho | Qué falta |
|---|---|---|---|
| **H-1** | `is_admin` viajaba dentro del JWT | El endpoint `login` ya no incluye `is_admin` en el token. `get_admin_user` re-consulta la BD. | El endpoint `register` sí incluye `is_admin` en el JWT (`auth.py:175`). La duplicación sigue siendo frágil. |
| **H-2** | `PATCH /users/me` aceptaba email sin validación ni unicidad | `UpdateProfileRequest.email` usa `EmailStr` (`user_schemas.py:88`). | `users.py:48-49` no verifica que el nuevo email no esté ya en uso por otro usuario activo. |
| **H-3** | Feed público filtra por `is_deleted`, pero admin delete no despublica contenido/imágenes | El feed público filtra por `User.is_deleted == False` (`filters.py:19`). | Los avatares de perfil NO se eliminan en cascada durante `admin_delete_user`. El media_router permite acceso directo sin verificar `is_shared`. |
| **H-8** | Cero rate limiting | Existe `RateLimitMiddleware` aplicado a operaciones mutantes (POST/PUT/PATCH/DELETE). | No aplica a GET/HEAD, opera en memoria (no escala a múltiples workers), y no protege endpoints de lectura intensiva. |

### 🟡 Medios (5)

| ID | Problema | Qué está hecho | Qué falta |
|---|---|---|---|
| **M-4** | ComfyUI `download_image` reenvía `filename`/`subfolder` sin sanitizar | Ahora usa `_sanitize_filename` que elimina caracteres no alfanuméricos/guiones/puntos. | Mitiga pero no elimina completamente el riesgo histórico de ese endpoint. |
| **M-8** | AWS credenciales de test en `.env.example` | Credenciales AWS están comentadas y usan placeholders genéricos. | El placeholder de `SECRET_KEY` sigue siendo un footgun si un operador hace `cp .env.example .env` sin cambiarlo en producción. |
| **M-10** | Logging sin redacción de PII | `_sanitize_for_log` elimina CR/LF de filenames. | No hay redacción generalizada de PII en todos los logs. |
| **M-13** | Cleanup roto: archivos huérfanos para siempre | `_cascade_delete_images` ahora intenta borrar archivos físicos. | `_delete_image_file` usa `Path(storage_path)` como ruta relativa al CWD en lugar de resolverla bajo `media_root`, por lo que probablemente **no borra los archivos reales**. Los avatares de perfil tampoco se limpian en cascada. |
| **M-18** | Validación cliente-only de avatar | Backend valida MIME, extensión, tamaño y hace strip de EXIF. | Falta validación de **magic bytes para imágenes** (TODO en `validator.py:13`). |

### 🟢 Bajos (4)

| ID | Problema | Qué está hecho | Qué falta |
|---|---|---|---|
| **L-1** | `admin_delete_collection` idempotente sin audit log | Hay un `logger.info` con datos básicos. | No es un audit log estructurado ni inmutable. |
| **L-2** | `validate_image` sin cross-validación MIME ↔ extensión ↔ magic bytes | Valida MIME ↔ extensión y strip de EXIF. | Falta magic bytes para imágenes. |
| **L-8** | `scripts/make_admin.py` promociona admin sin confirmación | Ahora requiere confirmación interactiva o flag `--force`. | Falta audit log de la acción. |
| **L-12** | Logger global a INFO sin estructura/redacción | Mejorado con sanitización de filenames. | Falta redacción generalizada de PII y formato estructurado. |

---

## Problemas No Resueltos (17)

### 🔴 Críticos (1)

| ID | Problema | Archivo(s) involucrado(s) | Impacto |
|---|---|---|---|
| **C-2** | Producción salta verificación de usuario en BD | `backend/app/core/auth/dependencies.py:46-49` | Usuarios soft-deleted siguen siendo válidos en producción; `token_version` no se consulta en el branch de Clerk. |

### 🟠 Altos (4)

| ID | Problema | Archivo(s) involucrado(s) | Impacto |
|---|---|---|---|
| **H-4** | Indirect prompt injection vía documentos subidos | `backend/app/domain/prompt_templates.py:72-74` | Payload en PDF puede cerrar etiquetas `</context></user_request>` y reescribir instrucciones del sistema. |
| **H-5** | Prompt injection vía `entity.name` / `entity.description` | `backend/app/services/entity/generation_service.py:77-81` | Estos campos se interpolan fuera de `<context>` en zona de instrucciones, sin defensa estructural. |
| **H-13** | JWT en `localStorage` | `frontend/src/utils/token.ts:9-14` | Cualquier XSS futuro exfiltra el token inmediatamente. |
| **H-14** | Sin defensa CSRF planeada | — | Si se migra a cookies sin `SameSite=Strict` + token CSRF, todas las rutas mutantes quedan expuestas. |

### 🟡 Medios (8)

| ID | Problema | Archivo(s) involucrado(s) | Impacto |
|---|---|---|---|
| **M-1** | `content_guard.py` es decorativo | `backend/app/domain/content_guard.py:13-28` | 6 regex en denylist mínima; no detecta jailbreaks, leetspeak, base64, ROT13. |
| **M-2** | ReDoS / CPU-DoS: 6 regex sobre texto normalizado | `backend/app/domain/content_guard.py:52-62` | Worker bloqueado aplicando regex sobre archivos de hasta 50MB normalizados con NFKD. |
| **M-3** | Prompt injection vía `confirmed_content` editable | `backend/app/services/entity/content_service.py:103` | `edit_content` NO ejecuta `check_user_input` sobre el nuevo texto antes de guardarlo. |
| **M-5** | `/auth/clerk/verify` decodifica y devuelve `user_id` sin chequeo de `is_deleted` | `backend/app/api/routes/auth/auth_clerk.py:73-84` | Inconsistente con `get_current_user` del branch local. |
| **M-6** | Sin compare constant-time + sin dummy-bcrypt → timing oracle | `backend/app/api/routes/auth/auth.py:111-116` | Distingue "user not found" vs "wrong password" por tiempo de respuesta. |
| **M-9** | CORS no exige HTTPS cuando `environment != "local"` | `backend/app/core/config/__init__.py:151-157` | Solo exige HTTPS en `production`; `demo` queda sin validación. |
| **M-12** | Default `environment="local"` en código (fail-open) | `backend/app/core/config/__init__.py:69` | Olvidar setear `production` deja todas las guardas de seguridad desactivadas. |
| **M-17** | Migración planeada a cookies sin pareja CSRF defensiva | — | Plan pendiente sin implementación. |

### 🟢 Bajos (4)

| ID | Problema | Archivo(s) involucrado(s) | Impacto |
|---|---|---|---|
| **L-3** | TOCTOU en `delete_image_service` | `backend/app/services/image/image_generation_service.py:484-488` | `if os.path.exists(full_path): os.remove(full_path)` es vulnerable a race condition. |
| **L-7** | No hay `secrets.compare_digest` documentado como regla | — | Comparaciones de strings sensibles no usan timing-safe comparison. |
| **L-11** | Token revocation TTL no documentado | — | `token_version` existe pero sin política de TTL formal ni documentación. |
| **L-13** | Docker compose publica Qdrant 6333 y Redis 6379 al host | `backend/docker-compose.yml` | Exposición de servicios internos en entorno de desarrollo (bajo riesgo, pero persistente). |

---

## No Verificados / Pendientes (3)

| ID | Problema | Motivo |
|---|---|---|
| **M-16** | `rehype-sanitize` con schema default es la única barrera XSS | Requiere revisión profunda del frontend (React + rehype-sanitize). |
| **L-9** | Frontend `<img src={url}>` sin allowlist de origen | Requiere revisión del código fuente del frontend. |
| **L-10** | `<Route path="/admin">` solo gateado por `ProtectedRoute` | Requiere revisión del routing del frontend. |

---

## Áreas verificadas y limpias (sin cambios desde auditoría original)

- **Cero SQL injection.** Todo SQLModel parametrizado; `.ilike(f"%{x}%")` usa bound parameters.
- **Cero command injection.** Sin `subprocess`/`os.system`/`Popen`/`eval`/`exec` en `app/`.
- **Cero deserialización insegura.** Sin `pickle.loads`, sin `yaml.load` inseguro.
- **Sin secretos commiteados.** `.env` nunca tracked en git history.
- **CORS no usa `*` con `allow_credentials`** (validator lo bloquea).
- **Bcrypt usado correctamente** para hashing de passwords.
- **Frontend:** cero `dangerouslySetInnerHTML`, `innerHTML`, `eval`, `new Function`, `document.write`, `postMessage` con `*`. `npm audit`: 0 vulnerabilidades.
- **Mass-assignment estructuralmente prevenido** — schemas de request no aceptan `user_id`/`owner_id`/`role`/`is_admin`.
- **Open redirect:** sin `RedirectResponse` en backend; rutas de frontend internas y literales.

---

## Top 5 fixes de mayor leverage (pendientes)

1. **C-3:** Sustituir `get_document_or_404` → `get_document_or_404_owned` en `documents.py` (get_document, retry_ingest, delete_document).
2. **C-2:** Replicar lookup de BD (`is_deleted`, `token_version`) en el branch de Clerk de `get_current_user`.
3. **C-5:** Reemplazar `shutil.rmtree` en `delete_profile_image` por eliminación de archivos individuales con `is_relative_to`.
4. **C-6:** Proteger `media_router` con auth + verificación de `is_shared` + `Content-Disposition: attachment`.
5. **C-8 + M-13:** Eliminar defaults de PostgreSQL en `docker-compose.yml` y corregir `_delete_image_file` para resolver rutas bajo `media_root`.

---

*Generado automáticamente el 2026-05-11 a partir de la validación de código frente a `docs/AUDIT-SECURITY.md`.*
