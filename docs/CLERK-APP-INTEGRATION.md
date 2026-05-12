# Integración con Clerk

Guía para conectar Lore Master con Clerk como proveedor de autenticación externo.

> **Última actualización:** 2026-05-12  
> **Estado:** Backend listo (90%). Pendiente: provisioning automático de usuarios, adaptación frontend a cookies, e integración SDK Clerk.

---

## Estado actual

El backend tiene la validación de tokens Clerk implementada:

- `backend/app/api/routes/auth/auth_clerk.py` — valida tokens RS256 descargando las claves JWKS de Clerk. Cache thread-safe con TTL de 1 hora.
- `backend/app/core/auth/dependencies.py` — `get_current_user` delega en `decode_clerk_token` cuando `ENVIRONMENT=production`.
- **Nuevo (Fase 13):** Cookies HttpOnly + CSRF tokens para todas las sesiones.

Lo que falta es el provisioning automático de usuarios Clerk en la BD local, y la adaptación del frontend al SDK de Clerk manteniendo el sistema de cookies.

---

## Parte 1 — Backend

### 1.1 Variables de entorno

Añadir al archivo `backend/.env`:

```dotenv
ENVIRONMENT=production
CLERK_JWKS_URL=https://<tu-app>.clerk.accounts.dev/.well-known/jwks.json
CLERK_AUDIENCE=<tu-audience>    # normalmente la URL de tu frontend
```

Los valores exactos están en el dashboard de Clerk → **API Keys** y **JWT Templates**.

### 1.2 Flujo de autenticación con cookies

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend  │────▶│    Clerk     │────▶│   Backend    │
│  (SDK Clerk)│     │  (OAuth/SSO) │     │ (cookies)    │
└─────────────┘     └──────────────┘     └──────────────┘
      │                                          │
      │ 1. Usuario inicia sesión en Clerk        │
      │ 2. Clerk redirige con JWT                │
      │ 3. Frontend envía JWT a /auth/clerk/sync │
      │ 4. Backend valida JWT con decode_clerk_token()
      │ 5. Backend crea/actualiza User local       │
      │ 6. Backend setea cookies HttpOnly:         │
      │    - access_token (JWT propio)             │
      │    - csrf_token                            │
      │ 7. Frontend usa cookies automáticamente    │
```

### 1.3 Provisioning de usuarios (gap principal)

Con JWT local, el backend crea el `User` en la BD en el momento del registro. Con Clerk, el usuario se crea en Clerk pero **no existe en la BD local** hasta que se sincroniza explícitamente.

Esto rompe los endpoints que consultan `User` por `sub`:

| Endpoint | Síntoma |
|---|---|
| `GET /users/me` | `session.get(User, "user_2abc...")` → 404 |
| `POST /collections/` | Crea colección con `owner_id` sin FK válida en `users` |
| `GET /admin/users/*` | No encuentra el User del admin → 403 |

**Solución: endpoint `/auth/clerk/sync` + `get_or_create_user`**

Añadir en `backend/app/api/routes/auth/auth_clerk.py`:

```python
@router.post("/sync")
def sync_clerk_user(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    """Sincroniza un usuario Clerk con la BD local y setea cookies.

    El frontend envía el JWT de Clerk en el header Authorization.
    El backend valida el token, crea/actualiza el usuario local,
    genera un JWT propio, y setea cookies HttpOnly + CSRF.
    """
    # Leer token Clerk del header (único momento que usamos header)
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Token requerido")

    clerk_token = auth.split(" ", 1)[1]
    payload = decode_clerk_token(clerk_token)
    user_id = payload.get("sub")

    # Crear o actualizar usuario local
    user = session.get(User, user_id)
    if not user:
        user = User(
            id=user_id,
            username=payload.get("username") or payload.get("email") or user_id,
            email=payload.get("email", ""),
            hashed_password="",  # no aplica en modo Clerk
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    # Generar JWT propio y setear cookies
    token = create_access_token(
        data={
            "sub": user.id,
            "username": user.username,
            "version": user.token_version,
        }
    )
    _set_auth_cookies(response, token)  # Reutilizar función de auth.py
    return {"username": user.username}
```

También crear la dependencia `get_or_create_user`:

```python
# backend/app/core/auth/dependencies.py

def get_or_create_user(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> User:
    user = session.get(User, current_user["sub"])
    if not user:
        user = User(
            id=current_user["sub"],
            username=current_user.get("username") or current_user["sub"],
            hashed_password="",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    return user
```

Sustituir `Depends(get_current_user)` por `Depends(get_or_create_user)` en rutas que necesitan el registro local: `POST /collections/`, `GET /users/me`, `PATCH /users/me`, y endpoints `/admin/*`.

### 1.4 Issue #36 — RESUELTO

> **Estado:** ✅ Resuelto en refactorización previa.  
> La función `get_collection_or_404_public_or_owned` ya no existe. Todas las dependencias de colecciones/entidades/documentos usan `get_current_user` vía `Depends` consistentemente.

### 1.5 Redis para token_version (opcional, Fase 2+)

Actualmente `get_current_user` consulta `token_version` en la BD en cada request (1 query extra). Con Redis se puede eliminar este hit:

```python
# backend/app/core/auth/redis_cache.py (nuevo)
import redis
from app.core.config import settings

redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

def get_token_version(user_id: str, session: Session) -> int:
    cached = redis_client.get(f"token_version:{user_id}")
    if cached is not None:
        return int(cached)
    user = session.get(User, user_id)
    if user:
        redis_client.setex(f"token_version:{user_id}", 3600, user.token_version)
        return user.token_version
    return -1

def invalidate_token_version(user_id: str) -> None:
    redis_client.delete(f"token_version:{user_id}")
```

**Logout con Redis:**
```python
# En endpoint /auth/logout
user.token_version += 1
session.add(user)
session.commit()
invalidate_token_version(user.id)  # Invalidar cache
_clear_auth_cookies(response)
```

**Requisitos:**
```bash
pip install redis
```

**Configuración:**
```env
REDIS_URL=redis://localhost:6379/0
```

---

## Parte 2 — Frontend

### 2.1 Instalar el SDK

```bash
cd frontend
npm install @clerk/clerk-react
```

### 2.2 Variable de entorno

Añadir a `frontend/.env`:

```dotenv
VITE_CLERK_PUBLISHABLE_KEY=pk_live_...   # o pk_test_... en dev
```

El valor está en el dashboard de Clerk → **API Keys**.

### 2.3 Envolver la app con `ClerkProvider`

**`frontend/src/main.tsx`**

```tsx
import { ClerkProvider } from "@clerk/clerk-react";

const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ClerkProvider publishableKey={publishableKey}>
      <App />
    </ClerkProvider>
  </StrictMode>
);
```

`ClerkProvider` debe ir por fuera de `BrowserRouter`. El `AuthProvider` existente puede coexistir inicialmente, pero idealmente se migra a usar el estado de Clerk.

### 2.4 Sincronizar sesión con el backend

Con Clerk el token se obtiene de forma asíncrona con `useAuth().getToken()`. Pero **no enviamos el token en cada request** — solo en el momento de sincronización:

```tsx
// frontend/src/api/clerkSync.ts
import { apiFetch } from "./apiClient";

export async function syncClerkSession(clerkToken: string) {
  return apiFetch("/auth/clerk/sync", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${clerkToken}`,
    },
  });
}
```

Llamar una sola vez después del login:

```tsx
// App.tsx o un hook de inicialización
import { useAuth } from "@clerk/clerk-react";
import { syncClerkSession } from "./api/clerkSync";
import { useEffect } from "react";

export function useClerkSync() {
  const { getToken, isSignedIn } = useAuth();

  useEffect(() => {
    if (isSignedIn) {
      getToken().then((token) => {
        if (token) syncClerkSession(token);
      });
    }
  }, [isSignedIn]);
}
```

Después de la sincronización, el backend maneja todo via cookies. El `apiClient.ts` existente ya funciona sin cambios (lee cookies automáticamente y envía CSRF en mutaciones).

### 2.5 Reemplazar `AuthContext` y `ProtectedRoute`

Con Clerk el estado de sesión lo provee el propio SDK:

```tsx
// components/ProtectedRoute.tsx
import { useUser } from "@clerk/clerk-react";
import { Navigate, Outlet } from "react-router-dom";

export default function ProtectedRoute() {
  const { isSignedIn, isLoaded } = useUser();
  if (!isLoaded) return null;                    // evita flash de login
  if (!isSignedIn) return <Navigate to="/login" replace />;
  return <Outlet />;
}
```

```tsx
// pages/LoginPage.tsx — reemplazar el formulario manual
import { SignIn } from "@clerk/clerk-react";

export default function LoginPage() {
  return (
    <div className="d-flex justify-content-center align-items-center vh-100">
      <SignIn routing="hash" />
    </div>
  );
}
```

`Layout.tsx` puede mostrar el username con `useUser().user?.username` y el botón de logout con `useClerk().signOut()`.

**Logout:**
```tsx
import { useClerk } from "@clerk/clerk-react";

function LogoutButton() {
  const { signOut } = useClerk();

  const handleLogout = async () => {
    await fetch("/api/v1/auth/logout", { method: "POST", credentials: "include" });
    await signOut();
  };

  return <button onClick={handleLogout}>Cerrar sesión</button>;
}
```

---

## Resumen de cambios

| Área | Archivo | Acción |
|---|---|---|
| Config | `backend/.env` | Añadir `ENVIRONMENT`, `CLERK_JWKS_URL`, `CLERK_AUDIENCE` |
| Backend | `app/api/routes/auth/auth_clerk.py` | Añadir endpoint `/auth/clerk/sync` |
| Backend | `app/core/auth/dependencies.py` | Añadir `get_or_create_user` |
| Backend | Rutas que usan User local | Cambiar `Depends(get_current_user)` → `Depends(get_or_create_user)` |
| Backend (opt) | `app/core/auth/redis_cache.py` | Cache de `token_version` con Redis |
| Config | `frontend/.env` | Añadir `VITE_CLERK_PUBLISHABLE_KEY` |
| Frontend | `main.tsx` | Envolver con `ClerkProvider` |
| Frontend | `api/clerkSync.ts` | Crear función para sincronizar sesión |
| Frontend | `App.tsx` | Llamar `syncClerkSession` post-login |
| Frontend | `ProtectedRoute.tsx` | Usar `useUser()` de Clerk |
| Frontend | `LoginPage.tsx` | Reemplazar formulario manual con `<SignIn>` |
| Frontend | `Layout.tsx` | Usar `useUser()` / `useClerk().signOut()` |

**Complejidad total estimada:** 1–2 días de trabajo.

---

## Documentos relacionados

- `CLERK.md` — Guía conceptual de alto nivel
- `PLAN-COOKIES-CSRF.md` — Diseño del sistema de cookies HttpOnly + CSRF
- `AUDIT-RESULTS-11-05-26.md` — Estado del audit de seguridad
