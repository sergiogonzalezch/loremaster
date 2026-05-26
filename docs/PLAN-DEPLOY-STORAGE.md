# Plan — Prueba de Despliegue con Storage S3-Compatible

Referencia de implementación para reemplazar el almacenamiento local por un backend S3-compatible.
Cubre dos opciones: LocalStack (emulador AWS completo) y MinIO (S3-compatible, más simple y
recomendado para esta escala).

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

| | LocalStack | MinIO | Cloudflare R2 |
|---|---|---|---|
| Tipo | Emulador AWS completo | S3-compatible independiente | S3-compatible en nube |
| Complejidad | Alta (requiere config extra) | Baja | Media (necesita cuenta) |
| Uso recomendado | Validar integración AWS SDK | Dev + producción pequeña | Producción real |
| Egress cost | N/A (local) | N/A (local) | Gratuito |
| Docker image | `localstack/localstack` | `minio/minio` | N/A |
| API S3 compatible | Sí (port 4566) | Sí (port 9000) | Sí |
| Consola web | No (pro) | Sí (port 9001) | Sí (dashboard web) |

**Recomendación:** MinIO para dev/demo, Cloudflare R2 para producción real.
LocalStack tiene sentido solo si el destino final es AWS (EC2, ECS, etc.).

---

## Opción A — MinIO (recomendada)

### 1. Añadir MinIO a `docker-compose.prod.yml`

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

volumes:
  minio_data:
```

Añadir `minio_data:` a la sección `volumes:` global del compose.

### 2. Variables de entorno para el servicio `app`

```yaml
    environment:
      # Storage — S3 via MinIO
      STORAGE_BACKEND: s3
      S3_ENDPOINT_URL: http://minio:9000
      S3_BUCKET: ${S3_BUCKET:-loremaster-media}
      S3_REGION: us-east-1            # MinIO ignora la región pero boto3 la requiere
      AWS_ACCESS_KEY_ID: ${MINIO_ROOT_USER:-loremaster}
      AWS_SECRET_ACCESS_KEY: ${MINIO_ROOT_PASSWORD}
      STORAGE_BASE_URL: http://localhost:9000/${S3_BUCKET:-loremaster-media}
```

### 3. Dependencia en el servicio `app`

```yaml
    depends_on:
      minio:
        condition: service_healthy
```

---

## Opción B — LocalStack

### 1. Añadir LocalStack a `docker-compose.prod.yml`

```yaml
  localstack:
    image: localstack/localstack:latest
    container_name: loremaster-localstack
    restart: unless-stopped
    environment:
      SERVICES: s3
      DEFAULT_REGION: us-east-1
      AWS_DEFAULT_REGION: us-east-1
    ports:
      - "127.0.0.1:4566:4566"
    volumes:
      - localstack_data:/var/lib/localstack
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4566/_localstack/health"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - loremaster
```

### 2. Variables de entorno para el servicio `app`

```yaml
    environment:
      STORAGE_BACKEND: s3
      S3_ENDPOINT_URL: http://localstack:4566
      S3_BUCKET: loremaster-media
      S3_REGION: us-east-1
      AWS_ACCESS_KEY_ID: test       # LocalStack acepta cualquier valor
      AWS_SECRET_ACCESS_KEY: test
      STORAGE_BASE_URL: http://localhost:4566/loremaster-media
```

---

## Cambios de código requeridos

### 3.1 Dependencias — `requirements.txt`

```
boto3>=1.34.0
```

### 3.2 Settings — `app/core/config/__init__.py`

```python
storage_backend: str = "local"          # "local" | "s3"
s3_endpoint_url: str | None = None      # None = AWS real; URL = LocalStack/MinIO
s3_bucket: str = "loremaster-media"
s3_region: str = "us-east-1"
aws_access_key_id: str | None = None
aws_secret_access_key: str | None = None
```

### 3.3 Cliente S3 — `app/core/storage/s3_client.py`

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

### 3.4 Storage — `app/core/storage/__init__.py`

Añadir rama S3 en `save_file` y `build_storage_url`:

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
        # MinIO/LocalStack: URL directa al endpoint
        base = settings.s3_endpoint_url.rstrip("/")
        return f"{base}/{settings.s3_bucket}/{relative_path}"
    return f"{settings.storage_base_url.rstrip('/')}/{relative_path}"
```

### 3.5 Crear bucket al arrancar — `app/core/lifespan.py`

```python
if settings.storage_backend == "s3":
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except client.exceptions.NoSuchBucket:
        client.create_bucket(Bucket=settings.s3_bucket)
```

---

## Checklist de validación

```bash
# 1. Levantar el stack completo
docker compose -f backend/docker-compose.prod.yml up -d

# 2. Verificar health de todos los servicios
docker compose -f backend/docker-compose.prod.yml ps

# 3. Health del backend
curl http://localhost:8000/health

# 4. Consola MinIO (si usas MinIO) — abrir en browser
#    http://localhost:9001  →  usuario: loremaster / password: del .env

# 5. Flujo completo de imagen
#    a. Crear colección + subir documento
#    b. Crear entidad + generar contenido + confirmar
#    c. POST /image-generation/build-prompt
#    d. POST /image-generation/generate
#    e. Verificar que la URL de imagen responde 200
#    f. Verificar que el archivo aparece en la consola MinIO / LocalStack

# 6. Persistencia: bajar y volver a levantar el stack
docker compose -f backend/docker-compose.prod.yml down
docker compose -f backend/docker-compose.prod.yml up -d
#    → la imagen generada en el paso 5 debe seguir accesible

# 7. Test suite completa (sin servicios externos)
cd backend && python -m pytest -q
```

---

## Variables `.env` adicionales para la prueba

```env
# MinIO
MINIO_ROOT_USER=loremaster
MINIO_ROOT_PASSWORD=<password-seguro-min-8-chars>
S3_BUCKET=loremaster-media
STORAGE_BACKEND=s3
```

---

## Opción C — Cloudflare R2 (producción real, sin LocalStack)

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
6. Añadir MinIO al `docker-compose.prod.yml`
7. Añadir variables al `.env.production.example`
8. Validar con el checklist de arriba