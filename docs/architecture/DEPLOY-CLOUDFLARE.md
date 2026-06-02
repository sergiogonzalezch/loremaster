# Deploy Gratuito — Cloudflare Tunnel + R2

Exponer el stack demo desde tu propio equipo con URL fija y TLS gratuito,
usando Cloudflare Named Tunnel y Cloudflare R2 (storage gratuito).

**Costo total: ~$1.98/año** (dominio `loremasterai.site` en Namecheap)

---

## Estado actual

| Paso | Estado |
|---|---|
| Fase 0 — Instalar `cloudflared` + crear bucket R2 | ✅ completo (2026-06-02) |
| Fase 1 — Activar R2 como storage | ✅ completo (2026-06-02) |
| Fase 2 — Exponer stack con Quick Tunnel | ✅ completo (2026-06-02) |
| Fase 3 — Actualizar config + verificar | ✅ completo (2026-06-02) |
| Fase 4 — Named Tunnel con dominio fijo `loremasterai.site` | ✅ completo (2026-06-02) |

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

## Tunnel activo: Named Tunnel con dominio fijo

| Opción | URL | Persiste al reiniciar | Costo |
|---|---|---|---|
| ~~Quick Tunnel~~ | `https://<random>.trycloudflare.com` | ❌ cambia | $0 |
| **Named Tunnel** ← **activo** | `https://loremasterai.site` | ✅ fija | ~$1.98/año |

URL permanente — no requiere reconfiguración entre sesiones de demo.

### Configuración del Named Tunnel

- Tunnel ID: en `~/.cloudflared/<tunnel-id>.json` (generado por `cloudflared tunnel create`)
- Credentials: `%USERPROFILE%\.cloudflared\<tunnel-id>.json` — **no compartir**
- Config: `%USERPROFILE%\.cloudflared\config.yml`
- DNS: CNAME `loremasterai.site` → tunnel (gestionado por Cloudflare)

```yaml
# %USERPROFILE%\.cloudflared\config.yml
tunnel: <tunnel-id>
credentials-file: %USERPROFILE%\.cloudflared\<tunnel-id>.json

ingress:
  - hostname: loremasterai.site
    service: http://localhost:80
  - service: http_status:404
```

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

## Fase 2 — Exponer el stack con Quick Tunnel ✅ (superado por Fase 4)

~~Con el stack corriendo en `localhost:80`:~~
~~`cloudflared tunnel --url http://localhost:80`~~

Esta fase fue el punto de partida. Reemplazada por el Named Tunnel en Fase 4.

---

## Fase 3 — Actualizar config con la URL del tunnel ✅

Variables activas en `.env.production`:

```bash
ALLOWED_ORIGINS=["https://loremasterai.site"]
CLERK_AUDIENCE=https://loremasterai.site
```

> Con `pk_test_` Clerk es permisivo — login funciona sin añadir el dominio
> en el dashboard. Para producción real: crear instancia de producción en Clerk
> y obtener claves `pk_live_`.

### Verificar

```bash
curl https://loremasterai.site/health
# Esperado: {"status":"healthy","services":{...}}
```

Checklist final:
- [x] Frontend carga desde `https://loremasterai.site`
- [x] Login con Clerk funciona
- [x] Subida de documento funciona
- [x] Imagen generada tiene URL de R2 (`https://pub-<r2-token>.r2.dev/...`)
- [x] Cerrar sesión y volver a entrar funciona

---

## Fase 4 — Named Tunnel con dominio fijo ✅ (2026-06-02)

### Setup (ya realizado — referencia)

```powershell
# 1. Login
cloudflared tunnel login

# 2. Crear tunnel
cloudflared tunnel create loremaster
# → genera credentials en ~/.cloudflared/<id>.json

# 3. Apuntar DNS
cloudflared tunnel route dns loremaster loremasterai.site

# 4. Crear config.yml (ver sección anterior)

# 5. Arrancar
cloudflared tunnel --config "%USERPROFILE%\.cloudflared\config.yml" run loremaster
```

### Dominio
- Registrado en Namecheap: `loremasterai.site`
- Nameservers apuntando a Cloudflare (asignados al activar el dominio en Cloudflare dashboard)
- CNAME en Cloudflare DNS apunta al tunnel (proxied)

---

## Flujo para cada demo (Named Tunnel activo)

```
1. make prod-up                                                          (~2 min)
2. cloudflared tunnel --config "%USERPROFILE%\.cloudflared\config.yml" run loremaster
3. Compartir https://loremasterai.site con el evaluador
```

Total: ~2-3 min. URL siempre la misma — sin reconfiguración.

---

## Limitaciones

| Limitación | Impacto | Estado |
|---|---|---|
| Máquina debe estar encendida | App offline si apaga el PC | Aceptable para demo bajo demanda |
| ~~URL cambia al reiniciar tunnel~~ | ~~5 min de reconfig~~ | ✅ Resuelto — Named Tunnel con `loremasterai.site` |
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

*Actualizado: 2026-06-02. Named Tunnel activo en `loremasterai.site`. Ver también: `DEPLOY.md` (runbook operacional), `ENV-ARCHITECTURE.md` (flujo de variables), `COST-REPORT.md` (estimaciones de costo).*
