# Plan de Implementacion — Problemas Medios y Bajos Pendientes

**Fecha:** 2026-05-11
**Referencia:** `./AUDIT-RESULTS-11-05-26.md`
**Estrategia:** Igual que fases anteriores: agrupar por dominio, cambios minimos, test suite completo despues de cada fase, documentar en log.

---

## Resumen de pendientes (Medios + Bajos)

| ID | Severidad | Problema | Riesgo |
|---|---|---|---|
| **M-5** | Medio | `/auth/clerk/verify` sin chequeo `is_deleted` | Inconsistencia con branch local; usuarios eliminados pueden autenticarse |
| **M-6** | Medio | Timing oracle en login | Distingue "user not found" vs "wrong password" por tiempo de respuesta |
| **M-9** | Medio | CORS no exige HTTPS en `demo` | Solo valida en `production`; `demo` queda sin validacion |
| **M-12** | Medio | Default `environment="local"` | Fail-open: olvidar setear `production` desactiva todas las guardas |
| **M-3** | Medio | `edit_content` NO ejecuta `check_user_input` | Prompt injection via contenido confirmado editable |
| **M-1** | Medio | `content_guard.py` decorativo | 6 regex minimas; no detecta jailbreaks, leetspeak, base64, ROT13 |
| **M-2** | Medio | ReDoS / CPU-DoS en `content_guard.py` | Worker bloqueado aplicando regex sobre archivos de hasta 50MB normalizados con NFKD |
| **L-7** | Bajo | Sin `secrets.compare_digest` | Comparaciones de strings sensibles no usan timing-safe comparison |
| **L-11** | Bajo | Token revocation TTL no documentado | `token_version` existe pero sin politica formal |
| **L-13** | Bajo | Docker compose expone Qdrant 6333 y Redis 6379 | Exposicion de servicios internos en desarrollo |

**Descartados de este plan:**
- **M-17** (migracion a cookies sin CSRF): Requiere cambio arquitectonico mayor (frontend + backend). Se deja para plan separado.
- **M-16, L-9, L-10** (frontend): Requieren revision de codigo frontend, fuera del scope de estas fases.

---

## Fase 5 — Auth Hardening (M-5, M-6, L-7)

**Objetivo:** Eliminar timing oracle en login, consistencia en verificacion de Clerk, y comparaciones timing-safe.

### 5.1 M-6 — Timing oracle en login
**Archivo:** `backend/app/api/routes/auth/auth.py`
**Problema:** El endpoint distingue "user not found" (respuesta rapida) vs "wrong password" (bcrypt lento).
**Fix:** Agregar dummy bcrypt para usuarios inexistentes:
```python
# Si el usuario no existe, ejecutar bcrypt.verify con un hash dummy
# para mantener tiempo constante
```
**Consideracion:** No cambiar mensaje de error (sigue siendo generico). Solo igualar el tiempo de respuesta.

### 5.2 M-5 — `/auth/clerk/verify` sin `is_deleted`
**Archivo:** `backend/app/api/routes/auth/auth_clerk.py`
**Problema:** Decodifica JWT de Clerk y devuelve `user_id` sin verificar si el usuario esta eliminado.
**Fix:** Agregar lookup de BD despues de obtener `user_id` del token de Clerk:
```python
user = session.get(User, user_id)
if not user or user.is_deleted:
    raise HTTPException(status_code=401, detail="Usuario no encontrado")
```

### 5.3 L-7 — `secrets.compare_digest`
**Archivo:** Revisar `backend/app/core/auth/__init__.py`, `backend/app/api/routes/auth/auth.py`
**Problema:** Comparaciones de strings sensibles (tokens, versiones) no usan `hmac.compare_digest` o `secrets.compare_digest`.
**Fix:** Identificar comparaciones de strings sensibles y reemplazar por `secrets.compare_digest`.

**Validacion:** `175 passed` despues de cambios.

---

## Fase 6 — Config e Infraestructura (M-9, M-12, L-11, L-13)

**Objetivo:** Cerrar gaps de configuracion y documentar politicas.

### 6.1 M-9 — CORS HTTPS en `demo`
**Archivo:** `backend/app/core/config/__init__.py`
**Problema:** Solo valida HTTPS en `production`; `demo` queda sin validacion.
**Fix:** Extender validacion a `demo`:
```python
if self.environment in ("production", "demo"):
```

### 6.2 M-12 — Default `environment="local"`
**Archivo:** `backend/app/core/config/__init__.py`
**Problema:** `environment: str = "local"` es fail-open.
**Fix:** Agregar `WARNING` log en startup si `environment == "local"` y no es entorno de test. No cambiar el default para no romper desarrollo local, pero hacer visible el riesgo.
**Decision:** No cambiar el valor default (romperia DX), pero agregar log de advertencia en startup.

### 6.3 L-11 — Token revocation TTL documentado
**Archivo:** `backend/app/core/auth/__init__.py` o `backend/app/models/db/user.py`
**Problema:** `token_version` existe pero sin politica de TTL formal.
**Fix:** Agregar docstring/documentacion que explique:
- Como funciona token_version
- Que hacer cuando se revoca un token (incrementar version)
- Recomendacion de TTL (ej. tokens de 24h, refresh de 7 dias)

### 6.4 L-13 — Docker compose expone servicios internos
**Archivo:** `backend/docker-compose.yml`
**Problema:** Qdrant 6333 y Redis 6379 expuestos al host sin bind a 127.0.0.1.
**Fix:** Agregar bind a `127.0.0.1` para Qdrant y Redis en `docker-compose.yml` (desarrollo). En produccion ya esta cubierto por `docker-compose.prod.yml`.

**Validacion:** `175 passed` despues de cambios.

---

## Fase 7 — Content/Entity Hardening (M-3, L-3)

**Objetivo:** Prevenir prompt injection via contenido editable y eliminar race condition en borrado de archivos.

### 7.1 M-3 — `edit_content` sin `check_user_input`
**Archivo:** `backend/app/services/entity/content_service.py`
**Problema:** `edit_content` NO ejecuta `check_user_input` sobre el nuevo texto antes de guardarlo.
**Fix:** Importar y llamar `check_user_input` en `edit_content` antes de persistir cambios.

### 7.2 L-3 — TOCTOU en `delete_image_service`
**Archivo:** `backend/app/services/image/image_generation_service.py`
**Problema:** `if os.path.exists(full_path): os.remove(full_path)` es vulnerable a race condition.
**Fix:** Reemplazar por `try/except FileNotFoundError`:
```python
try:
    os.remove(full_path)
except FileNotFoundError:
    pass
```

**Validacion:** `175 passed` despues de cambios.

---

## Fase 8 — Content Guard & ReDoS (M-1, M-2)

**Objetivo:** Mitigar ReDoS y documentar limitaciones de content_guard.

### 8.1 M-2 — ReDoS / CPU-DoS
**Archivo:** `backend/app/domain/content_guard.py`
**Problema:** 6 regex sobre texto normalizado de hasta 50MB con NFKD.
**Fix:** 
1. Agregar limite de longitud antes de normalizar (ej. max 100KB para guard)
2. Agregar timeout simple con `signal` o documentar que es first-line defense

### 8.2 M-1 — `content_guard.py` decorativo
**Archivo:** `backend/app/domain/content_guard.py`
**Problema:** 6 regex en denylist minima; no detecta jailbreaks, leetspeak, base64, ROT13.
**Fix:** Agregar docstring que documente explicitamente las limitaciones y recomiende usar como primera linea de defensa, no como unica barrera.

**Validacion:** `175 passed` despues de cambios.

---

## Orden de ejecucion

1. **Fase 5** (Auth) — Mayor impacto de seguridad
2. **Fase 6** (Config) — Cambios de configuracion seguros
3. **Fase 7** (Content/Entity) — Logica de negocio
4. **Fase 8** (Content Guard) — Documentacion + limites

---

## Criterios de exito por fase

- [ ] Todos los cambios son minimos y no alteran interfaces publicas
- [ ] `python -m pytest -q` pasa `175 passed`
- [ ] Se crea `AUDIT-FASE{X}-LOG.md` con los cambios aplicados
- [ ] Se actualiza `AUDIT-RESULTS-11-05-26.md` moviendo los hallazgos a "Resueltos"

---

*Plan generado el 2026-05-11. Pendientes de aprobacion antes de iniciar implementacion.*
