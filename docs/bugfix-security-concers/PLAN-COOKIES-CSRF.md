# Plan de Migración: Cookies HttpOnly + CSRF (H-14, M-17, H-13)

**Fecha:** 2026-05-12  
**Branch:** `bugfix/security-concers`  
**Estado:** Diseño aprobado — pendiente de implementación  
**Resuelve:** H-14 (sin CSRF), M-17 (migración a cookies sin CSRF), H-13 (JWT en sessionStorage)

---

## Contexto

Actualmente el frontend almacena el JWT en `sessionStorage` y lo envía en cada request via header `Authorization: Bearer <token>`. Esto tiene dos problemas graves:

1. **XSS puede exfiltrar el token** durante la sesión activa (`sessionStorage` es accesible desde JS).
2. **No hay protección CSRF** — si se migra a cookies sin defensa CSRF, las rutas mutantes quedan expuestas.
3. **Sin SameSite=Strict** — las cookies de sesión (cuando existan) pueden ser enviadas en contextos cross-site.

Este documento describe la arquitectura de doble cookie (`access_token` HttpOnly + `csrf_token`) que resuelve los tres problemas y es compatible con el despliegue futuro en producción.

---

## Estado actual (pre-migración)

| Componente | Cómo funciona hoy |
|---|---|
| **Login** | Backend responde JSON `{"access_token": "..."}` |
| **Frontend** | Guarda token en `sessionStorage`, lo lee con `getToken()` de `utils/token.ts` |
| **API calls** | `apiFetch` inyecta header `Authorization: Bearer <token>` |
| **Auth backend** | `get_current_user` lee `HTTPBearer` del header `Authorization` |
| **Logout** | Endpoint POST `/logout` (incrementa `token_version` en BD) |
| **Cookies** | No se usan para autenticación |
| **Clerk** | No está en producción todavía. Solo existe branch en `dependencies.py` para `environment="production"` |

---

## Arquitectura propuesta: Doble cookie

### Cookies involucradas

| Cookie | Atributos | ¿Quién la lee? | Propósito |
|---|---|---|---|
| `access_token` | `HttpOnly`, `Secure`, `SameSite=Strict`, `Path=/api/v1` | Solo el servidor | Transporta el JWT firmado. Inaccesible para JavaScript. |
| `csrf_token` | `Secure`, `SameSite=Strict`, `Path=/api/v1` | Backend + Frontend | Token aleatorio de 32 bytes. El frontend lo envía en header `X-CSRF-Token`; el backend valida que coincida con la cookie. |

### Flujo de autenticación

```
LOGIN (POST /auth/login)
├─ Backend valida credenciales
├─ Backend genera JWT
├─ Backend setea cookie HttpOnly "access_token" con el JWT
├─ Backend genera CSRF token aleatorio (32 bytes hex)
├─ Backend setea cookie "csrf_token" con el CSRF token
└─ Backend responde: { "success": true } (sin JWT en body)

REQUESTS MUTANTES (POST/PUT/PATCH/DELETE)
├─ Navegador envía automáticamente ambas cookies
├─ Frontend lee cookie "csrf_token" via document.cookie
├─ Frontend envía header: X-CSRF-Token: <csrf_token>
├─ Backend lee JWT desde cookie HttpOnly (no del header)
├─ Backend compara CSRF del header vs CSRF de la cookie
└─ Si coinciden → autoriza. Si no → 403

REQUESTS DE LECTURA (GET/HEAD)
├─ Solo requieren la cookie HttpOnly (sin CSRF)
└─ Esto permite compartir links / hacer prefetch seguro

LOGOUT (POST /auth/logout)
├─ Backend invalida token_version en BD
├─ Backend borra ambas cookies (setea expiración en el pasado)
└─ Frontend redirige a /login
```

---

## Cambios por archivo

### Backend

#### 1. `backend/app/core/config/settings.py`

Agregar configuración de cookies:

```python
cookie_access_name: str = "access_token"
cookie_csrf_name: str = "csrf_token"
cookie_secure: bool = True  # HTTPS obligatorio en producción/demo
cookie_samesite: str = "Strict"
cookie_domain: str | None = None  # Setear en producción si se comparte entre subdominios
```

#### 2. `backend/app/core/auth/csrf.py` (nuevo archivo)

```python
import secrets
from fastapi import Request, HTTPException

def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)

def validate_csrf(request: Request) -> None:
    cookie_token = request.cookies.get("csrf_token")
    header_token = request.headers.get("x-csrf-token")
    if not cookie_token or not header_token:
        raise HTTPException(status_code=403, detail="CSRF token faltante")
    if not secrets.compare_digest(cookie_token, header_token):
        raise HTTPException(status_code=403, detail="CSRF token inválido")
```

#### 3. `backend/app/core/auth/dependencies.py`

- Reemplazar `HTTPBearer` por lectura de cookie `access_token`.
- Para el branch de Clerk (producción futura), mantener el mismo flujo pero leyendo la cookie después de validar el token de Clerk.
- Si no hay cookie → 401.

```python
from fastapi import Request

def get_current_user(
    request: Request,  # Reemplaza HTTPBearer
    session: Session = Depends(get_session),
) -> dict:
    token = request.cookies.get(settings.cookie_access_name)
    if not token:
        raise HTTPException(status_code=401, detail="No autorizado")
    
    if settings.environment == "production":
        # Clerk: validar token de Clerk, luego setear/validar cookie local
        ...
    
    payload = verify_token(token)
    # Resto de validaciones igual (is_deleted, token_version)
    ...
```

#### 4. `backend/app/api/routes/auth/auth.py`

- **`/login`** y **`/register`**: En lugar de retornar `{"access_token": token}`, setear dos cookies en la `Response`.
- **`/logout`**: Invalidar `token_version` + borrar ambas cookies.

```python
from fastapi import Response

@router.post("/login")
def login(request: LoginRequest, session: Session = Depends(get_session)):
    ...
    token = create_access_token(...)
    csrf = generate_csrf_token()
    response = Response(content='{"success": true}', media_type="application/json")
    response.set_cookie(
        key=settings.cookie_access_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/api/v1",
    )
    response.set_cookie(
        key=settings.cookie_csrf_name,
        value=csrf,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/api/v1",
    )
    return response
```

#### 5. Routers mutantes (POST/PUT/PATCH/DELETE)

Agregar `Depends(validate_csrf)` a los routers que modifican estado:

```python
from app.core.auth.csrf import validate_csrf

router = APIRouter(
    prefix="/collections",
    tags=["collections"],
    dependencies=[Depends(validate_csrf)],  # Solo para mutaciones
)
```

> **Nota:** Los endpoints GET/HEAD no deben requerir CSRF.

---

### Frontend

#### 1. `frontend/src/utils/token.ts`

**Eliminar o deprecar.** El token ya no vive en JavaScript.

```typescript
// TODO: Eliminar tras migración a cookies
// Los tokens ahora son manejados por el navegador via cookies HttpOnly
```

#### 2. `frontend/src/api/apiClient.ts`

**Cambios:**
- `BASE_URL`: cambiar a `/api/v1` para usar el proxy de Vite en desarrollo.
- Quitar inyección de `Authorization: Bearer`.
- Agregar lectura de `csrf_token` desde `document.cookie`.
- En requests **mutantes** (`POST`, `PUT`, `PATCH`, `DELETE`), añadir header `X-CSRF-Token`.

```typescript
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

function getCsrfToken(): string | null {
  const match = document.cookie.match(new RegExp('(^| )csrf_token=([^;]+)'));
  return match ? decodeURIComponent(match[2]) : null;
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  
  // CSRF solo para mutaciones
  if (["POST", "PUT", "PATCH", "DELETE"].includes(options.method?.toUpperCase() || "")) {
    const csrf = getCsrfToken();
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }
  
  // NO enviar Authorization: Bearer — la cookie se envía automáticamente
  
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
    credentials: "include",  // Crítico: envía cookies cross-origin
  });
  
  // Manejo de 401: redirigir a login (la cookie la borra el backend en logout)
  if (response.status === 401) {
    const isAlreadyOnLogin = window.location.pathname === "/login";
    if (!isAlreadyOnLogin) {
      window.location.href = "/login";
      throw new ApiError(401, "Sesión expirada.");
    }
    ...
  }
  ...
}
```

#### 3. `frontend/src/api/factory.ts`

Sin cambios directos. El header CSRF se maneja en `apiClient.ts`.

#### 4. Hooks de autenticación (`useAuth` o similar)

- **Login:** Después de POST `/auth/login`, no guardar nada en `sessionStorage`. El navegador guarda las cookies automáticamente.
- **Logout:** Llamar POST `/auth/logout`, luego redirigir. No necesita `removeToken()`.

---

## ⚠️ Consideraciones de implementación

### Entorno local (desarrollo)

| Aspecto | Configuración |
|---|---|
| `cookie_secure` | `False` (HTTP localhost) |
| `cookie_samesite` | `"Strict"` |
| `BASE_URL` frontend | `/api/v1` (usa proxy de Vite) |
| CORS | Menos crítico con proxy, pero mantener `allow_credentials=True` |

**Por qué el proxy de Vite es necesario:**
- El frontend corre en `localhost:5173`, el backend en `localhost:8000`.
- Sin proxy, el navegador las trata como cross-site y `SameSite=Strict` bloquea las cookies.
- Con proxy, todo va a `localhost:5173/api/*` y Vite reenvía internamente → same-site.

### Entorno de producción (despliegue futuro)

| Aspecto | Configuración |
|---|---|
| `cookie_secure` | `True` (HTTPS obligatorio) |
| `cookie_samesite` | `"Strict"` |
| `cookie_domain` | `"tudominio.com"` (opcional, para subdominios) |
| `BASE_URL` frontend | `https://api.tudominio.com/api/v1` o `/api/v1` si usan reverse proxy |

### Integración con Clerk (futuro)

Cuando se implemente Clerk en producción:

1. **Opción A (recomendada):** Clerk maneja la autenticación y setea su propia cookie HttpOnly. Tu backend valida esa cookie en `get_current_user` en lugar de la tuya.
2. **Opción B:** Tu backend valida el JWT de Clerk, luego setea tu propia `access_token` cookie + `csrf_token` como se describe aquí.

En ambos casos, el token CSRF que implementas **sigue funcionando igual**.

### Tests

| Suite | Ajuste necesario |
|---|---|
| **Backend (175 tests)** | `TestClient` de FastAPI maneja cookies automáticamente si se usa `client.post(...)` y luego `client.get(...)` en la misma instancia. Verificar que el login setea cookies y las peticiones siguientes las envían. |
| **Frontend (121 tests)** | Mocks de `sessionStorage` y `getToken()` deben ajustarse. Simular cookies con `document.cookie = "..."` en tests. |

---

## ✅ Checklist de implementación

- [ ] Agregar config de cookies en `settings.py`
- [ ] Crear `csrf.py` con generación y validación
- [ ] Modificar `dependencies.py` para leer JWT de cookie
- [ ] Modificar `auth.py` login/register/logout para setear/borrar cookies
- [ ] Aplicar dependencia CSRF en routers mutantes
- [ ] Actualizar `apiClient.ts` (quitar Authorization, agregar X-CSRF-Token, cambiar BASE_URL)
- [ ] Limpiar `token.ts`
- [ ] Ajustar tests backend para cookies
- [ ] Ajustar tests frontend si rompen
- [ ] Verificar CORS en local con `credentials: "include"`
- [ ] Documentar variables de entorno para producción

---

## Referencias

- [Owasp: Double Submit Cookie](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html#double-submit-cookie)
- [FastAPI: Response.set_cookie](https://fastapi.tiangolo.com/reference/response/#fastapi.Response.set_cookie)
- [MDN: SameSite cookies](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie/SameSite)
- Hallazgos del audit: H-14, M-17, H-13 en `./AUDIT-RESULTS-11-05-26.md`

---

*Documento generado para referencia durante despliegue. Implementación pendiente de aprobación.*
