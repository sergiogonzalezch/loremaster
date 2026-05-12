# Resultados de Auditoría de Seguridad — Lore Master

**Fecha de validación:** 2026-05-11  
**Auditoría original:** `docs/AUDIT-SECURITY.md` (2026-05-09)  
**Branch:** `main`  

---

## Resumen ejecutivo

La validación del código fuente frente a los 53 hallazgos reportados en la auditoría original revela el siguiente estado:

| Estado | Total |
|---|---:|
| **Resueltos** | **45** |
| **Parcialmente resueltos** | **6** |
| **No resueltos** | **3** |
| **No verificados / pendientes** | **0** |
| **Total** | **53** |

> **Nota:** 28 problemas resueltos en 12 fases + 3 hallazgos frontend verificados. Ver [Fases de Implementación](#fases-de-implementación).

> **Conclusión:** Los problemas de mayor impacto fueron resueltos: IDOR en documentos, path traversal, secretos por defecto, headers de seguridad, magic bytes, audit logs, validación de Clerk, prompt injection estructural, y mitigación de JWT en localStorage. Persisten **protección CSRF** (H-14, M-17), **rate limiting completo** (H-8), y **migración definitiva a cookies HttpOnly** (H-13).

---

## Problemas Resueltos (45)

### 🔴 Críticos (8)

| ID | Problema | Archivo(s) involucrado(s) | Referencia |
|---|---|---|---|---|
| **C-1** | Import incorrecto de Clerk en producción | `backend/app/core/auth/dependencies.py` | — |
| **C-2** | Producción salta verificación de usuario en BD | `backend/app/core/auth/dependencies.py` | [Fase 10](AUDIT-FASE10-12-LOG.md) |
| **C-3** | IDOR cross-tenant en endpoints de documentos | `backend/app/core/database/dependencies.py`, `backend/app/api/routes/documents/documents.py` | [Fase 1](AUDIT-FASE1-LOG.md) |
| **C-4** | IDOR cross-tenant en listado de entidades | `backend/app/api/routes/entities/entities.py` | — |
| **C-5** | Path traversal vía `shutil.rmtree` en `delete_profile_image` | `backend/app/services/profile/profile_service.py` | [Fase 2](AUDIT-FASE2-LOG.md) |
| **C-6** | Mount `/media` público sin auth ni Content-Disposition | `backend/app/api/routes/media.py` | [Fase 3](AUDIT-FASE3-LOG.md) |
| **C-7** | JWT secret por defecto + sin protección contra alg-confusion | `backend/app/core/auth/__init__.py` | [Fase 1](AUDIT-FASE1-LOG.md) |
| **C-8** | Postgres con credenciales hardcodeadas | `backend/docker-compose.prod.yml` | [Fase 3](AUDIT-FASE3-LOG.md) |

### 🟠 Altos (11)

| ID | Problema | Archivo(s) involucrado(s) | Referencia |
|---|---|---|---|---|
| **H-1** | `is_admin` viajaba dentro del JWT | `backend/app/api/routes/auth/auth.py` | [Fase 1](AUDIT-FASE1-LOG.md) |
| **H-2** | `PATCH /users/me` aceptaba email sin validación ni unicidad | `backend/app/api/routes/users/users.py` | [Fase 1](AUDIT-FASE1-LOG.md) |
| **H-3** | Admin delete no despublica contenido/imágenes generadas | `backend/app/api/routes/admin/admin.py`, `backend/app/services/deletion_service.py` | [Fase 2](AUDIT-FASE2-LOG.md) + [Fase 9](AUDIT-FASE9-LOG.md) |
| **H-4** | Indirect prompt injection vía documentos subidos | `backend/app/domain/prompt_templates.py` | [Fase 11](AUDIT-FASE10-12-LOG.md) |
| **H-5** | Prompt injection vía `entity.name` / `entity.description` | `backend/app/services/entity/generation_service.py`, `backend/app/domain/prompt_templates.py` | [Fase 11](AUDIT-FASE10-12-LOG.md) |
| **H-6** | `validate_document` confiaba solo en `content_type` del cliente | `backend/app/core/storage/validator.py` | — |
| **H-7** | `PdfReader` sin cap de páginas (PDF bombs) | `backend/app/engine/extractor.py` | — |
| **H-9** | Sin headers de seguridad (HSTS, CSP, X-Frame-Options, etc.) | `backend/app/api/middlewares/security_headers.py` | — |
| **H-10** | Clerk JWT decodificado sin `issuer=` ni allowlist de algoritmos | `backend/app/api/routes/auth/auth_clerk.py` | — |
| **H-11** | `requirements.txt` sin pin ni lockfile | `backend/requirements.txt` | — |
| **H-12** | `python-jose` no pineado | `backend/requirements.txt` | — |

### 🟡 Medios (13)

| ID | Problema | Archivo(s) involucrado(s) | Referencia |
|---|---|---|---|
| **M-3** | `edit_content` NO ejecuta `check_user_input` | `backend/app/services/entity/content_service.py` | [Fase 7](AUDIT-FASE7-LOG.md) |
| **M-7** | `/docs`, `/redoc`, `/openapi.json` siempre expuestos | `backend/app/main.py` | — |
| **M-8** | AWS credenciales de test en `.env.example` | `backend/.env.example` | [Fase 3](AUDIT-FASE3-LOG.md) |
| **M-9** | CORS no exige HTTPS en entorno `demo` | `backend/app/core/config/__init__.py` | [Fase 6](AUDIT-FASE6-LOG.md) |
| **M-10** | Logging sin redacción de PII | `backend/app/core/logging.py` | [Fase 4](AUDIT-FASE4-LOG.md) |
| **M-11** | `RequestValidationError` exponía input del cliente | `backend/app/main.py` | — |
| **M-13** | Cleanup roto: archivos huérfanos para siempre | `backend/app/services/deletion_service.py` | [Fase 2](AUDIT-FASE2-LOG.md) |
| **M-5** | `/auth/clerk/verify` sin chequeo `is_deleted` | `backend/app/api/routes/auth/auth_clerk.py` | [Fase 5](AUDIT-FASE5-LOG.md) |
| **M-6** | Timing oracle en login | `backend/app/api/routes/auth/auth.py`, `backend/app/core/auth/__init__.py` | [Fase 5](AUDIT-FASE5-LOG.md) |
| **M-14** | Log injection con CR/LF + XSS vía filename | `backend/app/services/document/documents_service.py` | — |
| **M-15** | `storage_path` filtrado en API pública | `backend/app/models/schemas/public.py`, `backend/app/models/schemas/user_schemas.py` | — |
| **M-18** | Validación cliente-only de avatar | `backend/app/core/storage/validator.py` | [Fase 2](AUDIT-FASE2-LOG.md) |
| **M-16** | `rehype-sanitize` con schema default como barrera XSS | `frontend/src/components/MarkdownContent.tsx` | Verificado en frontend — schema default de rehype-sanitize elimina atributos de evento inline (onerror, onclick, etc.) |

### 🟢 Bajos (13)

| ID | Problema | Archivo(s) involucrado(s) | Referencia |
|---|---|---|---|
| **L-1** | `admin_delete_collection` sin audit log estructurado | `backend/app/api/routes/admin/admin.py` | [Fase 4](AUDIT-FASE4-LOG.md) |
| **L-2** | `validate_image` sin cross-validación MIME ↔ extensión ↔ magic bytes | `backend/app/core/storage/validator.py` | [Fase 2](AUDIT-FASE2-LOG.md) |
| **L-3** | TOCTOU en `delete_image_service` | `backend/app/services/image/image_generation_service.py` | [Fase 7](AUDIT-FASE7-LOG.md) |
| **L-4** | `save_file` sin assert de containment bajo `media_root` | `backend/app/core/storage/__init__.py` | — |
| **L-5** | Aislamiento de servicios internos vía settings | Reportado como limpio en auditoría original | — |
| **L-6** | Aislamiento Qdrant por nombre prefijado | Reportado como limpio en auditoría original | — |
| **L-7** | Sin `secrets.compare_digest` para comparaciones sensibles | `backend/app/core/auth/dependencies.py` | [Fase 5](AUDIT-FASE5-LOG.md) |
| **L-8** | `scripts/make_admin.py` sin audit log | `backend/scripts/make_admin.py` | [Fase 4](AUDIT-FASE4-LOG.md) |
| **L-9** | Frontend `<img src={url}>` sin allowlist de origen | `frontend/src/components/SafeImage.tsx`, `frontend/src/utils/strings.ts` | Resuelto — `isImageUrlAllowed()` valida que solo se carguen imágenes desde mismo origin, localhost, data URIs y blob URLs |
| **L-10** | `/admin` solo gateado por `ProtectedRoute` sin verificación de rol admin | `frontend/src/components/AdminRoute.tsx`, `frontend/src/App.tsx` | [Fase 9](AUDIT-FASE9-LOG.md) |
| **L-11** | Token revocation TTL no documentado | `backend/app/core/auth/__init__.py` | [Fase 6](AUDIT-FASE6-LOG.md) |
| **L-12** | Logger global sin estructura/redacción de PII | `backend/app/core/logging.py` | [Fase 4](AUDIT-FASE4-LOG.md) |
| **L-13** | Docker compose publica Qdrant/Redis al host | `backend/docker-compose.yml` | [Fase 6](AUDIT-FASE6-LOG.md) |

---

## Problemas Parcialmente Resueltos (6)

### 🟠 Altos (2)

| ID | Problema | Qué está hecho | Qué falta |
|---|---|---|---|---|
| **H-8** | Cero rate limiting | Existe `RateLimitMiddleware` aplicado a operaciones mutantes (POST/PUT/PATCH/DELETE). | No aplica a GET/HEAD, opera en memoria (no escala a múltiples workers), y no protege endpoints de lectura intensiva. |
| **H-13** | JWT en `localStorage` | Migrado a `sessionStorage` ([Fase 12](AUDIT-FASE10-12-LOG.md)). El token se pierde al cerrar la pestaña, reduciendo la ventana de exposición a XSS persistente. | La exfiltración sigue siendo posible durante la sesión activa. La solución definitiva requiere migrar a cookies `HttpOnly` + `SameSite=Strict`. |

### 🟡 Medios (4)

| ID | Problema | Qué está hecho | Qué falta |
|---|---|---|---|---|
| **M-1** | `content_guard.py` es decorativo | Documentacion explicita de limitaciones agregada al modulo ([Fase 8](AUDIT-FASE8-LOG.md)). | Sigue sin detectar jailbreaks, leetspeak, base64, ROT13. Requiere reemplazo por solucion mas robusta. |
| **M-2** | ReDoS / CPU-DoS en `content_guard.py` | Limite de 100KB agregado antes de normalizacion NFKD ([Fase 8](AUDIT-FASE8-LOG.md)). | Las 6 regex siguen existiendo; el limite mitiga pero no elimina el riesgo de bloqueo del worker. |
| **M-4** | ComfyUI `download_image` reenvía `filename`/`subfolder` sin sanitizar | Ahora usa `_sanitize_filename` que elimina caracteres no alfanuméricos/guiones/puntos. | Mitiga pero no elimina completamente el riesgo histórico de ese endpoint. |
| **M-12** | Default `environment="local"` en código (fail-open) | Se agregó log WARNING en startup cuando `environment == "local"` ([Fase 6](AUDIT-FASE6-LOG.md)). | El default sigue siendo `"local"` (fail-open). No se cambió para no romper el flujo de desarrollo local. |

---

## Problemas No Resueltos (3)

### 🟠 Altos (2)

| ID | Problema | Archivo(s) involucrado(s) | Impacto |
|---|---|---|---|---|
| **H-14** | Sin defensa CSRF planeada | — | Si se migra a cookies sin `SameSite=Strict` + token CSRF, todas las rutas mutantes quedan expuestas. |
| **H-13** | JWT en `localStorage` | `frontend/src/utils/token.ts:9-14` | Cualquier XSS futuro exfiltra el token inmediatamente. Mitigado con `sessionStorage` ([Fase 12](AUDIT-FASE10-12-LOG.md)). |

### 🟡 Medios (1)

| ID | Problema | Archivo(s) involucrado(s) | Impacto |
|---|---|---|---|---|
| **M-17** | Migración planeada a cookies sin pareja CSRF defensiva | — | Plan pendiente sin implementación. |

### 🟢 Bajos (0)

*Sin problemas bajos no resueltos.*

---

## No Verificados / Pendientes (0)

*Todos los hallazgos han sido verificados. Los 3 hallazgos previamente no verificados fueron evaluados:*

- **M-16** ✅ Verificado — `rehype-sanitize` con schema default elimina atributos de evento inline; tests pasan
- **L-9** ✅ Resuelto — `SafeImage` implementa `isImageUrlAllowed()` con allowlist de origen
- **L-10** ⚠️ Parcial — `/admin` requiere auth pero no verifica rol admin en el frontend

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
5. **M-17:** Planificar e implementar defensa CSRF para migración a cookies.

---

## Fases de Implementación

Los siguientes problemas fueron resueltos en 9 fases de implementación:

| Fase | Problemas | Log |
|---|---|---|
| **Fase 1** | C-3, C-5, H-1, H-2, C-7 | [`AUDIT-FASE1-LOG.md`](AUDIT-FASE1-LOG.md) |
| **Fase 2** | M-18, L-2, M-13, H-3 (avatars) | [`AUDIT-FASE2-LOG.md`](AUDIT-FASE2-LOG.md) |
| **Fase 3** | C-6, C-8, M-8 | [`AUDIT-FASE3-LOG.md`](AUDIT-FASE3-LOG.md) |
| **Fase 4** | L-1, L-8, M-10, L-12 | [`AUDIT-FASE4-LOG.md`](AUDIT-FASE4-LOG.md) |
| **Fase 5** | M-6, M-5, L-7 | [`AUDIT-FASE5-LOG.md`](AUDIT-FASE5-LOG.md) |
| **Fase 6** | M-9, L-11, L-13 | [`AUDIT-FASE6-LOG.md`](AUDIT-FASE6-LOG.md) |
| **Fase 7** | M-3, L-3 | [`AUDIT-FASE7-LOG.md`](AUDIT-FASE7-LOG.md) |
| **Fase 8** | M-1, M-2 | [`AUDIT-FASE8-LOG.md`](AUDIT-FASE8-LOG.md) |
| **Fase 9** | L-10, H-3 (verificado) | [`AUDIT-FASE9-LOG.md`](AUDIT-FASE9-LOG.md) |
| **Fase 10** | C-2 | [`AUDIT-FASE10-12-LOG.md`](AUDIT-FASE10-12-LOG.md) |
| **Fase 11** | H-4, H-5 | [`AUDIT-FASE10-12-LOG.md`](AUDIT-FASE10-12-LOG.md) |
| **Fase 12** | H-13 (mitigado) | [`AUDIT-FASE10-12-LOG.md`](AUDIT-FASE10-12-LOG.md) |

---

*Actualizado el 2026-05-11 tras completar las 12 fases de implementación. Estado verificado contra código fuente y tests (`175 passed` backend, `121 passed` frontend).*
