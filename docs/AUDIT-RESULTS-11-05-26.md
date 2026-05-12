# Resultados de Auditoría de Seguridad — Lore Master

**Fecha de validación:** 2026-05-11  
**Auditoría original:** `docs/AUDIT-SECURITY.md` (2026-05-09)  
**Branch:** `main`  

---

## Resumen ejecutivo

La validación del código fuente frente a los 53 hallazgos reportados en la auditoría original revela el siguiente estado:

| Estado | Total |
|---|---:|
| **Resueltos** | **34** |
| **Parcialmente resueltos** | **2** |
| **No resueltos** | **14** |
| **No verificados / pendientes** | **3** |
| **Total** | **53** |

> **Nota:** 19 problemas fueron resueltos en 5 fases de implementación (ver [Fases de Implementación](#fases-de-implementación)).

> **Conclusión:** Los problemas de mayor impacto (IDOR en documentos, path traversal, secretos por defecto, headers de seguridad, magic bytes, audit logs) fueron resueltos. Persisten **gaps críticos en validación de usuarios eliminados en Clerk**, **prompt injection**, **protección CSRF/storage de tokens**, y **rate limiting completo**.

---

## Problemas Resueltos (34)

### 🔴 Críticos (7)

| ID | Problema | Archivo(s) involucrado(s) | Referencia |
|---|---|---|---|
| **C-1** | Import incorrecto de Clerk en producción | `backend/app/core/auth/dependencies.py` | — |
| **C-3** | IDOR cross-tenant en endpoints de documentos | `backend/app/core/database/dependencies.py`, `backend/app/api/routes/documents/documents.py` | [Fase 1](AUDIT-FASE1-LOG.md) |
| **C-4** | IDOR cross-tenant en listado de entidades | `backend/app/api/routes/entities/entities.py` | — |
| **C-5** | Path traversal vía `shutil.rmtree` en `delete_profile_image` | `backend/app/services/profile/profile_service.py` | [Fase 2](AUDIT-FASE2-LOG.md) |
| **C-6** | Mount `/media` público sin auth ni Content-Disposition | `backend/app/api/routes/media.py` | [Fase 3](AUDIT-FASE3-LOG.md) |
| **C-7** | JWT secret por defecto + sin protección contra alg-confusion | `backend/app/core/auth/__init__.py` | [Fase 1](AUDIT-FASE1-LOG.md) |
| **C-8** | Postgres con credenciales hardcodeadas | `backend/docker-compose.prod.yml` | [Fase 3](AUDIT-FASE3-LOG.md) |

### 🟠 Altos (8)

| ID | Problema | Archivo(s) involucrado(s) | Referencia |
|---|---|---|---|
| **H-1** | `is_admin` viajaba dentro del JWT | `backend/app/api/routes/auth/auth.py` | [Fase 1](AUDIT-FASE1-LOG.md) |
| **H-2** | `PATCH /users/me` aceptaba email sin validación ni unicidad | `backend/app/api/routes/users/users.py` | [Fase 1](AUDIT-FASE1-LOG.md) |
| **H-3** | Admin delete no despublica avatares de perfil | `backend/app/api/routes/admin/admin.py` | [Fase 2](AUDIT-FASE2-LOG.md) |
| **H-6** | `validate_document` confiaba solo en `content_type` del cliente | `backend/app/core/storage/validator.py` | — |
| **H-7** | `PdfReader` sin cap de páginas (PDF bombs) | `backend/app/engine/extractor.py` | — |
| **H-9** | Sin headers de seguridad (HSTS, CSP, X-Frame-Options, etc.) | `backend/app/api/middlewares/security_headers.py` | — |
| **H-10** | Clerk JWT decodificado sin `issuer=` ni allowlist de algoritmos | `backend/app/api/routes/auth/auth_clerk.py` | — |
| **H-11** | `requirements.txt` sin pin ni lockfile | `backend/requirements.txt` | — |
| **H-12** | `python-jose` no pineado | `backend/requirements.txt` | — |

### 🟡 Medios (10)

| ID | Problema | Archivo(s) involucrado(s) | Referencia |
|---|---|---|---|
| **M-7** | `/docs`, `/redoc`, `/openapi.json` siempre expuestos | `backend/app/main.py` | — |
| **M-8** | AWS credenciales de test en `.env.example` | `backend/.env.example` | [Fase 3](AUDIT-FASE3-LOG.md) |
| **M-10** | Logging sin redacción de PII | `backend/app/core/logging.py` | [Fase 4](AUDIT-FASE4-LOG.md) |
| **M-11** | `RequestValidationError` exponía input del cliente | `backend/app/main.py` | — |
| **M-13** | Cleanup roto: archivos huérfanos para siempre | `backend/app/services/deletion_service.py` | [Fase 2](AUDIT-FASE2-LOG.md) |
| **M-5** | `/auth/clerk/verify` sin chequeo `is_deleted` | `backend/app/api/routes/auth/auth_clerk.py` | [Fase 5](AUDIT-FASE5-LOG.md) |
| **M-6** | Timing oracle en login | `backend/app/api/routes/auth/auth.py`, `backend/app/core/auth/__init__.py` | [Fase 5](AUDIT-FASE5-LOG.md) |
| **M-14** | Log injection con CR/LF + XSS vía filename | `backend/app/services/document/documents_service.py` | — |
| **M-15** | `storage_path` filtrado en API pública | `backend/app/models/schemas/public.py`, `backend/app/models/schemas/user_schemas.py` | — |
| **M-18** | Validación cliente-only de avatar | `backend/app/core/storage/validator.py` | [Fase 2](AUDIT-FASE2-LOG.md) |

### 🟢 Bajos (6)

| ID | Problema | Archivo(s) involucrado(s) | Referencia |
|---|---|---|---|
| **L-1** | `admin_delete_collection` sin audit log estructurado | `backend/app/api/routes/admin/admin.py` | [Fase 4](AUDIT-FASE4-LOG.md) |
| **L-2** | `validate_image` sin cross-validación MIME ↔ extensión ↔ magic bytes | `backend/app/core/storage/validator.py` | [Fase 2](AUDIT-FASE2-LOG.md) |
| **L-4** | `save_file` sin assert de containment bajo `media_root` | `backend/app/core/storage/__init__.py` | — |
| **L-5** | Aislamiento de servicios internos vía settings | Reportado como limpio en auditoría original | — |
| **L-6** | Aislamiento Qdrant por nombre prefijado | Reportado como limpio en auditoría original | — |
| **L-7** | Sin `secrets.compare_digest` para comparaciones sensibles | `backend/app/core/auth/dependencies.py` | [Fase 5](AUDIT-FASE5-LOG.md) |
| **L-8** | `scripts/make_admin.py` sin audit log | `backend/scripts/make_admin.py` | [Fase 4](AUDIT-FASE4-LOG.md) |
| **L-12** | Logger global sin estructura/redacción de PII | `backend/app/core/logging.py` | [Fase 4](AUDIT-FASE4-LOG.md) |

---

## Problemas Parcialmente Resueltos (2)

### 🟠 Altos (1)

| ID | Problema | Qué está hecho | Qué falta |
|---|---|---|---|
| **H-3** | Feed público filtra por `is_deleted`, pero admin delete no despublica contenido/imágenes generadas | El feed público filtra por `User.is_deleted == False` (`filters.py:19`). Avatares se eliminan en cascada durante `admin_delete_user` ([Fase 2](AUDIT-FASE2-LOG.md)). | El contenido generado (imágenes de entidades) y el `media_router` permiten acceso directo sin verificar `is_shared`. |

### 🟡 Medios (1)

| ID | Problema | Qué está hecho | Qué falta |
|---|---|---|---|
| **M-4** | ComfyUI `download_image` reenvía `filename`/`subfolder` sin sanitizar | Ahora usa `_sanitize_filename` que elimina caracteres no alfanuméricos/guiones/puntos. | Mitiga pero no elimina completamente el riesgo histórico de ese endpoint. |

---

## Problemas No Resueltos (14)

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

### 🟡 Medios (6)

| ID | Problema | Archivo(s) involucrado(s) | Impacto |
|---|---|---|---|
| **M-1** | `content_guard.py` es decorativo | `backend/app/domain/content_guard.py:13-28` | 6 regex en denylist mínima; no detecta jailbreaks, leetspeak, base64, ROT13. |
| **M-2** | ReDoS / CPU-DoS: 6 regex sobre texto normalizado | `backend/app/domain/content_guard.py:52-62` | Worker bloqueado aplicando regex sobre archivos de hasta 50MB normalizados con NFKD. |
| **M-3** | Prompt injection vía `confirmed_content` editable | `backend/app/services/entity/content_service.py:103` | `edit_content` NO ejecuta `check_user_input` sobre el nuevo texto antes de guardarlo. |
| **M-9** | CORS no exige HTTPS cuando `environment != "local"` | `backend/app/core/config/__init__.py:151-157` | Solo exige HTTPS en `production`; `demo` queda sin validación. |
| **M-12** | Default `environment="local"` en código (fail-open) | `backend/app/core/config/__init__.py:69` | Olvidar setear `production` deja todas las guardas de seguridad desactivadas. |
| **M-17** | Migración planeada a cookies sin pareja CSRF defensiva | — | Plan pendiente sin implementación. |

### 🟢 Bajos (3)

| ID | Problema | Archivo(s) involucrado(s) | Impacto |
|---|---|---|---|
| **L-3** | TOCTOU en `delete_image_service` | `backend/app/services/image/image_generation_service.py:484-488` | `if os.path.exists(full_path): os.remove(full_path)` es vulnerable a race condition. |
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

1. **C-2:** Replicar lookup de BD (`is_deleted`, `token_version`) en el branch de Clerk de `get_current_user`.
2. **H-4 / H-5:** Agregar defensa estructural contra prompt injection en `prompt_templates.py` y `generation_service.py`.
3. **H-13:** Migrar JWT de `localStorage` a cookies `HttpOnly` + `SameSite=Strict`.
4. **M-1 / M-2:** Reemplazar `content_guard.py` decorativo por validación robusta con timeout.
5. **M-3:** Ejecutar `check_user_input` en `edit_content` antes de persistir cambios.

---

## Fases de Implementación

Los siguientes problemas fueron resueltos en 5 fases de implementación:

| Fase | Problemas | Log |
|---|---|---|
| **Fase 1** | C-3, C-5, H-1, H-2, C-7 | [`AUDIT-FASE1-LOG.md`](AUDIT-FASE1-LOG.md) |
| **Fase 2** | M-18, L-2, M-13, H-3 (avatars) | [`AUDIT-FASE2-LOG.md`](AUDIT-FASE2-LOG.md) |
| **Fase 3** | C-6, C-8, M-8 | [`AUDIT-FASE3-LOG.md`](AUDIT-FASE3-LOG.md) |
| **Fase 4** | L-1, L-8, M-10, L-12 | [`AUDIT-FASE4-LOG.md`](AUDIT-FASE4-LOG.md) |
| **Fase 5** | M-6, M-5, L-7 | [`AUDIT-FASE5-LOG.md`](AUDIT-FASE5-LOG.md) |

---

*Actualizado el 2026-05-11 tras completar las 5 fases de implementación. Estado verificado contra código fuente y tests (`175 passed`).*
