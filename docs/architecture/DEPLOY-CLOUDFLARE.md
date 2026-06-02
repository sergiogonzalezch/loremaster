# Deploy Gratuito — Cloudflare Tunnel + R2

Exponer el stack demo desde tu propio equipo sin VPS ni dominio,
usando Cloudflare Tunnel (TLS gratuito) y Cloudflare R2 (storage gratuito).

**Costo total: $0/mes**

---

## Estado actual

| Paso | Estado |
|---|---|
| Fase 0 — Instalar `cloudflared` + crear bucket R2 | ✅ completo (2026-06-02) |
| Fase 1 — Activar R2 como storage | ✅ completo (2026-06-02) |
| Fase 2 — Exponer stack con Quick Tunnel | ✅ completo (2026-06-02) |
| Fase 3 — Actualizar config + verificar | ✅ completo (2026-06-02) |

---

## Arquitectura

```
Internet (HTTPS)
    ↓ Cloudflare Edge — TLS gratuito terminado aquí
    ↓ Cloudflare Tunnel (conexión saliente — sin abrir puertos)
localhost:80 (Docker Nginx)
    ├── /api/*  → loremaster-api:8000
    └── /*      → React SPA bundle

Cloudflare R2 (S3-compatible, egress gratuito):
    ← Backend sube imágenes vía boto3
    → Frontend carga imágenes desde URL pública R2 directamente
       (no pasa por Nginx ni por el tunnel)

Tu máquina también aloja:
    ├── Ollama en localhost:11434
    └── ComfyUI en localhost:8188
```

`cloudflared` hace una conexión HTTPS **saliente** hacia Cloudflare.
Sin port-forwarding, sin IP pública fija, sin tocar el router.

---

## Opción de tunnel elegida: Quick Tunnel

| Opción | URL | Persiste al reiniciar | Costo |
|---|---|---|---|
| **Quick Tunnel** ← **esta** | `https://<random>.trycloudflare.com` | ❌ cambia | $0 |
| Named Tunnel (con dominio) | `https://tudominio.com` | ✅ fija | ~$1-3/año |

Quick Tunnel es suficiente para demo de portafolio bajo demanda.
La URL cambia al reiniciar `cloudflared` — se actualiza config en ~5 min antes de cada demo.

---

## Cambios necesarios en el proyecto

**Cero cambios de código.** Solo variables en `.env.production`.

`docker-compose.prod.yml` ya tiene todo interpolable con fallback a Floci:
`S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET` ✅

---

## Fase 0 — Prerrequisitos (una sola vez)

### Instalar cloudflared

```powershell
# PowerShell como Admin
winget install Cloudflare.cloudflared

# Verificar
cloudflared --version
```

### Crear bucket R2 en Cloudflare dashboard

1. Crear cuenta gratuita en cloudflare.com
2. Menú lateral → **R2 Object Storage** → **Create bucket**
   - Nombre: `loremaster-media`
   - Región: Automatic
3. Entrar al bucket → pestaña **Settings** → **Public Access** → **Allow Access** ✅
4. Anotar la **Public Bucket URL** → formato: `https://pub-<token>.r2.dev`

### Crear API Token para el bucket

1. Menú lateral → **R2** → **Manage R2 API Tokens** → **Create API Token**
2. Permisos: `Object Read & Write`
3. Scope: `Specific bucket` → `loremaster-media`
4. Guardar:
   - `Access Key ID` → será `AWS_ACCESS_KEY_ID`
   - `Secret Access Key` → será `AWS_SECRET_ACCESS_KEY`

### Anotar Account ID

Dashboard → barra lateral derecha → **Account ID**
Construye el endpoint S3: `https://<Account ID>.r2.cloudflarestorage.com`

---

## Fase 1 — Activar R2 como storage

Editar `.env.production` añadiendo/actualizando estas líneas:

```bash
# Storage — Cloudflare R2
S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
S3_BUCKET=loremaster-media
S3_REGION=auto
AWS_ACCESS_KEY_ID=<r2-access-key>
AWS_SECRET_ACCESS_KEY=<r2-secret-key>
STORAGE_BASE_URL=https://pub-<token>.r2.dev
```

Verificar y reiniciar:

```bash
# Verificar que las vars se interpolan correctamente
docker compose -f backend/docker-compose.prod.yml --env-file .env.production config | grep -E "S3|STORAGE|AWS"

# Reiniciar stack
make prod-down && make prod-up
```

Prueba: generar o subir una imagen en la app → verificar que la URL
resultante apunta a `https://pub-<token>.r2.dev/...`.

---

## Fase 2 — Exponer el stack con Quick Tunnel

Con el stack corriendo en `localhost:80`:

```powershell
cloudflared tunnel --url http://localhost:80
```

Output esperado:
```
2026-06-01T... INF Thank you for trying Cloudflare Tunnel. Doing so, ...
2026-06-01T... INF +-------------------------------------------------------+
2026-06-01T... INF |  Your quick Tunnel has been created! Visit it at      |
2026-06-01T... INF |  https://fancy-octopus-abc123.trycloudflare.com       |
2026-06-01T... INF +-------------------------------------------------------+
```

Copiar esa URL — la necesitas para la Fase 3.
Dejar el proceso corriendo en esa terminal mientras dure la demo.

---

## Fase 3 — Actualizar config con la URL del tunnel

### 1. Actualizar `.env.production`

```bash
ALLOWED_ORIGINS=["https://fancy-octopus-abc123.trycloudflare.com"]
CLERK_AUDIENCE=https://fancy-octopus-abc123.trycloudflare.com
```

### 2. Reiniciar el backend con la nueva config

```bash
make prod-down && make prod-up
```

### 3. Actualizar Clerk dashboard

En [dashboard.clerk.com](https://dashboard.clerk.com) → tu app → **Configure** → **Domains**:
- Añadir `https://fancy-octopus-abc123.trycloudflare.com` como dominio permitido

> Con `pk_test_` (clave actual) Clerk es permisivo con los orígenes en modo test,
> pero añadirlo en el dashboard evita warnings en los logs.

### 4. Verificar

```bash
curl https://fancy-octopus-abc123.trycloudflare.com/health
# Esperado: {"status": "ok", "qdrant": "ok", "ollama": "ok"}
```

Checklist final:
- [ ] Frontend carga desde la URL del tunnel
- [ ] Login con Clerk funciona
- [ ] Subida de documento funciona
- [ ] Imagen generada tiene URL de R2 (`pub-xxx.r2.dev/...`)
- [ ] Cerrar sesión y volver a entrar funciona

---

## Flujo para cada demo (una vez configurado)

```
1. make prod-up                                     (~2 min)
2. cloudflared tunnel --url http://localhost:80      (~30 s → URL)
3. Actualizar ALLOWED_ORIGINS + CLERK_AUDIENCE       (~1 min)
4. make prod-down && make prod-up                   (~2 min)
5. Compartir URL con el evaluador
```

Total: ~5-6 min de setup antes de cada sesión.
Si el dominio queda igual entre sesiones (raro), se saltan los pasos 3 y 4.

---

## Limitaciones

| Limitación | Impacto | Estado |
|---|---|---|
| Máquina debe estar encendida | App offline si apaga el PC | Aceptable para demo bajo demanda |
| URL cambia al reiniciar tunnel | ~5 min de reconfig | Aceptable para portafolio |
| Ollama/ComfyUI deben estar corriendo | Sin LLM/imágenes si no están activos | Prerequisito documentado |
| Upload del ISP | Limita velocidad de transferencia | Irrelevante para 1-5 usuarios |
| R2 free tier: 10 GB + 1M ops/mes | Muy holgado para demo | Sin acción |
| Cloudflare Tunnel free: 50 req/s | Más que suficiente | Sin acción |

---

## Actualizar DEPLOY.md tras completar

Cuando la Fase 3 esté completa, marcar en `DEPLOY.md §4 Checklist pre-deploy`:
- [ ] `ALLOWED_ORIGINS=["https://tu-url"]` con URL del tunnel
- [ ] `STORAGE_BASE_URL=https://pub-xxx.r2.dev` con URL pública R2
- [ ] Credenciales R2 en `.env.production`
- [ ] Cloudflare Tunnel activo (TLS resuelto sin cambios en `nginx.conf`)

---

*Actualizado: 2026-06-01. Ver también: `DEPLOY.md` (runbook operacional), `ENV-ARCHITECTURE.md` (flujo de variables), `COST-REPORT.md` (estimaciones de costo).*
