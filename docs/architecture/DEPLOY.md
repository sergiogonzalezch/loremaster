# Guía de Deploy — Lore Master

Runbook operacional para demo y producción. Cubre solo los pasos que difieren del entorno local.

> **Pendiente de configuración en futuras sesiones:** Clerk (auth en prod), ComfyUI (URL del servidor), TLS/HTTPS. Storage S3/R2 ya implementado — solo requiere credenciales en `.env.production`.

---

## Arquitectura del stack de demo

```
                    ┌─────────────────────────────────────────┐
 http://localhost ──► loremaster-frontend (Nginx :80)         │
                    │   /health  → loremaster-api:8000/health │
                    │   /api/*   → loremaster-api:8000        │
                    │   /media/* → loremaster-floci:4566      │
                    │   /*       → bundle React (SPA)         │
                    └──────────────────────────────────────────┘
                           ↕ red Docker interna
                    loremaster-api:8000   (sin puerto al host)
                    loremaster-floci:4566 (sin puerto al host)
                    postgres:5432         (sin puerto al host)
                    qdrant:6333           (sin puerto al host)
                    redis:6379            (sin puerto al host)
```

Un único puerto expuesto al host: **80**. Nginx actúa como reverse proxy y sirve el frontend.  
Las migraciones Alembic corren automáticamente en el startup del backend (`lifespan.py`).

---

## 1. Variables de entorno

Copiar el archivo de ejemplo y editar los valores reales:

```bash
cp .env.production.example .env.production
# Editar .env.production con SECRET_KEY, POSTGRES_PASSWORD y ALLOWED_ORIGINS
```

`.env.production` contiene las variables que `docker-compose.prod.yml` interpola con `${VAR}`.
El archivo real nunca se commitea — está en `.gitignore`.

Variables obligatorias (el compose falla si no están definidas):

```bash
# Generar con: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=<valor-generado>

POSTGRES_USER=loremaster
POSTGRES_PASSWORD=<contraseña-segura>
POSTGRES_DB=loremaster

# Demo local: http://localhost | Servidor real: https://tu-dominio.com
ALLOWED_ORIGINS=http://localhost
```

> El resto de la configuración del backend (Qdrant, Redis, Ollama, storage...) está  
> hardcodeada en el bloque `environment:` del compose y no requiere `.env.production`.

---

## 2. Arranque

```bash
# Levantar todo el stack (construye imágenes si no existen)
make prod-up

# Verificar que todos los servicios están healthy
docker compose -f backend/docker-compose.prod.yml ps

# Bajar todo
make prod-down
```

### Reconstruir tras cambios de código

```bash
make prod-rebuild        # reconstruye backend + frontend
make prod-rebuild-api    # solo backend (cambios Python)
make prod-rebuild-fe     # solo frontend (cambios React/CSS)
```

> `SKIP_MIGRATIONS` **no debe definirse** en producción. Solo lo inyecta el script de evaluación local.

---

## 3. Primer usuario admin

Una vez el stack está corriendo, promover un usuario a admin:

```bash
# Desde la raíz del repo (requiere loremaster-api healthy)
make make-admin USER=<username>

# Alternativa directa (si make no está disponible):
docker exec -it loremaster-api python scripts/make_admin.py <username> --force
```

---

## 4. Checklist pre-deploy

### Configuración

- [x] `SECRET_KEY` generada y añadida a `.env.production`
- [x] `ALLOWED_ORIGINS=["http://localhost"]` en `.env.production` (actualizar con dominio real en cloud)
- [x] `STORAGE_BASE_URL=http://localhost/media` en `.env.production` (actualizar con dominio real en cloud)
- [x] `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` definidas en `.env.production`
- [x] `COOKIE_SECURE=true` — hardcodeado en `docker-compose.prod.yml`
- [x] `RATE_LIMIT_ENABLED=false` para demo — en `.env.production`
- [ ] `LLAMA_GUARD_ENABLED=false` por defecto — activar con `true` + `ollama pull llama-guard3:8b` si se quiere moderación semántica (añade ~400-900 ms por respuesta)

### Clerk

- [x] `CLERK_JWKS_URL` añadida a `.env.production`
- [x] `CLERK_AUDIENCE=http://localhost` en `.env.production` (actualizar con dominio real en cloud)
- [x] `VITE_CLERK_PUBLISHABLE_KEY` en `.env.production` — se bake en el bundle al hacer `prod-rebuild-fe`
- [x] JWT template con claim `email` configurado en Clerk Dashboard → Configure → Sessions
- [ ] Para cloud: cambiar `pk_test_` por `pk_live_` (requiere TLS activo)

### Storage S3/R2

- [x] Demo local: Floci activo por defecto (fallback en compose)
- [ ] Para R2 real: descomentar y rellenar `S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` en `.env.production`

### Base de datos

- [x] Migraciones Alembic configuradas para correr automáticamente en startup (`lifespan.py`)
- [ ] Verificar en el primer arranque: `docker logs loremaster-api | grep alembic`

### Infraestructura

- [x] `docker compose -f backend/docker-compose.prod.yml ps` muestra todos los servicios `healthy`
- [x] `http://localhost` abre el frontend correctamente
- [x] `http://localhost/health` retorna `{"status": "ok", ...}`
- [ ] `ComfyUI` accesible desde el backend en `COMFYUI_URL` (si se usa generación de imágenes)

### Pendientes (bloquean producción real, no demo privada)

| Item | Código | Compose | Configuración |
|---|---|---|---|
| **Clerk auth** | ✅ `auth_clerk.py`, `clerk.py`, 8 tests | ✅ `CLERK_JWKS_URL` + `CLERK_AUDIENCE` activos en compose | ✅ Configurado en `.env.production` + JWT template con `email` en dashboard |
| **Storage S3/R2 real** | ✅ `core/storage/s3_client.py` con boto3 | ✅ `S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` interpolables con fallback Floci | ✅ Vars comentadas en `.env.production` listas para R2 — solo rellenar credenciales |
| **TLS/HTTPS** | ❌ Nginx solo `listen 80` | — | ❌ Certificado SSL (Let's Encrypt / certbot) + `listen 443 ssl` + redirect 80→443 en `nginx.conf` |
| **GPU cloud** | ❌ `runpod_client.py` no existe | ❌ `IMAGE_BACKEND: comfyui` hardcodeado — hacer `${IMAGE_BACKEND:-comfyui}` | ❌ Implementar cliente + añadir `RUNPOD_API_KEY` / `RUNPOD_ENDPOINT_ID` en `.env.production` |

### Seguridad (código)

- [x] Fix moderación HARM-08 cerrado — patrón bidireccional + leet + separadores, 26 tests (`660c501`, `b225e70`, `9f7c4d0`)
- [x] Fix moderación HARM-12 cerrado — 12 tests adicionales de content guard
- [x] Path traversal guard en `delete_image_service` — `is_relative_to()` valida que el path esté dentro de `media_root` (`3a5818b`)

---

## 5. Verificación post-arranque

```bash
# Health check del backend (vía Nginx)
curl http://localhost/health

# Respuesta esperada:
# {"status": "ok", "qdrant": "ok", "ollama": "warn"}
# ollama aparece "warn" si Ollama no está corriendo en el host — no bloquea el arranque
```

Si `qdrant` aparece como `"warn"`, verificar que `QDRANT_URL` usa el nombre de servicio Docker (`qdrant:6333`), no `localhost`.

---

## 6. Debug — exponer puertos internos

Para inspección sin modificar `docker-compose.prod.yml`, usar el override de debug:

```bash
# Crear backend/docker-compose.debug.yml (ya en .gitignore):
# services:
#   qdrant: { ports: ["127.0.0.1:6333:6333"] }
#   floci:  { ports: ["127.0.0.1:4566:4566"] }
#   app:    { ports: ["127.0.0.1:8000:8000"] }

docker compose -f backend/docker-compose.prod.yml -f backend/docker-compose.debug.yml up -d
```

Con el override activo:
- `http://localhost:6333/dashboard` → Qdrant UI
- `http://localhost:4566` → Floci S3 (usar con AWS CLI)
- `http://localhost:8000/docs` → Swagger del backend

---

*Última actualización: 2026-05-27 (revisado — Storage S3/R2 ya implementado; TLS/GPU cloud añadidos como pendientes)*