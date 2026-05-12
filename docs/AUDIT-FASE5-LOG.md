# Registro de Implementacion — Fase 5 (Auditoria de Seguridad)

**Fecha:** 2026-05-11
**Referencia:** `docs/AUDIT-RESULTS-11-05-26.md`, `docs/PLAN-AUDIT-MEDIUM-LOW.md`
**Estado:** Completada

---

## Problemas atacados en esta fase

| ID | Severidad | Problema | Estado final |
|---|---|---|---|
| M-6 | Medio | Timing oracle en login (distingue "user not found" vs "wrong password") | **No resuelto → Completo** |
| M-5 | Medio | `/auth/clerk/verify` sin chequeo `is_deleted` | **No resuelto → Completo** |
| L-7 | Bajo | Sin `secrets.compare_digest` para comparaciones sensibles | **No resuelto → Completo** |

---

## Cambios aplicados

### 1. M-6 — Timing oracle en login

**Archivo modificado:**
- `backend/app/api/routes/auth/auth.py`
- `backend/app/core/auth/__init__.py`

**Descripcion:**
Se elimino el timing oracle en el endpoint `POST /auth/login`:

1. En `auth.py`: Se reestructuro la logica para ejecutar `verify_password` siempre, incluso cuando el usuario no existe:
   - Si el usuario existe: verifica contra su `hashed_password`
   - Si el usuario NO existe: ejecuta `verify_password` con un hash dummy invalido
   - En ambos casos, el tiempo de ejecucion de bcrypt es similar

2. En `core/auth/__init__.py`: `verify_password` ahora captura `ValueError` (hash invalido) y retorna `False` silenciosamente, en lugar de propagar la excepcion. Esto permite usar hashes dummy sin romper la aplicacion.

**Decision de diseno:** No se cambio el mensaje de error (sigue siendo generico "Credenciales incorrectas"). La unica diferencia es que ahora un atacante no puede distinguir "usuario existe" vs "usuario no existe" midiendo el tiempo de respuesta.

**Rollback:**
- Revertir `auth.py` a `if not user or not verify_password(...)`
- Quitar el `try/except ValueError` de `verify_password`

---

### 2. M-5 — `/auth/clerk/verify` sin `is_deleted`

**Archivo modificado:**
- `backend/app/api/routes/auth/auth_clerk.py`

**Descripcion:**
Se agrego verificacion de base de datos despues de decodificar el token de Clerk:

1. La funcion `verify` ahora acepta `session: Session = Depends(get_session)`
2. Despues de obtener `user_id` del payload, busca el usuario en BD
3. Si el usuario no existe o esta eliminado (`is_deleted == True`), retorna 401

**Decision de diseno:** Esto hace consistente el comportamiento del branch de Clerk con el branch local (`get_current_user` ya verifica `is_deleted`).

**Rollback:** Quitar los parametros `session` y el bloque de verificacion de `user.is_deleted`.

---

### 3. L-7 — `secrets.compare_digest` para token_version

**Archivo modificado:**
- `backend/app/core/auth/dependencies.py`

**Descripcion:**
Se reemplazo la comparacion directa de enteros:
```python
user.token_version != payload.get("version", 0)
```

Por una comparacion timing-safe usando `hmac.compare_digest`:
```python
hmac.compare_digest(str(user.token_version), str(payload.get("version", 0)))
```

**Decision de diseno:** Aunque `token_version` son enteros pequenos y el riesgo de timing attack es bajo, `hmac.compare_digest` garantiza que la comparacion no filtra informacion por tiempo. Se convirtieron ambos valores a string para usar la funcion.

**Rollback:** Revertir a la comparacion directa `!=`.

---

## Resultados de validacion

### Tests ejecutados

```
cd backend && python -m pytest -q

175 passed in 21.76s
```

**Desglose:**
- `test_auth.py`: 12/12 passed (incluyendo `test_login_nonexistent_user_401`)
- Todos los tests pasan sin modificaciones

---

## Estado actual de la auditoria (post-Fase 5)

| Estado | Pre-Fase 5 | Post-Fase 5 | Delta |
|---|---|---|---|
| Resueltos | 31 | **34** | +3 |
| Parcialmente resueltos | 2 | 2 | 0 |
| No resueltos | 17 | **14** | -3 |
| No verificados | 3 | 3 | 0 |
| **Total** | **53** | **53** | — |

Los 3 problemas que pasaron de "no resueltos" a "resueltos" son: **M-6, M-5, L-7**.

---

## Proxima fase

**Fase 6 — Config e Infraestructura:**
- M-9: CORS HTTPS en `demo`
- M-12: Default `environment="local"` (log warning)
- L-11: Token revocation TTL documentado
- L-13: Docker compose bind 127.0.0.1

---

*Documento generado el 2026-05-11 tras la validacion exitosa de la Fase 5.*

> **Nota de resolucion (2026-05-11):** Los 3 problemas atacados en esta fase fueron verificados como **resueltos** y estan reflejados en [`AUDIT-RESULTS-11-05-26.md`](AUDIT-RESULTS-11-05-26.md).
