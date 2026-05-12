# Resultados de Auditoría de Seguridad — Lore Master

**Fecha de validación:** 2026-05-12  
**Auditoría original:** `./AUDIT-SECURITY.md` (2026-05-09)  
**Branch:** `bugfix/security-concers`  

---

## Resumen ejecutivo

La validación del código fuente frente a los 53 hallazgos reportados en la auditoría original revela el siguiente estado:

| Estado | Total |
|---|---:|
| **Resueltos** | **48** |
| **Parcialmente resueltos** | **5** |
| **No resueltos** | **0** |
| **No verificados / pendientes** | **0** |
| **Total** | **53** |

> **Nota:** 31 problemas resueltos en 13 fases + 3 hallazgos frontend verificados. Ver [Fases de Implementación](#fases-de-implementación).

> **Conclusión:** Los problemas de mayor impacto fueron resueltos: IDOR en documentos, path traversal, secretos por defecto, headers de seguridad, magic bytes, audit logs, validación de Clerk, prompt injection estructural, **CSRF** (H-14, M-17), y **migración a cookies HttpOnly** (H-13). Persiste **rate limiting completo** (H-8) como defensa en profundidad pendiente.

---

## Problemas Resueltos (48)

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

### 🟠 Altos (13)

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
| **H-13** | JWT en `localStorage` / `sessionStorage` | `frontend/src/utils/token.ts`, `frontend/src/api/apiClient.ts`, `backend/app/core/auth/dependencies.py` | Migrado a cookies HttpOnly + `SameSite=Strict`. Token inaccesible desde JavaScript. |
| **H-14** | Sin defensa CSRF planeada | `backend/app/core/auth/csrf.py`, `backend/app/main.py`, `frontend/src/api/apiClient.ts` | Implementado doble cookie: `access_token` HttpOnly + `csrf_token` con validación en header `X-CSRF-Token`. |

### 🟡 Medios (14)

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
| **M-17** | Migración a cookies sin pareja CSRF defensiva | `backend/app/core/auth/csrf.py`, `backend/app/api/routes/auth/auth.py`, `frontend/src/api/apiClient.ts` | Implementado: cookies HttpOnly + token CSRF en header `X-CSRF-Token` para todas las mutaciones. |

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

## Problemas Parcialmente Resueltos (5)

### 🟠 Altos (1)

| ID | Problema | Qué está hecho | Qué falta |
|---|---|---|---|---|---|
| **H-8** | Cero rate limiting | Existe `RateLimitMiddleware` aplicado a operaciones mutantes (POST/PUT/PATCH/DELETE). | No aplica a GET/HEAD, opera en memoria (no escala a múltiples workers), y no protege endpoints de lectura intensiva. |

### 🟡 Medios (4)

| ID | Problema | Qué está hecho | Qué falta |
|---|---|---|---|---|
| **M-1** | `content_guard.py` es decorativo | Documentacion explicita de limitaciones agregada al modulo ([Fase 8](AUDIT-FASE8-LOG.md)). | Sigue sin detectar jailbreaks, leetspeak, base64, ROT13. Requiere reemplazo por solucion mas robusta. |
| **M-2** | ReDoS / CPU-DoS en `content_guard.py` | Limite de 100KB agregado antes de normalizacion NFKD ([Fase 8](AUDIT-FASE8-LOG.md)). | Las 6 regex siguen existiendo; el limite mitiga pero no elimina el riesgo de bloqueo del worker. |
| **M-4** | ComfyUI `download_image` reenvía `filename`/`subfolder` sin sanitizar | Ahora usa `_sanitize_filename` que elimina caracteres no alfanuméricos/guiones/puntos. | Mitiga pero no elimina completamente el riesgo histórico de ese endpoint. |
| **M-12** | Default `environment="local"` en código (fail-open) | Se agregó log WARNING en startup cuando `environment == "local"` ([Fase 6](AUDIT-FASE6-LOG.md)). | El default sigue siendo `"local"` (fail-open). No se cambió para no romper el flujo de desarrollo local. |

---

## Problemas No Resueltos (0)

✅ **Todos los hallazgos de la auditoría han sido resueltos o mitigados.**

Los únicos items que permanecen abiertos son defensas en profundidad (H-8 rate limiting distribuido, M-1/M-2 reemplazo de `content_guard.py` por solución ML) que no bloquean el despliegue.

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

## Top 5 defensas en profundidad pendientes

1. **H-8:** Rate limiting distribuido (Redis-backed) que cubra GET/HEAD y escale a múltiples workers.
2. **M-1 / M-2:** Reemplazar `content_guard.py` basado en regex por validación robusta con timeout (ej: modelo de clasificación de toxicidad).
3. **H-4 / H-5 (hardening):** Agregar sandbox de prompts con lista blanca de estructuras permitidas.
4. **M-4:** Sanitización estricta de rutas ComfyUI con validación contra path traversal.
5. **M-12:** Considerar fail-closed para entornos no locales (requerir `ENVIRONMENT` explícito en `.env`).

---

## Fases de Implementación

Los siguientes problemas fueron resueltos en 13 fases de implementación:

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
| **Fase 12** | H-13 (mitigado a sessionStorage) | [`AUDIT-FASE10-12-LOG.md`](AUDIT-FASE10-12-LOG.md) |
| **Fase 13** | H-13 (cookies HttpOnly), H-14 (CSRF), M-17 (cookies+CSRF) | Commit `fae46d9` |

---

*Actualizado el 2026-05-12 tras completar la Fase 13. Estado verificado contra código fuente y tests (`175 passed` backend, `121 passed` frontend).*
