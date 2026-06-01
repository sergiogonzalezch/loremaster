# Plan — Prueba de Despliegue con Storage S3-Compatible

Referencia de implementación para reemplazar el almacenamiento local por un backend S3-compatible.
Cubre tres opciones: MinIO (recomendado para dev/demo), Floci (emulador AWS ligero, reemplaza
LocalStack Community que quedó obsoleto en marzo 2026), y Cloudflare R2 (producción real).

---

## Estado actual

El backend usa almacenamiento en filesystem local:

```
STORAGE_BACKEND=local
MEDIA_ROOT=./media
STORAGE_BASE_URL=http://localhost:8000/media
```

`core/storage/__init__.py` escribe bytes directamente en disco. No hay cliente S3.
Las imágenes generadas no sobreviven un restart del contenedor sin un volumen montado.

---

## Opciones

| | Floci | MinIO | Cloudflare R2 |
|---|---|---|---|
| Tipo | Emulador AWS completo (52 servicios) | S3-compatible independiente | S3-compatible en nube |
| Docker image | `floci/floci:latest` (90 MB) | `minio/minio` (~200 MB) | N/A |
| Puerto S3 | 4566 | 9000 | — |
| Consola web | No | Sí (port 9001) | Sí (dashboard web) |
| Auth token | No requerido | Credenciales propias | API key Cloudflare |
| Uso recomendado | Validar integración boto3/AWS SDK | Dev + producción pequeña | Producción real |
| Egress cost | N/A (local) | N/A (local) | Gratuito |

**Recomendación:** MinIO para dev/demo, Floci para validar el SDK boto3 contra un emulador AWS
completo, Cloudflare R2 para producción real.

---

## Opción A — MinIO (recomendada para dev/demo)

### Paso 1 — Añadir MinIO a `docker-compose.prod.yml`

```yaml
  minio:
    image: minio/minio:latest
    container_name: loremaster-minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-loremaster}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:?MINIO_ROOT_PASSWORD requerida}
    ports:
      - "127.0.0.1:9000:9000"   # API S3
      - "127.0.0.1:9001:9001"   # Consola web
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 10s
      timeout: 5s
      retries: 3
    networks:
      - loremaster
```

Añadir `minio_data:` a la sección `volumes:` global del compose.

### Paso 2 — Variables de entorno para el servicio `app`

```yaml
    environment:
      STORAGE_BACKEND: s3
      S3_ENDPOINT_URL: http://minio:9000
      S3_BUCKET: ${S3_BUCKET:-loremaster-media}
      S3_REGION: us-east-1            # MinIO ignora la región pero boto3 la requiere
      AWS_ACCESS_KEY_ID: ${MINIO_ROOT_USER:-loremaster}
      AWS_SECRET_ACCESS_KEY: ${MINIO_ROOT_PASSWORD}
      STORAGE_BASE_URL: http://localhost:9000/${S3_BUCKET:-loremaster-media}
```

### Paso 3 — Dependencia en el servicio `app`

```yaml
    depends_on:
      minio:
        condition: service_healthy
```

---

## Opción B — Floci (emulador AWS, reemplaza LocalStack)

> LocalStack Community quedó obsoleto en marzo 2026. Floci es su sucesor MIT, sin auth token,
> imagen 90 MB vs 1 GB, startup 24 ms vs 3.3 s.
>
> **Doc principal:** https://github.com/floci-io/floci

### Paso 1 — Añadir Floci a `docker-compose.prod.yml`

> **Referencia:** [docs/configuration/docker-compose.md](https://github.com/floci-io/floci/blob/main/docs/configuration/docker-compose.md)
> — Variables `FLOCI_HOSTNAME`, `FLOCI_STORAGE_MODE`, `FLOCI_STORAGE_PERSISTENT_PATH`,
> `FLOCI_DEFAULT_REGION`. Volumen en `/app/data`. Puerto único: `4566`.

```yaml
  floci:
    image: floci/floci:latest
    container_name: loremaster-floci
    restart: unless-stopped
    environment:
      FLOCI_HOSTNAME: floci                        # nombre DNS dentro de la red Docker
      FLOCI_STORAGE_MODE: persistent               # memory | persistent | hybrid | wal
      FLOCI_STORAGE_PERSISTENT_PATH: /app/data
      FLOCI_DEFAULT_REGION: us-east-1
    ports:
      - "127.0.0.1:4566:4566"
    volumes:
      - floci_data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4566"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - loremaster
```

Añadir `floci_data:` a la sección `volumes:` global del compose.

> **Nota sobre healthcheck:** verificar en
> [docs/configuration/docker-compose.md](https://github.com/floci-io/floci/blob/main/docs/configuration/docker-compose.md)
> si floci expone un endpoint dedicado (ej. `/_floci/health`). Si la `curl` al root devuelve
> error, ajustar el path.

> **Nota sobre Docker socket:** según los docs, `-v /var/run/docker.sock:/var/run/docker.sock`
> solo es necesario para Lambda, RDS y ElastiCache — **no para S3**. No montarlo.

### Paso 2 — Variables de entorno para el servicio `app`

> **Referencia:** [README — boto3 Python snippet](https://github.com/floci-io/floci#readme)
> — `endpoint_url="http://localhost:4566"`, `aws_access_key_id="test"`, `aws_secret_access_key="test"`.
> Floci acepta cualquier valor no vacío como credenciales.

```yaml
    environment:
      STORAGE_BACKEND: s3
      S3_ENDPOINT_URL: http://floci:4566           # nombre de servicio Docker, no localhost
      S3_BUCKET: loremaster-media
      S3_REGION: us-east-1
      AWS_ACCESS_KEY_ID: test                      # cualquier string no vacío
      AWS_SECRET_ACCESS_KEY: test
      STORAGE_BASE_URL: http://localhost:4566/loremaster-media
```

### Paso 3 — Dependencia en el servicio `app`

```yaml
    depends_on:
      floci:
        condition: service_healthy
```

### Paso 4 — URL path-style para acceso a archivos

> **Referencia:** [docs/services/s3.md](https://github.com/floci-io/floci/blob/main/docs/services/s3.md)
> — Floci soporta dos estilos de URL:
> - Path-style: `http://localhost:4566/{bucket}/{key}` ← usar esta
> - Virtual-hosted: `http://{bucket}.s3.localhost.floci.io:4566/{key}` ← requiere DNS config adicional

El `STORAGE_BASE_URL` en el paso 2 ya usa path-style. En la función `build_storage_url` del código
(paso de código 3.4 abajo), la rama S3 construye la URL de este modo:
`http://localhost:4566/loremaster-media/{key}` — correcto para floci.

---

## Cambios de código requeridos (común a MinIO y Floci)

### Paso de código 1 — Dependencias: `requirements.txt`

```
boto3>=1.34.0
```

### Paso de código 2 — Settings: `app/core/config/__init__.py`

```python
storage_backend: str = "local"          # "local" | "s3"
s3_endpoint_url: str | None = None      # None = AWS real; URL = Floci/MinIO/R2
s3_bucket: str = "loremaster-media"
s3_region: str = "us-east-1"
aws_access_key_id: str | None = None
aws_secret_access_key: str | None = None
```

### Paso de código 3 — Cliente S3: `app/core/storage/s3_client.py`

> **Referencia:** [README — boto3 Python snippet](https://github.com/floci-io/floci#readme)
> — El ejemplo oficial usa `endpoint_url`, `region_name`, `aws_access_key_id`, `aws_secret_access_key`.
> Mismo patrón para MinIO y Floci.

```python
import boto3
from botocore.config import Config
from app.core.config import settings

def get_s3_client():
    kwargs = {
        "region_name": settings.s3_region,
        "config": Config(signature_version="s3v4"),
    }
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    if settings.aws_access_key_id:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return boto3.client("s3", **kwargs)
```

### Paso de código 4 — Storage: `app/core/storage/__init__.py`

> **Referencia:** [docs/services/s3.md](https://github.com/floci-io/floci/blob/main/docs/services/s3.md)
> — Operaciones soportadas: `PutObject`, `GetObject`, `CreateBucket`, `HeadBucket`, multipart upload.
> Todas las operaciones que usa este código están confirmadas en S3 de Floci.

```python
def save_file(content: bytes, relative_path: str) -> str:
    if settings.storage_backend == "s3":
        client = get_s3_client()
        client.put_object(
            Bucket=settings.s3_bucket,
            Key=relative_path,
            Body=content,
        )
        return relative_path
    # ... lógica local existente

def build_storage_url(relative_path: str | None) -> str | None:
    if not relative_path:
        return None
    if settings.storage_backend == "s3" and settings.s3_endpoint_url:
        # Path-style URL — compatible con Floci, MinIO y R2
        base = settings.s3_endpoint_url.rstrip("/")
        return f"{base}/{settings.s3_bucket}/{relative_path}"
    return f"{settings.storage_base_url.rstrip('/')}/{relative_path}"
```

### Paso de código 5 — Crear bucket al arrancar: `app/core/lifespan.py`

> **Referencia:** [README — Bucket creation](https://github.com/floci-io/floci#readme)
> — El ejemplo oficial crea el bucket con `client.create_bucket(Bucket="my-bucket")`.
> Floci no crea buckets automáticamente; hay que crearlos explícitamente.

```python
if settings.storage_backend == "s3":
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except client.exceptions.NoSuchBucket:
        client.create_bucket(Bucket=settings.s3_bucket)
```

---

## Checklist de validación (Floci)

```bash
# 1. Levantar el stack completo
docker compose -f backend/docker-compose.prod.yml up -d

# 2. Verificar que floci levantó y está healthy
docker compose -f backend/docker-compose.prod.yml ps
# floci debe mostrar "healthy"

# 3. Verificar que S3 responde (desde el host)
curl -s http://localhost:4566
# debe devolver XML o respuesta vacía — si devuelve "connection refused", floci no arrancó

# 4. Health del backend
curl http://localhost:8000/health

# 5. Verificar que el bucket fue creado (lifespan.py lo crea al arrancar)
# Opción con AWS CLI apuntando a Floci:
AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test \
  aws --endpoint-url http://localhost:4566 s3 ls
# debe mostrar: loremaster-media

# 6. Flujo completo de imagen
#    a. Crear colección + subir documento
#    b. Crear entidad + generar contenido + confirmar
#    c. POST /image-generation/build-prompt
#    d. POST /image-generation/generate
#    e. Verificar que la URL de imagen responde 200
#       curl http://localhost:4566/loremaster-media/<path-de-la-imagen>

# 7. Persistencia: bajar y volver a levantar (FLOCI_STORAGE_MODE=persistent)
docker compose -f backend/docker-compose.prod.yml down
docker compose -f backend/docker-compose.prod.yml up -d
# La imagen del paso 6 debe seguir accesible

# 8. Test suite (no toca servicios externos)
cd backend && python -m pytest -q
```

---

## Variables `.env` para la prueba con Floci

```env
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=http://localhost:4566
S3_BUCKET=loremaster-media
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
STORAGE_BASE_URL=http://localhost:4566/loremaster-media
```

---

## Opción C — Cloudflare R2 (producción real)

Si el destino es producción directamente:

1. Crear bucket en [dash.cloudflare.com](https://dash.cloudflare.com) → R2
2. Generar API token con permisos `Object Read & Write`
3. Variables:
   ```env
   STORAGE_BACKEND=s3
   S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
   S3_BUCKET=loremaster-media
   AWS_ACCESS_KEY_ID=<r2-access-key>
   AWS_SECRET_ACCESS_KEY=<r2-secret-key>
   STORAGE_BASE_URL=https://pub-<hash>.r2.dev  # dominio público del bucket
   ```
4. Sin cambios de código — el cliente boto3 funciona igual con R2.

Ventaja: egress gratuito (a diferencia de AWS S3). Plan gratuito: 10 GB almacenamiento + 1M operaciones/mes.

---

## Orden de implementación recomendado

1. Añadir `boto3` a `requirements.txt`
2. Añadir settings S3 en `config/__init__.py`
3. Crear `core/storage/s3_client.py`
4. Modificar `core/storage/__init__.py` con la rama S3
5. Añadir inicialización del bucket en `lifespan.py`
6. Añadir Floci (o MinIO) al `docker-compose.prod.yml`
7. Añadir variables al `.env.production.example`
8. Validar con el checklist de arriba
