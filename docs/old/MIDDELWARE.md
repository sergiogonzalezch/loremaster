## Auditoría de Middlewares de Seguridad

### Rate Limiting — `rate_limit.py`

#### Problema crítico: un solo bucket para todos los endpoints costosos

El endpoint `POST /collections/{id}/query` (RAG + Ollama, potencialmente 5–60s por llamada) comparte el mismo límite de 30 req/min que un `DELETE` trivial. Un usuario autenticado puede lanzar 30 llamadas LLM por minuto por diseño, saturando el semáforo de Ollama (`max_concurrent_llm_calls=1`) con una cola de 29 peticiones pendientes.

#### Problema alto: JWT sin verificar permite bypass

```python
# rate_limit.py:100-106
def _extract_user_from_token(self, token: str) -> str | None:
    try:
        parts = token.split(".")
        if len(parts) >= 2:
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
            return payload.get("sub")  # ← sin verificar firma
```

El payload se decodifica sin verificar la firma. Un atacante puede forjar tokens con `sub` distintos en cada request para evadir el rate limit por usuario. El límite efectivo cae a IP-based, que es fácil de rotar.

#### Problema alto: no es async-safe con múltiples workers

```python
# rate_limit.py:124
with self.lock:  # threading.Lock, no asyncio.Lock
```

`threading.Lock` bloquea el hilo OS pero no es compatible con el event loop de asyncio correctamente bajo carga. Más crítico: con `uvicorn --workers N`, cada proceso tiene su propio `dict` — el límite efectivo es **30 × N por minuto** por usuario.

#### Problema medio: memory leak en el dict de requests

```python
# rate_limit.py:41
self.requests: dict[str, list[float]] = {}
```

Las entradas solo se limpian cuando el mismo usuario hace un nuevo request. Un flood de IPs únicas o user IDs falsos (aprovechando el punto anterior) puede agotar la RAM del proceso.

#### Problema bajo: GET no está limitado

Los endpoints GET que invocan embeddings o consultas Qdrant costosas no están cubiertos. Menor, pero a tener en cuenta si se añaden GETs que llamen a servicios externos.

---

### Security Headers — `security_headers.py`

#### Problema alto: HSTS nunca se envía detrás de un proxy

```python
# security_headers.py:48
if request.url.scheme == "https":
    response.headers["Strict-Transport-Security"] = ...
```

Si hay un reverse proxy (Nginx, Caddy, Cloudflare) que termina TLS, FastAPI recibe la petición como `http://` y **nunca establece HSTS**. Hay que usar `ProxyHeadersMiddleware` de Starlette o confiar en el header `X-Forwarded-Proto`.

#### Problema medio: `unsafe-inline` en script-src (HTTP) y style-src (ambos)

```python
# security_headers.py:65 (HTTP)
"script-src 'self' 'unsafe-inline'; "
# security_headers.py:54, 57 (HTTPS — style-src)
"style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
```

`script-src 'unsafe-inline'` en HTTP anula completamente la protección XSS de la CSP. En HTTPS está bien que no esté, pero `style-src 'unsafe-inline'` permite CSS injection. Si el frontend usa CSS-in-JS con nonces, esto puede eliminarse.

#### Problema medio: `img-src http:` en HTTP es demasiado permisivo

```python
# security_headers.py:67 (HTTP)
"img-src 'self' data: blob: http:; "
```

Permite cargar imágenes desde cualquier origen HTTP. En desarrollo es tolerable, pero si alguna vez se usa `environment=demo` con HTTP, quedaría expuesto.

#### Headers faltantes para producción

| Header | Valor recomendado | Impacto |
|--------|-------------------|---------|
| `HSTS preload` | `max-age=31536000; includeSubDomains; preload` | Sin `preload`, la primera visita puede ser interceptada (SSL stripping) |
| `Cache-Control` | `no-store` | Respuestas de API autenticadas pueden cachearse en proxies intermedios |
| `Cross-Origin-Opener-Policy` | `same-origin` | Protección contra ataques Spectre cross-window |
| `Cross-Origin-Resource-Policy` | `same-origin` | Previene que otros orígenes incrusten respuestas de la API |
| `Permissions-Policy` | Añadir `payment=(), usb=(), display-capture=()` | La política actual es incompleta |

---

### Configuración — demasiado permisiva para producción

#### `cookie_secure: bool = False` como default

```python
# config/__init__.py:142
cookie_secure: bool = False  # True en producción/demo (HTTPS)
```

Si `ENVIRONMENT` no se define explícitamente en producción (y el código ya tiene un `warnings.warn` para ese caso), las cookies JWT se enviarán sin el flag `Secure`. La validación del `model_validator` no cubre este caso — solo valida CORS y SECRET_KEY.

#### `PUT` ausente en CORS

```python
# main.py:105
allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
```

`PUT` está ausente. Si algún cliente externo o herramienta usa PUT, fallará silenciosamente con un error CORS en lugar de un 405 claro.

---

### Resumen de prioridades

| Prioridad | Ítem | Archivo |
|-----------|------|---------|
| Crítico | Rate limit separado para endpoints LLM | `rate_limit.py` + rutas RAG/imagen |
| Alto | JWT sin verificar en rate limiter | `rate_limit.py:100-106` |
| Alto | HSTS inoperativo detrás de proxy | `security_headers.py:48` + `main.py` |
| Alto | In-memory dict no distribuido | `rate_limit.py:41` |
| Medio | `unsafe-inline` en CSP | `security_headers.py:65` |
| Medio | Memory leak en dict de requests | `rate_limit.py:41` |
| Medio | `Cache-Control: no-store` ausente | `security_headers.py` |
| Bajo | `COOP`/`CORP` faltantes | `security_headers.py` |
| Bajo | `cookie_secure` default `False` | `config/__init__.py:142` |

---

## Validación contra código fuente

> Revisión realizada el 2026-05-17 sobre `rate_limit.py`, `security_headers.py`, `config/__init__.py` y `main.py`.

| # | Issue | Estado | Nota |
|---|-------|--------|------|
| 1 | Un bucket para todos los endpoints LLM | ✅ Confirmado | `RateLimitMiddleware.__init__` acepta un solo `requests_per_minute`; misma ventana para RAG y DELETE |
| 2 | JWT sin verificar firma | ✅ Confirmado | `_extract_user_from_token` hace `base64.urlsafe_b64decode` sin `jwt.decode()` |
| 3 | threading.Lock + multi-workers | ✅ Confirmado (multi-worker) · ⚠️ Matiz: `threading.Lock` es correcto en asyncio sin `await` dentro del bloque; el problema real es el dict por proceso |
| 4 | Memory leak en dict | ✅ Confirmado | Limpieza solo al re-visitar; sin TTL ni límite de tamaño |
| 5 | GET no limitado | ✅ Confirmado | Línea 66: bypass explícito de GET/HEAD/OPTIONS |
| 6 | HSTS inoperativo detrás de proxy | ✅ Confirmado | `request.url.scheme` refleja HTTP cuando hay proxy TLS; sin ProxyHeadersMiddleware ni X-Forwarded-Proto |
| 7 | `unsafe-inline` en CSP | ✅ Confirmado | `script-src` en HTTP y `style-src` en ambos modos |
| 8 | `img-src http:` permisivo | ✅ Confirmado | Solo en CSP HTTP |
| 9 | Headers faltantes | ✅ Confirmado | HSTS falta `; preload`; Cache-Control, COOP, CORP ausentes; Permissions-Policy incompleta |
| 10 | `cookie_secure=False` sin validación en producción | ✅ Confirmado | `model_validator` no cubre este caso |
| 11 | `PUT` ausente en CORS | ✅ Confirmado | `main.py:105`; impacto actual nulo (no hay rutas PUT), riesgo futuro |

**Dependencias disponibles** — `python-jose[cryptography]==3.5.0` y `redis==7.4.0` ya están en `requirements.txt`; Redis corre en `docker-compose.yml:38` en `127.0.0.1:6379`. No se necesita añadir nuevas librerías.

---

## Plan de corrección

### Principios
- Cada fase puede commitearse y desplegarse de forma independiente.
- El orden dentro de cada fase respeta las dependencias entre fixes.
- La Fase 3 (Redis) es la más invasiva; las Fases 1 y 2 pueden ejecutarse sin ella.
- No se añaden nuevas dependencias: `python-jose` y `redis` ya existen.

---

### Fase 1 — Correcciones de alto impacto y bajo riesgo (1 commit)

Fixes atómicos que no cambian la interfaz del middleware ni requieren infraestructura nueva.

#### Fix A · JWT verificado en `_extract_user_from_token`

**Archivo:** `app/api/middlewares/rate_limit.py`

Reemplazar la decodificación manual por `jwt.decode()` con la clave secreta. Un token forjado lanzará `JWTError` y caerá al fallback por IP — comportamiento idéntico al actual para tokens inválidos, pero sin la ventana de bypass.

```python
# Eliminar: import base64, json (si no se usan en otro sitio)
# Añadir:
from jose import JWTError, jwt as jose_jwt

def _extract_user_from_token(self, token: str) -> str | None:
    try:
        payload = jose_jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload.get("sub")
    except (JWTError, Exception):
        return None
```

**Criterio de aceptación:** un token con payload `{"sub": "attacker"}` sin firma válida cae a IP-based limiting.

---

#### Fix B · HSTS detrás de proxy — X-Forwarded-Proto

**Archivo:** `app/api/middlewares/security_headers.py`

Leer `X-Forwarded-Proto` además de `request.url.scheme`. Esto cubre la topología proxy más común (Nginx/Cloudflare terminando TLS) sin añadir middleware extra.

```python
forwarded_proto = request.headers.get("x-forwarded-proto", "")
is_https = request.url.scheme == "https" or forwarded_proto == "https"

if is_https:
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains; preload"
    )
    csp = ...  # rama HTTPS actual
else:
    csp = ...  # rama HTTP actual
```

> **Nota sobre `preload`:** añadir `;preload` implica que el dominio puede incluirse en los preload lists de los navegadores (irreversible). Solo activar si el dominio estará siempre en HTTPS. Si hay duda, omitir `preload` en este fix y dejarlo para cuando el dominio esté consolidado.

**Criterio de aceptación:** con `X-Forwarded-Proto: https` en el request, la respuesta incluye el header `Strict-Transport-Security`.

---

#### Fix C · `cookie_secure` forzado en producción/demo

**Archivo:** `app/core/config/__init__.py`

Añadir validación en `_validate_cors` que impida arrancar con `cookie_secure=False` en entornos `production` o `demo`.

```python
if self.environment in ("production", "demo") and not self.cookie_secure:
    raise ValueError(
        "COOKIE_SECURE debe ser True en entornos production/demo. "
        "Añade COOKIE_SECURE=true al .env de producción."
    )
```

**Criterio de aceptación:** `Settings()` lanza `ValueError` si `ENVIRONMENT=production` y `COOKIE_SECURE` no está en `.env` o es `false`.

---

#### Fix D · `PUT` en CORS

**Archivo:** `app/main.py`

```python
allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
```

Cambio de una palabra. No hay rutas PUT activas, pero elimina la trampa silenciosa para futuras adiciones.

---

### Fase 2 — Hardening de headers (1 commit)

Todos los cambios son en `security_headers.py`. Sin dependencias de Fase 1.

#### Fix E · Eliminar `unsafe-inline` de `script-src` en HTTP

```python
# Antes:
"script-src 'self' 'unsafe-inline'; "
# Después:
"script-src 'self'; "
```

El frontend (Vite) no emite scripts inline en producción. En local/dev el navegador puede quejarse de scripts inline en hot-reload, pero el servidor de Vite sirve su propia CSP y esto no aplica.

---

#### Fix F · Añadir headers ausentes

```python
response.headers["Cache-Control"] = "no-store"
response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
# Reemplazar Permissions-Policy actual:
response.headers["Permissions-Policy"] = (
    "geolocation=(), microphone=(), camera=(), "
    "payment=(), usb=(), display-capture=()"
)
```

`Cache-Control: no-store` se añade incondicionalmente (todas las rutas son API autenticada). `COOP` y `CORP` protegen contra ataques cross-window (Spectre) sin romper nada.

---

#### Fix G · Restringir `img-src` en HTTP

```python
# Antes (HTTP):
"img-src 'self' data: blob: http:; "
# Después:
"img-src 'self' data: blob:; "
```

Elimina la comodín `http:`. Las imágenes en local se sirven desde `localhost` que cae en `'self'`.

---

### Fase 3 — Rate limiter distribuido con Redis (1-2 commits)

Esta fase resuelve los problemas de multi-worker (Fix #3) y memory leak (Fix #4), y habilita los límites diferenciados (Fix #1). Requiere que Redis esté disponible (`REDIS_URL` en `.env`; ya corre en `docker-compose.yml`).

#### Fix H · Migrar backend a Redis con ventana deslizante atómica

**Archivo:** `app/api/middlewares/rate_limit.py`

Usar `redis.asyncio` (incluido en `redis==7.4.0`) con un sorted set por usuario. Cada entrada es un timestamp; las entradas fuera de la ventana de 60s se expiran atómicamente con `ZREMRANGEBYSCORE`.

```python
import redis.asyncio as aioredis
from app.core.config import settings

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, requests_per_minute: int = 30) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.redis: aioredis.Redis = aioredis.from_url(
            settings.redis_url, decode_responses=True
        )

    async def _check_rate_limit(self, user_id: str, limit: int) -> bool:
        now = time.time()
        window_start = now - 60
        key = f"rl:{user_id}"

        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, 61)
            results = await pipe.execute()

        count: int = results[2]
        return count <= limit
```

Esto elimina:
- El `threading.Lock` (Redis es atómico por diseño).
- El dict en memoria (el estado vive en Redis, compartido entre workers).
- El memory leak (Redis expira las claves a los 61s automáticamente).

**Precondición:** añadir `redis_url: str = "redis://localhost:6379"` a `Settings`.

---

#### Fix I · Límites diferenciados por endpoint

**Archivo:** `app/api/middlewares/rate_limit.py` + `app/core/config/__init__.py`

Definir un mapa de paths costosos con su límite específico, configurable via settings.

```python
# En Settings:
rate_limit_llm_per_minute: int = 5    # RAG + Ollama
rate_limit_image_per_minute: int = 3  # Image generation

# En RateLimitMiddleware:
EXPENSIVE_PATHS: dict[str, str] = {
    "/api/v1/collections/": "llm",      # POST query
    "/api/v1/image-generation/": "image",
}

def _get_limit(self, path: str) -> int:
    for prefix, tier in EXPENSIVE_PATHS.items():
        if prefix in path:
            return getattr(settings, f"rate_limit_{tier}_per_minute")
    return self.requests_per_minute
```

El límite LLM de 5 req/min satura el semáforo de Ollama (`max_concurrent_llm_calls=1`) con solo 4 llamadas en cola en el peor caso, en lugar de 29.

---

### Orden de implementación recomendado

```
Fase 1 (A+B+C+D) → Fase 2 (E+F+G) → Fase 3 (H → I)
```

Fase 1 y Fase 2 son independientes entre sí y pueden ejecutarse en paralelo o en orden inverso. Fase 3 depende de que Redis esté disponible en el entorno de despliegue.

### Archivos afectados

| Archivo | Fixes |
|---------|-------|
| `app/api/middlewares/rate_limit.py` | A, H, I |
| `app/api/middlewares/security_headers.py` | B, E, F, G |
| `app/core/config/__init__.py` | C, H (redis_url) |
| `app/main.py` | D |