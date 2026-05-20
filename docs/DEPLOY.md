# Guía de Deploy — Lore Master

Runbook operacional para demo y producción. Cubre solo los pasos que difieren del entorno local.

> **Pendiente de configuración en futuras sesiones:** Clerk (auth en prod), ComfyUI (URL del servidor), Storage S3/R2.

---

## 1. Variables de entorno

```bash
# Copiar la plantilla de producción y completar los valores marcados como <REQUERIDA>
cp backend/.env.production.example backend/.env
```

El archivo `backend/.env.production.example` tiene todos los valores pre-configurados para producción. Las únicas variables que necesitan completarse manualmente:

| Variable | Acción |
|---|---|
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(32))"` — guardar en secrets manager |
| `ALLOWED_ORIGINS` | Reemplazar `https://tu-dominio.com` con el dominio real |
| `POSTGRES_USER` | Definir usuario de PostgreSQL |
| `POSTGRES_PASSWORD` | Definir contraseña — **no guardar en disco en producción**, usar secrets manager o CI/CD |
| `POSTGRES_DB` | Por defecto `loremaster`, cambiar si es necesario |
| `COMFYUI_URL` | Reemplazar `<ip-comfyui>` con la IP/hostname del servidor GPU |

> `RATE_LIMIT_ENABLED=true` ya está activo en la plantilla. No sobreescribir con `false` en producción — esa variable es exclusiva de entornos de evaluación/desarrollo local.

> `POSTGRES_USER`, `POSTGRES_PASSWORD` y `POSTGRES_DB` también son requeridas por `docker-compose.prod.yml` para levantar el contenedor de PostgreSQL.

---

## 2. Infraestructura — secuencia de arranque

```bash
# 1. Levantar Qdrant + Redis + PostgreSQL (sin puertos expuestos al host)
docker compose -f backend/docker-compose.prod.yml up -d

# 2. Esperar a que PostgreSQL esté listo
docker compose -f backend/docker-compose.prod.yml ps  # postgres: healthy

# 3. Aplicar migraciones (ANTES de arrancar el backend)
cd backend
alembic upgrade head

# 4. Arrancar el backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# 5. Construir y servir el frontend
cd frontend
npm run build
# servir dist/ con nginx, caddy, o similar detrás de HTTPS
```

> `SKIP_MIGRATIONS` **no debe definirse** en producción. Solo lo inyecta el script de evaluación local.

---

## 3. Checklist pre-deploy

### Configuración

- [ ] `SECRET_KEY` generada con `secrets.token_hex(32)` y guardada en secrets manager
- [ ] `ENVIRONMENT=production`
- [ ] `COOKIE_SECURE=True`
- [ ] `ALLOWED_ORIGINS` contiene solo dominios con `https://`
- [ ] `LOG_LEVEL=WARNING`
- [ ] `RATE_LIMIT_ENABLED=true`
- [ ] `DATABASE_URL` apunta a PostgreSQL (no SQLite)
- [ ] `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` definidas (no en `.env` en disco — usar secrets manager o CI/CD)
- [ ] `QDRANT_URL` y `REDIS_URL` usan nombres de servicio Docker (`qdrant`, `redis`)

### Base de datos

- [ ] `alembic upgrade head` ejecutado y sin errores antes del primer arranque
- [ ] Verificar que las tablas existen: `psql -c "\dt"`

### Infraestructura

- [ ] `docker compose -f docker-compose.prod.yml ps` muestra todos los servicios `healthy`
- [ ] `ComfyUI` accesible desde el backend en `COMFYUI_URL`

### Pendientes (bloquean producción real, no demo privada)

- [ ] Clerk configurado (`CLERK_JWKS_URL`, `CLERK_AUDIENCE`) y probado end-to-end
- [ ] Storage S3/R2 configurado (`STORAGE_BACKEND`, bucket, credenciales)

### Seguridad (código)

- [ ] Fix moderación HARM-08 aplicado antes del primer deploy público

---

## 4. Verificación post-arranque

```bash
# Health check del backend
curl https://tu-dominio.com/api/v1/health

# Respuesta esperada (todos en "ok" o "warn" si Ollama no está en la misma red):
# {"status": "ok", "qdrant": "ok", "ollama": "ok"}
```

Si `qdrant` aparece como `"warn"`, verificar que `QDRANT_URL` usa el nombre del servicio Docker (`qdrant:6333`), no `localhost`.

---

*Última actualización: 2026-05-19*
