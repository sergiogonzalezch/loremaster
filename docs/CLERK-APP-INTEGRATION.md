# Integración con Clerk

Guía para conectar Lore Master con Clerk como proveedor de autenticación externo.

---

## Estado actual

El backend ya tiene el 80 % de la integración implementada:

- `backend/app/api/routes/auth_clerk.py` — valida tokens RS256 descargando las claves JWKS de Clerk. Cache thread-safe con TTL de 1 hora.
- `backend/app/core/auth_deps.py` — `get_current_user` delega en `decode_clerk_token` cuando `ENVIRONMENT=production`.

Lo que falta es el provisioning de usuarios, una corrección en un dependency, y el SDK en el frontend.

---

## Parte 1 — Backend

### 1.1 Variables de entorno

Añadir al archivo `backend/.env`:

```dotenv
ENVIRONMENT=production
CLERK_JWKS_URL=https://<tu-app>.clerk.accounts.dev/.well-known/jwks.json
CLERK_AUDIENCE=<tu-audience>    # normalmente la URL de tu frontend, ej. https://loremaster.app
```

Los valores exactos están en el dashboard de Clerk → **API Keys** y **JWT Templates**.

### 1.2 Provisioning de usuarios (gap principal)

Con JWT local, el backend crea el `User` en la BD en el momento del registro y su `id` coincide con el `sub` del token. Con Clerk, el `sub` del token es el ID de Clerk (`user_2abc...`) y no existe ningún registro `User` local con ese ID.

Esto rompe silenciosamente los siguientes endpoints la primera vez que un usuario Clerk los llama:

| Endpoint | Síntoma |
|---|---|
| `GET /users/me` | `session.get(User, "user_2abc...")` → 404 |
| `POST /collections/` | Crea la colección con `owner_id` sin FK válida en `users` |
| `GET /admin/users/*` | No encuentra el User del admin → 403 |

**Solución: dependencia `get_or_create_user`**

Añadir en `backend/app/core/auth_deps.py`:

```python
from app.models.users import User

def get_or_create_user(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> User:
    user = session.get(User, current_user["sub"])
    if not user:
        user = User(
            id=current_user["sub"],
            username=current_user.get("username") or current_user["sub"],
            hashed_password="",             # no aplica en modo Clerk
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    return user
```

Sustituir `Depends(get_current_user)` por `Depends(get_or_create_user)` en las rutas que necesitan el registro local: `POST /collections/`, `GET /users/me`, `PATCH /users/me`, y los endpoints `/admin/*`.

### 1.3 Corregir issue #36 (`deps.py`)

`get_collection_or_404_public_or_owned` llama `verify_token` directamente (HS256 local) en vez de pasar por `get_current_user`. Un usuario Clerk que intente acceder a su colección privada recibiría 403.

**Archivo:** `backend/app/core/deps.py`

Reemplazar la lógica manual de verificación de credenciales por una dependencia opcional que use `get_current_user`:

```python
from typing import Optional

def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Optional[dict]:
    if not credentials:
        return None
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None


def get_collection_or_404_public_or_owned(
    collection_id: str,
    current_user: Optional[dict] = Depends(get_optional_current_user),
    session: Session = Depends(get_session),
) -> Collection:
    collection = session.get(Collection, collection_id)
    if not collection or collection.is_deleted:
        raise HTTPException(status_code=404, detail="Colección no encontrada.")
    if collection.is_public:
        return collection
    if current_user and collection.owner_id == current_user["sub"]:
        return collection
    raise HTTPException(status_code=403, detail="Acceso denegado.")
```

Con este cambio, Clerk tokens y JWT locales funcionan igual en el path de colecciones públicas/propias.

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

`ClerkProvider` debe ir por fuera de `BrowserRouter` y `AuthProvider`. Una vez hecho esto, `AuthProvider` puede eliminarse o coexistir delegando en Clerk.

### 2.4 Pasar el token Clerk al `apiClient`

El `apiClient` actual lee el token de `localStorage` via `getToken()`. Con Clerk el token se obtiene de forma asíncrona con `useAuth().getToken()`.

La forma más limpia es exponer una función de token inyectable en el cliente:

**`frontend/src/api/client.ts`**

```ts
let tokenProvider: (() => Promise<string | null>) | null = null;

export function setTokenProvider(fn: () => Promise<string | null>) {
  tokenProvider = fn;
}

export async function apiClient(path: string, options: RequestInit = {}) {
  const token = tokenProvider ? await tokenProvider() : getToken();
  return fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
}
```

Registrar el provider en `App.tsx` una sola vez:

```tsx
import { useAuth } from "@clerk/clerk-react";
import { setTokenProvider } from "./api/client";

export default function App() {
  const { getToken } = useAuth();
  setTokenProvider(() => getToken());
  // ...
}
```

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

`AuthProvider` y `AuthContext` dejan de ser necesarios; `useAuth.ts` puede reexportar `useUser` de Clerk o eliminarse.

---

## Resumen de cambios

| Área | Archivo | Acción |
|---|---|---|
| Config | `backend/.env` | Añadir `ENVIRONMENT`, `CLERK_JWKS_URL`, `CLERK_AUDIENCE` |
| Backend | `app/core/auth_deps.py` | Añadir `get_or_create_user` y `get_optional_current_user` |
| Backend | `app/core/deps.py` | Corregir `get_collection_or_404_public_or_owned` (issue #36) |
| Backend | Rutas que usan User local | Cambiar `Depends(get_current_user)` → `Depends(get_or_create_user)` |
| Config | `frontend/.env` | Añadir `VITE_CLERK_PUBLISHABLE_KEY` |
| Frontend | `main.tsx` | Envolver con `ClerkProvider` |
| Frontend | `api/client.ts` | Añadir `setTokenProvider` para tokens asíncronos |
| Frontend | `App.tsx` | Registrar `tokenProvider` con `getToken` de Clerk |
| Frontend | `ProtectedRoute.tsx` | Usar `useUser()` de Clerk |
| Frontend | `LoginPage.tsx` | Reemplazar formulario manual con `<SignIn>` |
| Frontend | `Layout.tsx` | Usar `useUser()` / `useClerk().signOut()` |
| Frontend | `AuthContext.tsx`, `useAuth.ts` | Eliminar o delegar en Clerk SDK |

**Complejidad total estimada:** 1–2 días de trabajo.
