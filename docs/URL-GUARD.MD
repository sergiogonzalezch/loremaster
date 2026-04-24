# Plan: Protección de URLs en Lore Master (Autenticación JWT)

## Contexto

El frontend actualmente es accesible sin ningún tipo de autenticación. Cualquier persona con acceso a la red puede navegar a cualquier ruta y consumir la API. La protección consiste en añadir un único usuario de sistema (single-user local-first) con autenticación JWT stateless: el backend valida un token en cada request, el frontend guarda el token en memoria (no cookie httpOnly por simplicidad local) y redirige a login cuando falta o expira.

---

## Arquitectura del flujo

```
[LoginPage]
    │  POST /api/v1/auth/token  {username, password}
    ▼
[Backend: POST /auth/token]
    │  valida contra AUTH_USERNAME + AUTH_PASSWORD_HASH (bcrypt)
    │  genera JWT (python-jose)  →  {access_token, token_type}
    ▼
[AuthContext]  ──  guarda token en memoria (+ localStorage como cache)
    │
    ▼
[ProtectedRoute]  ──  si no hay token → redirect /login
    │
    ▼
[apiClient]  ──  inyecta  Authorization: Bearer <token>  en cada request
    │              si recibe 401 → limpia token → redirect /login
    ▼
[Backend: cualquier ruta /api/v1/*]
    │  Depends(get_current_user)  →  decodifica JWT, valida expiración
    └─ 401 si inválido / expirado
```

---

## Capa Backend

### Nuevas dependencias Python

```
python-jose[cryptography]
passlib[bcrypt]
```

Añadir a `backend/requirements.txt`.

### Variables de entorno — `app/core/config.py`

```python
# Auth
auth_username: str = Field(default="admin")
auth_password_hash: str = Field(default="")   # bcrypt hash
jwt_secret: str = Field(default="change-me-in-production")
jwt_expire_minutes: int = Field(default=60)
```

Añadir a `backend/.env.example`:

```
# Auth
AUTH_USERNAME=admin
AUTH_PASSWORD_HASH=       # generar con: python -c "from passlib.hash import bcrypt; print(bcrypt.hash('tu_password'))"
JWT_SECRET=change-me-in-production
JWT_EXPIRE_MINUTES=60
```

### Nuevo módulo `app/core/auth.py`

Responsabilidad única: crear y verificar tokens JWT.

```python
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.hash import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.verify(plain, hashed)

def create_access_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": settings.auth_username, "exp": expire},
        settings.jwt_secret,
        algorithm="HS256",
    )

def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exc
        return username
    except JWTError:
        raise credentials_exc
```

### Nueva ruta `app/api/routes/auth.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.core.auth import verify_password, create_access_token
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username != settings.auth_username or \
       not verify_password(form_data.password, settings.auth_password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(), token_type="bearer")
```

### Registro en `app/main.py`

1. Importar y registrar `auth_router` **sin** dependencia JWT (es el endpoint público).
2. Aplicar `Depends(get_current_user)` como dependencia global a todos los routers de `/api/v1/` existentes.

```python
from app.core.auth import get_current_user
from app.api.routes.auth import router as auth_router

# Router público (sin JWT)
app.include_router(auth_router, prefix="/api/v1")

# Routers protegidos (con JWT global)
app.include_router(
    collections_router,
    prefix="/api/v1",
    dependencies=[Depends(get_current_user)],
)
# ... mismo patrón para entities, documents, entity_content, rag_query
```

---

## Capa Frontend

### `src/context/AuthContext.tsx` — Nuevo

Estado global de autenticación. Guarda el token en `localStorage` como caché entre recargas (el token sigue siendo stateless; si expira, el backend rechaza con 401).

```tsx
import { createContext, useContext, useState, useCallback } from "react";

interface AuthCtx {
  token: string | null;
  login: (token: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(
    () => localStorage.getItem("lm_token"),
  );

  const login = useCallback((t: string) => {
    localStorage.setItem("lm_token", t);
    setToken(t);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("lm_token");
    setToken(null);
  }, []);

  return (
    <AuthContext.Provider value={{ token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
```

### `src/pages/LoginPage.tsx` — Nuevo

Formulario mínimo: username + password. Llama a `POST /api/v1/auth/token` con `application/x-www-form-urlencoded` (requerido por OAuth2PasswordRequestForm).

```tsx
import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Form, Button, Card, Alert } from "react-bootstrap";
import { useAuth } from "../context/AuthContext";
import { loginUser } from "../api";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const { access_token } = await loginUser(username, password);
      login(access_token);
      navigate("/");
    } catch {
      setError("Usuario o contraseña incorrectos.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="d-flex justify-content-center align-items-center vh-100">
      <Card style={{ width: 360 }}>
        <Card.Body>
          <Card.Title className="mb-4">Lore Master — Acceso</Card.Title>
          {error && <Alert variant="danger">{error}</Alert>}
          <Form onSubmit={handleSubmit}>
            <Form.Group className="mb-3">
              <Form.Label>Usuario</Form.Label>
              <Form.Control
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoFocus
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Contraseña</Form.Label>
              <Form.Control
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </Form.Group>
            <Button
              variant="warning"
              type="submit"
              className="w-100"
              disabled={loading}
            >
              {loading ? "Entrando..." : "Entrar"}
            </Button>
          </Form>
        </Card.Body>
      </Card>
    </div>
  );
}
```

### `src/components/ProtectedRoute.tsx` — Nuevo

```tsx
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute() {
  const { token } = useAuth();
  return token ? <Outlet /> : <Navigate to="/login" replace />;
}
```

### `src/api/auth.ts` — Nuevo

```typescript
import { apiFetch } from "./apiClient";

interface TokenResponse {
  access_token: string;
  token_type: string;
}

export function loginUser(
  username: string,
  password: string,
): Promise<TokenResponse> {
  const body = new URLSearchParams({ username, password });
  return apiFetch<TokenResponse>("/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: body.toString(),
  });
}
```

Exportar desde `src/api/index.ts`:

```typescript
export { loginUser } from "./auth";
```

### `src/api/apiClient.ts` — Modificar

Inyectar el token en cada request y manejar 401 globalmente.

```typescript
// Obtener token (sin importar React — fuera del árbol de componentes)
function getToken(): string | null {
  return localStorage.getItem("lm_token");
}

function clearToken(): void {
  localStorage.removeItem("lm_token");
}

// En apiFetch, antes de fetch():
const token = getToken();
if (token) {
  headers["Authorization"] = `Bearer ${token}`;
}

// En el bloque de manejo de error:
if (response.status === 401) {
  clearToken();
  window.location.href = "/login";
  throw new ApiAbortError("Session expired");
}
```

### `src/App.tsx` — Modificar

Envolver toda la aplicación en `AuthProvider` y estructurar rutas con `ProtectedRoute`:

```tsx
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import LoginPage from "./pages/LoginPage";

// En el árbol de rutas:
<AuthProvider>
  <Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route element={<ProtectedRoute />}>
      <Route element={<Layout />}>
        <Route path="/" element={<CollectionsPage />} />
        <Route path="/collections/:id" element={<CollectionDetailPage />} />
      </Route>
    </Route>
  </Routes>
</AuthProvider>
```

### `src/components/Layout.tsx` — Modificar

Añadir botón de logout en la barra de navegación:

```tsx
import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";

// Dentro del componente:
const { logout } = useAuth();
const navigate = useNavigate();

function handleLogout() {
  logout();
  navigate("/login");
}

// En el navbar:
<Button variant="outline-secondary" size="sm" onClick={handleLogout}>
  Cerrar sesión
</Button>
```

---

## Archivos modificados

| Archivo | Tipo |
|---|---|
| `backend/requirements.txt` | Añadir `python-jose[cryptography]`, `passlib[bcrypt]` |
| `backend/.env.example` | Añadir bloque `# Auth` con 4 variables |
| `backend/app/core/config.py` | Añadir 4 campos `auth_*` / `jwt_*` en `Settings` |
| `backend/app/core/auth.py` | **Nuevo** — JWT logic + `get_current_user` dependency |
| `backend/app/api/routes/auth.py` | **Nuevo** — `POST /auth/token` |
| `backend/app/main.py` | Registrar `auth_router` público + añadir `Depends(get_current_user)` a routers existentes |
| `frontend/src/context/AuthContext.tsx` | **Nuevo** — estado global de token |
| `frontend/src/pages/LoginPage.tsx` | **Nuevo** — formulario de login |
| `frontend/src/components/ProtectedRoute.tsx` | **Nuevo** — guarda de ruta |
| `frontend/src/api/auth.ts` | **Nuevo** — `loginUser()` |
| `frontend/src/api/index.ts` | Exportar `loginUser` |
| `frontend/src/api/apiClient.ts` | Inyectar Bearer + manejar 401 global |
| `frontend/src/App.tsx` | `AuthProvider` wrapper + rutas con `ProtectedRoute` |
| `frontend/src/components/Layout.tsx` | Botón de logout |

---

## Pasos de configuración inicial

Tras implementar, el operador debe:

1. Generar el hash de la contraseña:
   ```bash
   python -c "from passlib.hash import bcrypt; print(bcrypt.hash('mi_password_seguro'))"
   ```
2. Copiar el hash resultante a `AUTH_PASSWORD_HASH` en `backend/.env`.
3. Cambiar `JWT_SECRET` por una cadena aleatoria larga (mínimo 32 caracteres).
4. Reiniciar el backend.

---

## Fuera de alcance (fase posterior)

- **Multi-usuario**: tabla `users` en DB, passwords por usuario — rompe el modelo local single-user sin añadir valor inmediato.
- **Refresh tokens**: los tokens de 60 minutos son suficientes para sesiones de trabajo locales; añadir refresh token endpoint duplica complejidad.
- **httpOnly cookies**: más seguro contra XSS en apps públicas, pero requiere configurar CORS + SameSite y cambia el flujo de logout. Prioridad baja para un sistema local.
- **RBAC / roles**: single-user no requiere roles; añadirlos sería sobre-ingeniería.
- **Rate limiting en `/auth/token`**: útil contra fuerza bruta si el sistema es público; para uso local es bajo riesgo.
