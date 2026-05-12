# AUTH-FIX — Plan de corrección de gestión de sesiones

Fecha de análisis: 2026-05-08  
Branch en curso: `feature/user-profile`  
Estado: **Pendiente de implementación**

---

## Contexto y problemas identificados

### P1 — Token expirado no cierra la sesión (frontend)

**Archivos afectados:**
- `frontend/src/contexts/AuthContext.tsx:34-37`
- `frontend/src/utils/token.ts:15-17`

**Causa:** `decodeUser()` extrae `sub`, `username` e `is_admin` del payload JWT pero ignora el campo `exp`. Al recargar la app, si existe un token en `localStorage` — aunque esté expirado — el usuario aparece como autenticado. `ProtectedRoute` solo evalúa `if (!user)`, por lo que pasa sin problemas. La sesión solo se cierra de forma **reactiva** cuando una llamada API devuelve 401 (`apiClient.ts:62-66`). Si el usuario no interactúa con el API, la sesión nunca se cierra sola.

---

### P2 — Reinicio del servidor no invalida sesiones + no hay logout real en servidor

**Archivos afectados:**
- `backend/app/core/auth.py`
- `backend/app/core/auth_deps.py`
- `backend/app/api/routes/auth.py`

**Causa:** JWT es stateless. No existe endpoint `/auth/logout` en el backend; el logout actual borra solo el token del `localStorage` del browser. Si alguien tiene una copia del token, sigue siendo válido hasta su expiración. Al reiniciar el servidor, la misma `SECRET_KEY` se carga desde `.env`, por lo que todos los tokens firmados antes siguen siendo criptográficamente válidos.

---

### P3 — Problemas de configuración

| Ubicación | Problema | Severidad |
|-----------|----------|-----------|
| `backend/app/core/config.py:50` | `secret_key = "your-secret-key"` como valor por defecto | Crítica |
| `backend/app/core/config.py:52` | `access_token_expire_minutes = 1440` (24 horas) | Alta |

---

## Diseño de la solución

### Fase 1 — Sin Redis (implementar ahora)

#### 1a. Frontend: validación proactiva de expiración

**Archivo:** `frontend/src/contexts/AuthContext.tsx`

Dos capas de protección:

1. **En el `useState` lazy initializer:** al leer el token de `localStorage`, decodificar el payload y comprobar el campo `exp` contra `Date.now() / 1000`. Si expiró, limpiar `localStorage` y devolver `null`.

2. **En un `useEffect`:** calcular los milisegundos restantes hasta `exp * 1000` y programar un `setTimeout` que llame a `logout()`. Si el usuario renueva sesión (nuevo login), cancelar el timer anterior con `clearTimeout`. Esto garantiza que el cierre de sesión ocurre en el momento exacto sin depender de una llamada API.

```
init:
  token → decode → exp < now? → clear + null
                              → set user + schedule auto-logout

auto-logout timer:
  setTimeout(logout, (exp * 1000) - Date.now())
```

**No requiere cambios en el backend.**

---

#### 1b. Backend: campo `token_version` en el modelo `User`

**Archivo:** `backend/app/models/users.py`

Añadir campo:
```python
token_version: int = SQLField(default=0)
```

Migración Alembic requerida:
```
alembic revision --autogenerate -m "add token_version to users"
alembic upgrade head
```

---

#### 1c. Backend: incluir `version` en el JWT

**Archivo:** `backend/app/api/routes/auth.py`

Al crear el token en `/auth/login` y `/auth/register`, añadir `version` al payload:
```python
data={"sub": user.id, "username": user.username, "is_admin": user.is_admin, "version": user.token_version}
```

---

#### 1d. Backend: verificar versión en `get_current_user`

**Archivo:** `backend/app/core/auth_deps.py`

Tras verificar la firma JWT, consultar el usuario en DB y comparar versiones:
```python
user = session.get(User, payload["sub"])
if not user or user.is_deleted or user.token_version != payload.get("version"):
    raise HTTPException(status_code=401, detail="Sesión inválida")
```

Esto implica **1 query extra a DB por request protegido**. Es el coste sin Redis. Cuando Redis esté disponible, se cachea `token_version` por `user_id` y el hit a DB desaparece (ver Fase 2).

---

#### 1e. Backend: endpoint `/auth/logout`

**Archivo:** `backend/app/api/routes/auth.py`

```
POST /auth/logout
  → incrementa user.token_version en DB
  → todos los tokens previos del usuario quedan inválidos
```

El frontend llama a este endpoint antes de limpiar el `localStorage`.

---

#### 1f. Config: validaciones de seguridad

**Archivo:** `backend/app/core/config.py`

1. Validador que falle si `secret_key == "your-secret-key"` y `environment != "local"`.
2. Reducir `access_token_expire_minutes` de `1440` a `60`.

---

### Fase 2 — Con Redis (en 1-2 semanas)

#### Objetivo: eliminar el hit a DB por request

La función que resuelve `token_version` se abstrae para que el cambio sea transparente al resto del código:

```python
# Hoy (Fase 1) — lee de DB
def get_token_version(user_id: str, session: Session) -> int:
    user = session.get(User, user_id)
    return user.token_version if user else -1

# Mañana (Fase 2) — lee de Redis con fallback a DB
def get_token_version(user_id: str, session: Session) -> int:
    cached = redis_client.get(f"token_version:{user_id}")
    if cached is not None:
        return int(cached)
    user = session.get(User, user_id)
    if user:
        redis_client.setex(f"token_version:{user_id}", ttl=3600, value=user.token_version)
        return user.token_version
    return -1
```

**El endpoint `/auth/logout` en Fase 2:**
1. Incrementa `token_version` en DB.
2. Invalida la entrada en Redis: `redis_client.delete(f"token_version:{user_id}")`.

Con esto, el flujo de una request normal nunca toca la DB para verificar la sesión.

---

#### Preparación para refresh tokens (opcional, Fase 2+)

Si en el futuro se quieren access tokens de vida muy corta (5-15 min) con renovación silenciosa:

- **Access token:** corto (15 min), contiene `sub`, `version`, `exp`.
- **Refresh token:** largo (7 días), opaco, almacenado en Redis con clave `refresh:{jti}` → `user_id`.
- Endpoint `POST /auth/refresh`: valida el refresh token en Redis, emite nuevo access token.
- El logout invalida también el refresh token en Redis.

Este diseño es compatible con la infraestructura de `token_version` ya implementada en Fase 1.

---

## Orden de implementación recomendado

```
1. Config: reducir lifetime + validador de secret_key          (5 min)
2. Frontend: validar exp en AuthContext + auto-logout timer     (30 min)
3. Migration: token_version en User                            (10 min)
4. Backend: version en JWT payload (login + register)          (5 min)
5. Backend: verificar version en get_current_user              (15 min)
6. Backend: endpoint /auth/logout                              (15 min)
7. Frontend: llamar /auth/logout antes de limpiar localStorage (10 min)
--- Hasta aquí sin Redis ---
8. Cuando Redis esté disponible: abstraer get_token_version    (30 min)
```

---

## Archivos a modificar (resumen)

| Archivo | Cambio |
|---------|--------|
| `backend/app/core/config.py` | Validador secret_key + reducir lifetime |
| `backend/app/models/users.py` | Campo `token_version` |
| `backend/app/api/routes/auth.py` | `version` en payload + endpoint `/logout` |
| `backend/app/core/auth_deps.py` | Verificar `version` en cada request |
| `frontend/src/contexts/AuthContext.tsx` | Validar `exp` + auto-logout timer |

Nueva migración Alembic para `token_version`.
