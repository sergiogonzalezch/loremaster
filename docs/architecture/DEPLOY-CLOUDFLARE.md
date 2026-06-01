# Deploy Gratuito — Cloudflare Tunnel + R2

Plan para exponer el stack demo desde tu propio equipo sin VPS ni dominio de pago,
usando Cloudflare Tunnel (TLS gratuito) y Cloudflare R2 (storage gratuito).

**Costo total: $0/mes** (o ~$1-3/año si se quiere un dominio propio permanente).

---

## Arquitectura resultante

```
Internet (HTTPS)
    │
    ▼
Cloudflare Edge ← TLS terminado aquí; certificado gratuito
    │
    │  Cloudflare Tunnel (conexión saliente desde tu máquina)
    ▼
cloudflared daemon ─────────────────────────────────────────┐
    │                                                        │
    ▼ HTTP (interno)                                         │
localhost:80 (Docker Nginx)                                  │
    ├── /api/*   → loremaster-api:8000                       │
    └── /*       → React SPA (bundle React)                  │
                                                             │
Tu máquina también aloja:                                    │
    ├── Ollama (LLM texto) en localhost:11434                 │
    └── ComfyUI (imágenes) en localhost:8188  ───────────────┘

Cloudflare R2 (bucket S3-compatible, egress gratuito):
    ← Backend sube imágenes vía boto3
    → Frontend carga imágenes directamente desde R2 public URL
       (no pasa por Nginx ni por el tunnel)
```

**Por qué funciona sin abrir puertos ni tocar el router:**
`cloudflared` hace una conexión HTTPS saliente hacia Cloudflare. El tráfico
entra a tu máquina por ese túnel ya autenticado — sin necesidad de port-forwarding
ni IP pública fija.

---

## Comparativa de opciones de tunnel

| Opción | URL | Persiste al reiniciar | Costo | Ideal para |
|---|---|---|---|---|
| **Quick Tunnel** | `https://<random>.trycloudflare.com` | ❌ Cambia | $0 | Demos puntuales, pruebas |
| **Named Tunnel** (sin dominio) | `https://<uuid>.cfargotunnel.com` | ✅ Fija | $0 | Demo continua (URL fea) |
| **Named Tunnel** (con dominio) | `https://loremaster.tudominio.com` | ✅ Fija | ~$1-3/año | Portafolio permanente |

**Recomendación para portafolio:** Named Tunnel con dominio barato. Porkbun ofrece
`.xyz` desde ~$1/año. No es un requisito — el Quick Tunnel funciona para demos.

---

## Cambios requeridos en el proyecto

El stack ya soporta todo. Solo hay que actualizar variables; **cero cambios de código.**

### 1. `docker-compose.prod.yml` — ya listo ✅

`IMAGE_BACKEND`, `S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
y `S3_BUCKET` ya son interpolables con fallback a Floci. No se toca el compose.

### 2. `.env.production` — actualizaciones necesarias

```bash
# ── URL pública del tunnel (reemplazar con la URL real) ──────────────────────
# Para quick tunnel: la URL que imprime cloudflared al arrancar
# Para named tunnel: https://loremaster.tudominio.com
TUNNEL_URL=https://tu-url.trycloudflare.com

# ── CORS y Clerk ─────────────────────────────────────────────────────────────
ALLOWED_ORIGINS=["https://tu-url.trycloudflare.com"]
CLERK_AUDIENCE=https://tu-url.trycloudflare.com

# ── Cloudflare R2 ────────────────────────────────────────────────────────────
S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
S3_BUCKET=loremaster-media
S3_REGION=auto
AWS_ACCESS_KEY_ID=<r2-access-key>
AWS_SECRET_ACCESS_KEY=<r2-secret-key>

# URL pública del bucket R2 (habilitar "Public Access" en el dashboard R2)
# Formato: https://pub-<token>.r2.dev  o  https://media.tudominio.com (custom domain R2)
STORAGE_BASE_URL=https://pub-<token>.r2.dev
```

> **Nota sobre `STORAGE_BASE_URL`:** con R2, las imágenes se sirven directamente
> desde la URL pública de R2, no a través del tunnel ni de Nginx. El bucket necesita
> tener "Allow Access" habilitado en el dashboard de Cloudflare R2.

### 3. Rebuild del frontend (una sola vez por cambio de URL)

`ALLOWED_ORIGINS` y `CLERK_AUDIENCE` son runtime (solo reiniciar el backend).
Pero si cambia la URL del tunnel con un Quick Tunnel, hay que actualizar `.env.production`
y reiniciar el stack. Con Named Tunnel la URL es fija — esto no aplica.

```bash
# Si Clerk publishable key o API base URL cambian:
make prod-rebuild-fe   # rebuildea bundle con nuevas VITE_* vars

# Si solo cambian vars de backend (ALLOWED_ORIGINS, CLERK_AUDIENCE, R2 creds):
make prod-down && make prod-up
```

### 4. Clerk dashboard — actualizar allowed URLs

En el dashboard de Clerk (optimum-tuna-92.clerk.accounts.dev):
- **Authorized redirect URLs**: añadir `https://tu-url.trycloudflare.com`
- **Allowed origins for JWT**: añadir `https://tu-url.trycloudflare.com`

> Con `pk_test_` (clave actual) Clerk acepta cualquier origen en modo test.
> Con `pk_live_` (modo producción real) requiere que el dominio esté verificado
> en el dashboard y solo funciona con Named Tunnel + dominio.

---

## Guía de setup paso a paso

### Fase 0 — Prerrequisitos (~30 min, una sola vez)

```bash
# 1. Instalar cloudflared (Windows — PowerShell como Admin)
winget install Cloudflare.cloudflared
# O descargar el .exe desde: https://github.com/cloudflare/cloudflared/releases

# 2. Verificar instalación
cloudflared --version
```

En Cloudflare dashboard (cloudflare.com):
1. Crear cuenta gratuita
2. Ir a **R2** → Create bucket → nombre: `loremaster-media`
3. En el bucket creado → Settings → **Public Access** → Allow Access ✅
4. Ir a **R2** → API Tokens → Create Token (permisos: Object Read + Write para `loremaster-media`)
5. Guardar `Access Key ID` y `Secret Access Key`
6. Anotar la **Account ID** (en la barra lateral derecha del dashboard)

Con esos datos ya puedes construir:
```
S3_ENDPOINT_URL = https://<Account ID>.r2.cloudflarestorage.com
STORAGE_BASE_URL = https://pub-<token>.r2.dev   ← aparece en bucket → Settings → Public URL
```

---

### Fase 1 — Activar R2 como storage (~10 min)

```bash
# Actualizar .env.production con las credenciales R2 (ver sección anterior)
# Verificar que las vars se resuelven correctamente:
docker compose -f backend/docker-compose.prod.yml --env-file .env.production config

# Levantar (o reiniciar) el stack:
make prod-down && make prod-up

# Probar: subir una imagen desde la app y verificar que la URL pública de R2 funciona
```

Si todo va bien, las imágenes nuevas se guardarán en R2 y se servirán desde
`https://pub-<token>.r2.dev/<path>`. Las imágenes antiguas (en Floci) dejan de
ser accesibles — solo afecta a una demo fresca, lo cual es el caso habitual.

---

### Fase 2 — Exponer el stack con Cloudflare Tunnel (~15 min)

#### Opción A — Quick Tunnel (cero configuración, URL temporal)

```bash
# Con el stack ya corriendo en localhost:80:
cloudflared tunnel --url http://localhost:80

# Output de ejemplo:
# https://fancy-name-abc123.trycloudflare.com
```

Esa URL ya tiene HTTPS y es accesible desde internet. Copiarla y:
1. Actualizar `ALLOWED_ORIGINS` y `CLERK_AUDIENCE` en `.env.production`
2. `make prod-down && make prod-up`
3. Añadir URL en Clerk dashboard → Authorized redirect URLs

**Limitación:** la URL cambia cada vez que reinicias `cloudflared`.

---

#### Opción B — Named Tunnel (URL fija, requiere dominio en Cloudflare)

```bash
# 1. Login con cuenta Cloudflare
cloudflared tunnel login

# 2. Crear tunnel (una sola vez)
cloudflared tunnel create loremaster
# Output: tunnel ID UUID, ej: a1b2c3d4-...

# 3. Crear config (guardar como %USERPROFILE%\.cloudflared\config.yml en Windows)
```

```yaml
# config.yml
tunnel: <tunnel-uuid>
credentials-file: C:\Users\<user>\.cloudflared\<tunnel-uuid>.json

ingress:
  - hostname: loremaster.tudominio.com
    service: http://localhost:80
  - service: http_status:404
```

```bash
# 4. Enrutar el dominio al tunnel (dominio debe estar en Cloudflare DNS)
cloudflared tunnel route dns loremaster loremaster.tudominio.com

# 5. Arrancar el tunnel
cloudflared tunnel run loremaster

# Para que arranque con Windows: registrar como servicio
cloudflared service install
```

---

### Fase 3 — Verificar el deploy completo

```bash
# Health check vía tunnel
curl https://tu-url.trycloudflare.com/health
# Esperado: {"status": "ok", "qdrant": "ok", "ollama": "ok"}

# Verificar que el frontend carga
# Abrir en navegador: https://tu-url.trycloudflare.com
```

Checklist:
- [ ] Frontend carga correctamente
- [ ] Login con Clerk funciona
- [ ] Subida de documento funciona
- [ ] Imagen generada aparece desde URL de R2 (no `/media/`)
- [ ] Cerrar sesión y volver a entrar funciona

---

## Limitaciones conocidas

| Limitación | Impacto | Mitigación |
|---|---|---|
| Máquina debe estar encendida | App offline si apaga el PC | Aceptable para demo de portafolio |
| Quick Tunnel: URL cambia al reiniciar | Necesitas actualizar config y Clerk | Usar Named Tunnel para demo permanente |
| Ollama/ComfyUI deben estar corriendo | Sin LLM/imágenes si no están activos | Documentar prerequisitos en README del portafolio |
| Ancho de banda del ISP | Limitado por upload de tu conexión | Irrelevante para 1-5 usuarios |
| R2 free tier: 10 GB + 1M ops | Muy holgado para demo | Sin acción requerida |
| Cloudflare Tunnel: 50 req/s gratis | Más que suficiente para demo | Sin acción requerida |

---

## Comparativa final vs VPS

| | Este plan (Cloudflare) | VPS mínimo (Hetzner CX22) |
|---|---|---|
| **Costo mensual** | **$0** | ~$4.90 |
| **Hardware** | Tu máquina | Servidor remoto |
| **Uptime** | Cuando tu PC está encendido | 24/7 |
| **Setup** | ~1 hora | ~2 horas + mantenimiento |
| **Validez para portafolio** | ✅ Sí | ✅ Sí |
| **Escalabilidad** | Tu máquina | Fácil de escalar |
| **IP pública** | No requerida | Incluida |

Para un portafolio técnico donde el evaluador agenda una demo o accede bajo demanda,
este plan es completamente válido. No requiere que la app esté online las 24h.

---

## Actualizar checklist de DEPLOY.md tras activar este plan

Cuando completes la Fase 3 del setup, marcar en `DEPLOY.md §4 Checklist pre-deploy`:
- [ ] `ALLOWED_ORIGINS=["https://tu-url"]` ✅ (actualizar con URL real)
- [ ] `STORAGE_BASE_URL=https://pub-xxx.r2.dev` ✅ (URL pública R2)
- [ ] Credenciales R2 en `.env.production` ✅
- [ ] Cloudflare Tunnel corriendo ✅ (TLS resuelto — sin cambios en nginx.conf)

---

*Creado: 2026-06-01. Ver también: `DEPLOY.md` (runbook operacional), `ENV-ARCHITECTURE.md` (flujo de variables), `COST-REPORT.md` (estimaciones de costo).*
