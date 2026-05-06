# Autenticación con JWT en Loremaster

Guía de estudio sobre cómo funciona el sistema de autenticación del proyecto, desde los conceptos básicos hasta la implementación concreta.

---

## 1. Conceptos previos

### ¿Qué es un JWT?

JWT son las siglas de **JSON Web Token**. Es una cadena de texto que el servidor entrega al cliente cuando se autentica correctamente. Tiene este aspecto:

```
eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyLTEyMyIsInVzZXJuYW1lIjoic2VyZ2lvIn0.Xk3h...
```

No es aleatoria — está compuesta por tres partes separadas por puntos:

```
HEADER . PAYLOAD . FIRMA
```

| Parte | Contenido | Ejemplo decodificado |
|---|---|---|
| Header | Algoritmo usado | `{"alg": "HS256"}` |
| Payload | Datos del usuario + expiración | `{"sub": "user-123", "exp": 1234567890}` |
| Firma | Verificación de integridad | calculada con `SECRET_KEY` |

> El payload **no está cifrado** — solo está en Base64. Cualquiera puede leerlo. La firma garantiza que nadie lo ha modificado.

### ¿Qué es Bearer?

`Bearer` es una palabra del estándar HTTP que significa "portador". Indica el tipo de token que se está enviando. Siempre va fija antes del JWT:

```
Authorization: Bearer eyJhbGci...
                ↑            ↑
           palabra fija   el JWT real
```

No se genera ni se configura — es siempre esa palabra.

### ¿Qué es el SECRET_KEY?

Es una clave privada que **solo conoce el servidor**. Se usa para firmar el JWT al generarlo y para verificar que la firma es auténtica cuando llega en una petición. Si alguien consigue el `SECRET_KEY`, puede forjar tokens válidos — por eso nunca debe publicarse.

---

## 2. Flujo completo paso a paso

```
┌──────────────────────────────────────────────────────────────────┐
│  REGISTRO (primera vez)                                          │
│                                                                  │
│  Frontend → POST /api/v1/auth/register  {username, password}     │
│  Backend  → hashea la contraseña con bcrypt                      │
│  Backend  → guarda User en la base de datos                      │
│  Backend  → genera JWT firmado con SECRET_KEY                    │
│  Backend  → devuelve { access_token: "eyJ..." }                 │
│  Frontend → guarda el token en localStorage                      │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  LOGIN (sesiones posteriores)                                    │
│                                                                  │
│  Frontend → POST /api/v1/auth/login  {username, password}        │
│  Backend  → busca el usuario en la BD por username               │
│  Backend  → verifica la contraseña con bcrypt                    │
│  Backend  → genera JWT firmado con SECRET_KEY                    │
│  Backend  → devuelve { access_token: "eyJ..." }                 │
│  Frontend → guarda el token en localStorage                      │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  PETICIÓN AUTENTICADA (cualquier endpoint protegido)             │
│                                                                  │
│  Frontend → lee el token de localStorage                         │
│  Frontend → GET /api/v1/collections/                             │
│             Header: Authorization: Bearer eyJ...                 │
│  Backend  → extrae el token del header                           │
│  Backend  → verifica la firma con SECRET_KEY                     │
│  Backend  → verifica que no ha expirado                          │
│  Backend  → deja pasar → responde 200                            │
│          ↳ si falla → responde 401                               │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  401 RECIBIDO                                                    │
│                                                                  │
│  apiClient.ts → elimina el token de localStorage                 │
│  apiClient.ts → redirige a /login                                │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  LOGOUT                                                          │
│                                                                  │
│  Usuario pulsa "Cerrar sesión" en el navbar                      │
│  Frontend → elimina el token de localStorage                     │
│  Frontend → redirige a /login                                    │
│  (el backend no necesita saber nada — el token simplemente       │
│   deja de enviarse)                                              │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Variables de entorno

Viven en `backend/.env` (copiado de `backend/.env.example`). `config.py` las lee automáticamente al arrancar — nunca contiene valores reales, solo los defaults de desarrollo.

### Variables de autenticación

| Variable | Dónde | Para qué |
|---|---|---|
| `SECRET_KEY` | `backend/.env` | Firma y verifica los JWT. Cambiar en producción. |
| `ALGORITHM` | `backend/.env` | Algoritmo de firma. Dejar en `HS256`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `backend/.env` | Duración del token. `1440` = 24 horas. |
| `ENVIRONMENT` | `backend/.env` | `local` usa JWT propio · `production` usa Clerk. |

### Variables de Clerk (solo producción)

| Variable | Para qué |
|---|---|
| `CLERK_JWKS_URL` | URL donde Clerk publica sus claves públicas de firma. |
| `CLERK_AUDIENCE` | Identificador de tu aplicación en Clerk. |

### Variable de frontend

| Variable | Dónde | Para qué |
|---|---|---|
| `VITE_API_BASE_URL` | `frontend/.env` | URL base del backend. Por defecto `http://localhost:8000/api/v1`. |

---

## 4. Cómo generar el SECRET_KEY

No es un token de ningún servicio externo — es una cadena aleatoria larga que tú defines. Generarla con Python:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
# → a3f8c2e1b4d6f0e9a2c5b8d1e4f7a0b3c6d9e2f5a8b1c4d7e0f3a6b9c2d5e8f1
```

Pegarla en `backend/.env`:

```bash
SECRET_KEY="a3f8c2e1b4d6f0e9a2c5b8d1e4f7a0b3c6d9e2f5a8b1c4d7e0f3a6b9c2d5e8f1"
```

---

## 5. Modos de autenticación según entorno

El backend decide qué sistema usar según `ENVIRONMENT`:

```
ENVIRONMENT=local
    └── get_current_user verifica con SECRET_KEY (HS256)
        Ideal para desarrollo — no necesita servicios externos.

ENVIRONMENT=production
    └── get_current_user verifica con las claves de Clerk (RS256)
        Clerk gestiona usuarios, sesiones y seguridad avanzada.
```

El frontend no necesita saber cuál está activo — siempre manda el mismo header `Authorization: Bearer <token>`. El backend resuelve qué verificador usar internamente.

---

## 6. Archivos del proyecto

### Backend

| Archivo | Responsabilidad |
|---|---|
| `app/core/auth.py` | `create_access_token`, `verify_token`, `hash_password`, `verify_password` |
| `app/core/auth_deps.py` | Dependencia FastAPI `get_current_user` — punto de entrada para todas las rutas protegidas |
| `app/api/routes/auth.py` | Endpoints `/auth/login` y `/auth/register` |
| `app/api/routes/auth_clerk.py` | Verificación de tokens Clerk + endpoint `/auth/clerk/verify` |
| `app/models/users.py` | Modelo `User` en base de datos |
| `app/core/config.py` | Lee las variables de entorno (`SECRET_KEY`, `ALGORITHM`, etc.) |

### Frontend

| Archivo | Responsabilidad |
|---|---|
| `src/utils/token.ts` | Lee/guarda/elimina el token en `localStorage` |
| `src/api/apiClient.ts` | Inyecta el token en cada petición · redirige a `/login` en 401 |
| `src/api/auth.ts` | Llama a `/auth/login` y `/auth/register` |
| `src/pages/LoginPage.tsx` | Formulario de login y registro |
| `src/components/ProtectedRoute.tsx` | Redirige a `/login` si no hay token |
| `src/App.tsx` | Define `/login` como pública y protege el resto de rutas |

---

## 7. ¿Por qué bcrypt para las contraseñas?

Las contraseñas **nunca se guardan en texto plano**. Se guardan hasheadas con bcrypt, un algoritmo diseñado específicamente para contraseñas:

```
"mipassword123"  →  bcrypt  →  "$2b$12$eImiTXuWVxfM37uY4JANj..."
```

bcrypt es lento por diseño — dificulta los ataques de fuerza bruta. Aunque alguien robe la base de datos, no puede recuperar las contraseñas originales.

---

## 8. Diferencias entre JWT local y Clerk

| | JWT local | Clerk |
|---|---|---|
| **Quién firma** | Tu servidor con `SECRET_KEY` | Clerk con clave privada RSA |
| **Algoritmo** | HS256 (simétrico) | RS256 (asimétrico) |
| **Gestión de usuarios** | Tu base de datos | Clerk (registro, 2FA, OAuth...) |
| **Cuándo usar** | Desarrollo local | Producción |
| **Configuración** | Solo `SECRET_KEY` en `.env` | `CLERK_JWKS_URL` + `CLERK_AUDIENCE` |
