# Integración con Clerk - Guía completa

> **Nota (2026-05-12):** Desde la Fase 13, el sistema usa **cookies HttpOnly** + **CSRF tokens** para todas las sesiones. Clerk sigue siendo el proveedor de identidad, pero el token de sesión local se transporta via cookie (no header `Authorization`). Ver `docs/CLERK-APP-INTEGRATION.md` para los detalles técnicos actualizados.

## Visión general

Lore Master soporta 3 entornos con diferentes configuraciones de autenticación:

| Entorno | ENVIRONMENT | Autenticación | Registro | Uso |
|---------|-------------|---------------|----------|-----|
| Local | `local` | JWT propio + cookies | Formulario propio | Desarrollo offline |
| Demo | `demo` | Clerk + cookies | Invitaciones manuales | Demos públicas (Vercel) |
| Production | `production` | Clerk + cookies | Registro abierto | Servidor de producción |

---

## Los 3 escenarios

### 1. LOCAL (desarrollo)

```
┌─────────────────────────────────────────────────────────────┐
│  USUARIO EN DESARROLLO LOCAL                               │
│                                                             │
│  Flujo:                                                    │
│  1. Entra a http://localhost:5173                          │
│  2. Usa el formulario de login/registro de la app         │
│  3. Usuario se crea en TU base de datos                   │
│                                                             │
│  ALMACENAMIENTO:                                           │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  TU BASE DE DATOS (users table)                   │     │
│  │  id | username | email | hashed_password | ...   │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                             │
│  • El usuario se almacena en tu BD                         │
│  • El owner_id en colecciones es un UUID local            │
└─────────────────────────────────────────────────────────────┘
```

### 2. DEMO (Vercel)

```
┌─────────────────────────────────────────────────────────────┐
│  USUARIO EN DEMO (Vercel)                                  │
│                                                             │
│  Pre-requisitos:                                           │
│  - Vos creás el usuario manualmente en Clerk Dashboard     │
│  - Clerk envía invitación al usuario                       │
│  - Usuario acepta y configura password                     │
│                                                             │
│  Flujo:                                                    │
│  1. Usuario entra a tu-demo.vercel.app                    │
│  2. Redirige a Clerk para autenticarse                    │
│  3. Clerk redirige de vuelta con JWT                      │
│  4. Tu backend valida el JWT de Clerk                     │
│  5. Backend crea/setea cookie HttpOnly local              │
│  6. Frontend usa cookies para requests posteriores        │
│                                                             │
│  ALMACENAMIENTO:                                           │
│  ┌──────────────────────┐  ┌──────────────────────────────┐   │
│  │      CLERK         │  │    TU BASE DE DATOS        │   │
│  │  (usuarios)        │  │  (datos de la app)         │   │
│  │                     │  │                            │   │
│  │  - id: clerk_123   │  │  collections               │   │
│  │  - email            │  │    owner_id: clerk_123    │   │
│  │  - password         │  │                            │   │
│  │  - nombre, avatar   │  │  entities, documents       │   │
│  └──────────────────────┘  │    owner_id: clerk_123    │   │
│                           └──────────────────────────────┘   │
│                                                             │
│  • Usuario NO se crea en tu BD                            │
│  • El owner_id referencia el ID de Clerk                   │
│  • Todos los datos de la app están en tu BD               │
└─────────────────────────────────────────────────────────────┘
```

### 3. PRODUCTION (tu servidor)

```
┌─────────────────────────────────────────────────────────────┐
│  USUARIO EN PRODUCCIÓN                                    │
│                                                             │
│  Configuración en Clerk Dashboard:                         │
│  User & Authentication → Sign-up → Allow public sign-ups    │
│                                                             │
│  Flujo:                                                    │
│  1. Usuario entra a tu-dominio.com                        │
│  2. Clerk muestra formulario de registro                  │
│  3. Usuario se registra (email/pass o Google)            │
│  4. Clerk crea usuario automáticamente                   │
│  5. Redirige a tu app con JWT                             │
│  6. Tu backend valida el JWT de Clerk                     │
│  7. Backend crea/setea cookie HttpOnly local              │
│  8. Frontend usa cookies para requests posteriores        │
│                                                             │
│  ALMACENAMIENTO:                                           │
│  (Exactamente igual que Demo)                             │
│                                                             │
│  ┌──────────────────────┐  ┌──────────────────────────────┐   │
│  │      CLERK         │  │    TU BASE DE DATOS        │   │
│  │  Usuario se crea    │  │  owner_id: clerk_xxx      │   │
│  │  automáticamente   │  │  (no hay tabla users)     │   │
│  └──────────────────────┘  └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuración de Clerk

### Variables de entorno necesarias

```env
# Obligatorio para demo y production (no necesario para local)
CLERK_JWKS_URL=https://your-org.clerk.accounts.dev/.well-known/jwks.json
CLERK_AUDIENCE=your-audience-id
```

### Ajuste de ENVIRONMENT

```env
# Desarrollo local
ENVIRONMENT=local

# Demo (Vercel)
ENVIRONMENT=demo

# Production (tu servidor)
ENVIRONMENT=production
```

### Control de registro en Clerk Dashboard

| Entorno | Configuración recomendada |
|---------|--------------------------|
| Demo | **Disable sign-ups** + crear usuarios manualmente |
| Production | **Allow public sign-ups** (registro abierto) |

---

## Archivos a modificar e importaciones necesarias

### 1. `backend/app/core/auth/dependencies.py`

**Cambio:** línea ~25

```python
# ANTES (solo production usa Clerk)
if settings.environment == "production":
    from app.api.routes.auth_clerk import decode_clerk_token
    return decode_clerk_token(credentials.credentials)

# DESPUÉS (demo + production usan Clerk)
if settings.environment not in ("local", "test"):
    from app.api.routes.auth_clerk import decode_clerk_token
    return decode_clerk_token(credentials.credentials)
```

**Importaciones necesarias:**
- Ya existe: `from app.core.config import settings`
- Ya existe: `from app.core.auth import verify_token`
- Ya existe: `from app.api.routes.auth_clerk import decode_clerk_token` (import dinámico)

### 2. `backend/app/.env` (configuración)

**Agregar variables:**

```env
# Para demo y production
CLERK_JWKS_URL=https://your-org.clerk.accounts.dev/.well-known/jwks.json
CLERK_AUDIENCE=your-audience-id

# Ajuste del entorno
ENVIRONMENT=demo    # o production
```

### 3. `backend/app/core/config.py` (si no existe)

Verificar que `Settings` incluya:

```python
class Settings(BaseSettings):
    # ... otros settings ...

    clerk_jwks_url: str = ""
    clerk_audience: str = ""
```

### 4. `backend/app/api/routes/auth_clerk.py` (ya existe)

**Verificar que contenga:**
- `decode_clerk_token(token: str) -> dict`
- Descarga y cachea el JWKS desde `CLERK_JWKS_URL`
- Valida el JWT contra la clave pública
- Retorna `{"sub": "user_xxx", "email": "...", ...}`

---

## Librerías necesarias (ya instaladas)

```
PyJWT>=2.8.0        # Para decodificar tokens JWT
httpx>=0.24.0       # Para descargar JWKS (si no usa requests)
```

Verificar en `backend/requirements.txt`.

---

## Resumen de diferencias

| Aspecto | Local | Demo | Production |
|---------|-------|------|-------------|
| **Auth** | JWT propio | Clerk | Clerk |
| **Usuario en tu BD** | ✅ Sí | ❌ No | ❌ No |
| **Usuario en Clerk** | ❌ No | ✅ Sí | ✅Sí |
| **owner_id en colecciones** | UUID local | Clerk ID | Clerk ID |
| **Cómo agregar usuarios** | Registro normal | Invitación manual | Registro abierto |
| **Sesión** | Tu token JWT | Token Clerk | Token Clerk |

---

## Notas importantes

1. **Cookies HttpOnly + CSRF** - Desde la Fase 13, todos los entornos usan cookies HttpOnly para el token de sesión y validación CSRF en mutaciones (POST/PUT/PATCH/DELETE). Clerk sigue siendo el proveedor de identidad, pero el frontend no maneja tokens JWT directamente.

2. **Provisioning de usuarios** - En demo y production, el usuario Clerk debe existir en la BD local (ver `get_or_create_user` en `CLERK-APP-INTEGRATION.md`). El `owner_id` referencia el ID de Clerk.

3. **Todos los datos de la app van a tu BD** - Colecciones, entidades, documentos, contenidos... todos almacenados localmente, solo referencian al owner_id de Clerk.

4. **El flujo es idéntico para demo y production** - Cambia solo la configuración en el dashboard de Clerk para controlar registro.

5. **Local es el único ambiente con registro propio** - Solo en desarrollo local se usa el sistema tradicional de registro con bcrypt.

---

## Links útiles

- [Clerk Dashboard](https://dashboard.clerk.com)
- [Documentación Clerk](https://clerk.com/docs)
- [JWKS Endpoint](https://clerk.com/docs/backend-clerk-frontend-apis/verify-token)

---

*Documento creado: 2026-05-10*