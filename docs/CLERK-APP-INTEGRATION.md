# Integración con Clerk

Guía para conectar Lore Master con Clerk como proveedor de autenticación externo.

> **Última actualización:** 2026-05-15  
> **Estado:** Backend 100% implementado. Frontend 100% implementado. Pendiente: `test_auth_clerk.py`.

---

## Estado actual (2026-05-15)

| Componente | Archivo | Estado |
|---|---|---|
| `JWKSManager` + `decode_clerk_token()` | `core/auth/clerk.py` | ✅ Implementado |
| Settings `clerk_jwks_url` + `clerk_audience` | `core/config/__init__.py` | ✅ Implementado |
| `GET /auth/clerk/verify` | `routes/auth/auth_clerk.py` | ✅ Implementado |
| Cookies HttpOnly + CSRF | `core/auth/` | ✅ Implementado |
| **`POST /auth/clerk/sync`** | `routes/auth/auth_clerk.py` | ✅ Implementado |
| **`get_or_create_clerk_user()`** | `services/auth/auth_service.py` | ✅ Implementado |
| **Bug en `get_current_user`** | `core/auth/dependencies.py` | ✅ Corregido |
| SDK Clerk + `ClerkProvider` + `ClerkBridge` | `frontend/src/App.tsx` | ✅ Implementado |
| `VITE_CLERK_PUBLISHABLE_KEY` | `frontend/.env` + `clerkConfig.ts` | ✅ Implementado |
| `clerkSync.ts` | `frontend/src/api/clerkSync.ts` | ✅ Implementado |
| **`test_auth_clerk.py`** | `backend/tests/test_auth_clerk.py` | ❌ Pendiente |

---

## Parte 1 — Backend

### 1.1 Variables de entorno

Añadir al archivo `backend/.env`:

```dotenv
ENVIRONMENT=production           # o "demo"
CLERK_JWKS_URL=https://<tu-app>.clerk.accounts.dev/.well-known/jwks.json
CLERK_AUDIENCE=<tu-audience>    # normalmente la URL de tu frontend
```

Los valores exactos están en el dashboard de Clerk → **API Keys** y **JWT Templates**.

### 1.2 Flujo de autenticación con cookies

La arquitectura usa un **patrón puente**: el JWT de Clerk nunca se almacena en cookie. En `/sync`, el backend valida el Clerk JWT (que llega por header), crea el usuario local si no existe, y emite un JWT propio que es el que va a la cookie HttpOnly. Todos los requests posteriores usan el JWT local, igual que en entorno `local`.

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────────────────┐
│   Frontend  │────▶│    Clerk     │────▶│           Backend            │
│  (SDK Clerk)│     │  (OAuth/SSO) │     │                              │
└─────────────┘     └──────────────┘     └──────────────────────────────┘
      │                                                │
      │ 1. Usuario inicia sesión en Clerk              │
      │ 2. Clerk devuelve Clerk JWT al frontend        │
      │ 3. Frontend envía Clerk JWT a POST /auth/clerk/sync
      │    (Authorization: Bearer <clerk_jwt>)         │
      │ 4. Backend: decode_clerk_token() valida RS256  │
      │ 5. Backend: get_or_create_clerk_user() crea o  │
      │    encuentra User en BD local                  │
      │ 6. Backend: create_access_token() → JWT local  │
      │ 7. Backend: setea cookies HttpOnly:            │
      │    - access_token (JWT local, firmado con SECRET_KEY)
      │    - csrf_token                                │
      │ 8. Frontend usa cookies automáticamente        │
      │                                                │
      │ [Requests siguientes]                          │
      │ 9. Cookie access_token (JWT local) → get_current_user()
      │    → verify_token() → token válido ✓           │
```

> **Importante:** El Clerk JWT **nunca** se almacena en cookie. Solo llega por header en el paso 3 y se descarta después de la validación. La cookie siempre contiene un JWT local.

### 1.3 ~~Fix necesario en `get_current_user`~~ ✅ Corregido

**Archivo:** `backend/app/core/auth/dependencies.py`

El bug original tenía un branch de producción que llamaba `decode_clerk_token(token)` sobre la cookie `access_token`, lo cual es incorrecto: la cookie siempre contiene un **JWT local** (firmado con `SECRET_KEY`), nunca el Clerk JWT.

El código actual ya es correcto: `get_current_user` usa `verify_token()` en todos los entornos. El Clerk JWT solo llega por header en `/sync` y se descarta tras la validación. `decode_clerk_token` no está importado en `dependencies.py`; se usa únicamente en `auth_clerk.py`.

```python
# Estado actual — correcto:
def get_current_user(request, session):
    token = request.cookies.get(settings.cookie_access_name)
    if not token:
        raise HTTPException(401, "No autorizado")
    payload = verify_token(token)                     # ← siempre JWT local
    user = session.get(User, payload["sub"])
    if not user or user.is_deleted:
        raise HTTPException(401, "No autorizado")
    if not hmac.compare_digest(str(user.token_version), str(payload.get("version", 0))):
        raise HTTPException(401, "Sesión inválida")
    return payload
```

### 1.4 Provisioning de usuarios — `get_or_create_clerk_user` ✅

**Archivo:** `backend/app/services/auth/auth_service.py`

Con Clerk, el usuario existe en el proveedor externo pero **no en la BD local** hasta el primer `/sync`. La función ya está implementada y exportada desde `services/auth/__init__.py`:

```python
def get_or_create_clerk_user(session: Session, payload: dict) -> User:
    """Crea el User local si no existe, retorna el existente si ya está registrado.

    El 'sub' del Clerk JWT (e.g. 'user_2abc...') es el ID primario.
    hashed_password queda vacío porque Clerk maneja las credenciales.
    """
    user_id = payload["sub"]
    user = session.get(User, user_id)
    if user:
        return user

    email = payload.get("email", "")
    username = (
        payload.get("username")
        or (email.split("@")[0] if email else None)
        or user_id
    )
    user = User(
        id=user_id,
        username=username,
        email=email,
        hashed_password="",   # no aplica — Clerk gestiona credenciales
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
```

Exportar desde `backend/app/services/auth/__init__.py`.

> **No usar** `create_user()` existente: hace hash de password y valida unicidad de username contra la BD, incompatible con el flujo Clerk.

### 1.5 Endpoint `POST /auth/clerk/sync` ✅

**Archivo:** `backend/app/api/routes/auth/auth_clerk.py`

```python
from app.api.routes.auth.auth import _set_auth_cookies
from app.core.auth import create_access_token
from app.services.auth import get_or_create_clerk_user

@router.post("/sync")
def sync_clerk_user(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
) -> AuthSuccessResponse:
    """Intercambia un Clerk JWT por una sesión local (cookies HttpOnly).

    El frontend envía el Clerk JWT una sola vez, en el header Authorization.
    El backend valida el token, crea/encuentra el User local,
    y setea las cookies de sesión. Requests posteriores usan las cookies.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No autorizado")

    clerk_token = auth_header.split(" ", 1)[1]
    payload = decode_clerk_token(clerk_token)

    user = get_or_create_clerk_user(session, payload)
    token = create_access_token(
        data={"sub": user.id, "username": user.username, "version": user.token_version}
    )
    _set_auth_cookies(response, token)
    return AuthSuccessResponse(username=user.username)
```

**CSRF:** Automáticamente exento por `main.py` (todos los paths bajo `/api/v1/auth/` están eximidos — el usuario aún no tiene sesión activa al llamar `/sync`).

**Rate limiting:** Cubierto por `RateLimitMiddleware` global (30 req/min).

### 1.6 Tests — `backend/tests/test_auth_clerk.py` ❌ Pendiente

Este es el único ítem faltante. El archivo aún no existe.

| ID | Escenario | Resultado esperado |
|---|---|---|
| CLERK-01 | `POST /sync` sin header Authorization | 401 |
| CLERK-02 | `POST /sync` con token Clerk inválido (mock) | 401 |
| CLERK-03 | `POST /sync` token válido, user nuevo | 200, user creado en BD, cookies seteadas |
| CLERK-04 | `POST /sync` token válido, user ya existe | 200, sin duplicar user (idempotente) |
| CLERK-05 | `GET /auth/clerk/verify` token válido, user en BD | 200 `{valid: True}` |
| CLERK-06 | `GET /auth/clerk/verify` user soft-deleted | 401 |

Patrón: `monkeypatch` de `app.core.auth.clerk.decode_clerk_token` para evitar llamadas reales a Clerk. Usar fixture `auth_client` del `conftest.py` existente.

### 1.7 Redis para token_version (fuera de scope — Fase 2+)

Actualmente `get_current_user` consulta `token_version` en la BD en cada request. Con Redis se puede cachear para eliminar ese hit. No implementar en esta fase.

---

## Parte 2 — Frontend ✅ Implementado

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

`ClerkProvider` debe ir por fuera de `BrowserRouter`. El `AuthProvider` existente puede coexistir inicialmente.

### 2.4 Sincronizar sesión con el backend

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

Después de la sincronización, el backend maneja todo via cookies. `apiClient.ts` ya funciona sin cambios.

### 2.5 Reemplazar `AuthContext` y `ProtectedRoute`

```tsx
// components/ProtectedRoute.tsx
import { useUser } from "@clerk/clerk-react";
import { Navigate, Outlet } from "react-router-dom";

export default function ProtectedRoute() {
  const { isSignedIn, isLoaded } = useUser();
  if (!isLoaded) return null;
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

## Resumen de cambios implementados

### Backend ✅ Completo

| Área | Archivo | Estado |
|---|---|---|
| Config | `backend/.env` + `.env.example` | ✅ `CLERK_JWKS_URL`, `CLERK_AUDIENCE` añadidos |
| Backend (fix) | `core/auth/dependencies.py` | ✅ Branch `production` eliminado; `verify_token()` uniforme |
| Backend | `services/auth/auth_service.py` | ✅ `get_or_create_clerk_user()` implementado |
| Backend | `services/auth/__init__.py` | ✅ `get_or_create_clerk_user` exportado |
| Backend | `routes/auth/auth_clerk.py` | ✅ `POST /auth/clerk/sync` implementado |
| Tests | `tests/test_auth_clerk.py` | ❌ Pendiente (único ítem faltante) |

### Frontend ✅ Completo

| Área | Archivo | Estado |
|---|---|---|
| Config | `frontend/.env` + `clerkConfig.ts` | ✅ `VITE_CLERK_PUBLISHABLE_KEY` configurado |
| SDK | `App.tsx` | ✅ `ClerkProvider` envuelve la app |
| Bridge | `App.tsx` → `ClerkBridge` | ✅ Sincroniza sesión Clerk → backend post-login |
| API | `api/clerkSync.ts` | ✅ `syncClerkSession()` implementado |
| Auth guard | `ProtectedRoute.tsx` | ✅ Usa `VITE_CLERK_PUBLISHABLE_KEY` para Clerk |

---

## Documentos relacionados

- `CLERK.md` — Guía conceptual de alto nivel (3 entornos)
- `AUDIT-SECURITY-REVIEW3-2026-05-12.md` — Issues de seguridad resueltos
- `REVIEW-2026-05-13.md` — Estado del proyecto al 2026-05-13
