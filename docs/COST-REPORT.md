# Reporte de Costos — Lore Master

Estimación de costos operativos mensuales para demo privada y producción.
Actualizado: 2026-05-30. Precios en USD, aproximados — verificar en los dashboards de cada servicio.

> **Estado actual:** Stack demo completamente containerizado (`make prod-up`).
> 6 servicios Docker corriendo en un único VPS. LLM + imágenes via Ollama/ComfyUI en el host.
> Decisión de GPU cloud: **resuelta** — ver secciones 2.2 y 2.3.

---

## 1. Escenarios

| Escenario | Descripción |
|---|---|
| **Dev local** | Todo en tu máquina. Costo = electricidad. |
| **Demo privada** | VPS económico + GPU en nube bajo demanda. Para 1-5 usuarios. |
| **Producción pequeña** | VPS estable + GPU serverless. Para 10-50 usuarios concurrentes. |

---

## 2. Demo privada — desglose mensual estimado

### 2.1 VPS (backend + servicios)

El stack containerizado corre **6 servicios Docker**: Nginx, FastAPI, PostgreSQL, Qdrant, Redis, Floci.
Requisitos reales del stack completo: **mínimo 4 GB RAM, recomendado 6-8 GB**. El CX22 (4 GB) puede ser justo con Qdrant cargado.

| Proveedor | Plan | Precio/mes | RAM | Notas |
|---|---|---|---|---|
| Hetzner Cloud | CX22 (2 vCPU, 4 GB) | ~$4.50 | 4 GB | Mínimo viable. Monitorear RAM con Qdrant. |
| Hetzner Cloud | CX32 (4 vCPU, 8 GB) | ~$9 | 8 GB | **Recomendado** para el stack de 6 servicios. |
| DigitalOcean | Basic (2 vCPU, 4 GB) | ~$24 | 4 GB | Más caro, mejor soporte. |
| Contabo | VPS S (4 vCPU, 6 GB) | ~$6 | 6 GB | Económico, soporte lento. |
| Fly.io | shared-cpu-2x (4 GB) | ~$10-15 | 4 GB | Serverless, paga por uso. |

**Recomendación demo:** Hetzner CX32 (~$9/mes). Con 8 GB hay margen para los 6 contenedores + headroom para picos de Qdrant.

### 2.2 GPU — generación de imágenes

El pipeline de imagen tiene dos pasos, ambos pueden correr en cloud:
1. **Prompt builder** (LLM texto): `mistral:latest` vía Ollama genera el prompt visual a partir del contenido confirmado.
2. **Diffusion** (GPU): ComfyUI ejecuta FLUX u otro modelo de difusión con ese prompt.

#### Opciones cloud — tabla comparativa

| Opción | Modelo | Precio/imagen (est.) | Cambio de código | Notas |
|---|---|---|---|---|
| **GPU propia (RTX 3080+)** | ComfyUI local | $0 + electricidad | Ninguno | Solución actual en demo local. |
| **RunPod Serverless** | ComfyUI template | ~$0.005-0.010/img (RTX 4090, 20-30 s × $0.00044/s) | Solo env var | **Sin cambio de código.** Apuntar `COMFYUI_URL` al endpoint serverless. |
| **fal.ai** | FLUX.1 schnell | ~$0.003/img | Reemplazar `comfyui_client.py` | API REST simple, sin gestionar GPU. Schnell: 4 pasos, muy rápido. |
| **fal.ai** | FLUX.1 dev | ~$0.025/img | Reemplazar `comfyui_client.py` | Mayor calidad que schnell. |
| **Replicate** | FLUX.1 schnell | ~$0.003/img | Reemplazar `comfyui_client.py` | Muy similar a fal.ai. |
| **Replicate** | FLUX.1 dev | ~$0.055/img | Reemplazar `comfyui_client.py` | Más caro que fal.ai dev. |
| **Modal** | ComfyUI custom | ~$0.003-0.008/img (A10G ~$0.00015/s) | Nuevo worker Python | Máxima flexibilidad de workflow, mayor complejidad ops. |
| **RunPod On-Demand** | ComfyUI | ~$0.74/hora | Solo env var | Solo rentable si se generan >50 imágenes/hora en bloque. |

#### Rutas arquitectónicas

**Ruta A — RunPod Serverless + ComfyUI (cero cambio de código)**

El proyecto ya tiene `engine/comfyui_client.py` integrado. RunPod permite desplegar ComfyUI como endpoint serverless con plantilla oficial:
- Crear endpoint en [runpod.io/serverless](https://www.runpod.io/serverless) con la plantilla `comfyui`.
- Cambiar solo: `COMFYUI_URL=https://<endpoint-id>-8188.proxy.runpod.net` en `.env.production`.
- Añadir autenticación: cabecera `Authorization: Bearer <RUNPOD_API_KEY>` en `ComfyUIClient._request`.
- **Ventaja:** compatibilidad total con los workflows actuales.
- **Desventaja:** arranque en frío de ~15-30 s si el worker estaba idle.

**Ruta B — fal.ai o Replicate (API managed, código nuevo)**

Reemplaza `comfyui_client.py` por un cliente REST de ~50 líneas:
```python
import httpx

FAL_KEY = settings.fal_api_key

def generate_image(prompt: str, width: int, height: int) -> bytes:
    resp = httpx.post(
        "https://fal.run/fal-ai/flux/schnell",
        headers={"Authorization": f"Key {FAL_KEY}"},
        json={"prompt": prompt, "image_size": {"width": width, "height": height}},
        timeout=60,
    )
    resp.raise_for_status()
    return httpx.get(resp.json()["images"][0]["url"]).content
```
- **Ventaja:** sin gestión de GPU, sin arranques en frío, SLA garantizado.
- **Desventaja:** pierde control del workflow ComfyUI (nodos personalizados, ControlNet, etc.).

#### Recomendación

| Contexto | Recomendación |
|---|---|
| Demo / prueba rápida | **RunPod Serverless** — cero código, solo env var. |
| Producción con escala | **fal.ai FLUX schnell** — más barato/imagen, sin ops GPU, API más simple. |
| Calidad máxima | **fal.ai FLUX dev** — $0.025/img, aún muy económico para <500 imgs/mes. |

#### Estimación de costo mensual por imagen

| Volumen | RunPod Serverless | fal.ai schnell | fal.ai dev |
|---|---|---|---|
| 50 imgs/mes (demo) | ~$0.25 | ~$0.15 | ~$1.25 |
| 500 imgs/mes (producción) | ~$2.50 | ~$1.50 | ~$12.50 |
| 5.000 imgs/mes (escala) | ~$25 | ~$15 | ~$125 |

> En todos los escenarios el costo de imagen es negligible frente al VPS. El factor dominante es la elección de modelo (schnell vs dev), no el proveedor.

### 2.3 LLM de texto para el pipeline de imagen

El pipeline de imagen usa dos LLMs de texto (configurables en `.env`):

| Variable | Modelo por defecto | Propósito |
|---|---|---|
| `OLLAMA_MODEL` | `llama3.2:latest` | RAG — respuestas de colección (**fuera del scope de imagen**) |
| `IMAGE_PROMPT_MODEL` | `mistral:latest` | Genera el prompt visual para ComfyUI |

Solo el `IMAGE_PROMPT_MODEL` es relevante para el pipeline de generación de imagen.

#### Opciones para `IMAGE_PROMPT_MODEL` en cloud

| Opción | Precio | Notas |
|---|---|---|
| **Ollama en GPU propia (host)** | $0/mes | Solución actual. El VPS apunta a `host.docker.internal:11434`. |
| **Groq API** (`mixtral-8x7b` / `llama-3.1-8b`) | Free tier / ~$0.27/1M tokens | Sin GPU propia. Latencia muy baja (~0.5 s). Compatible con sustitución directa. |
| **Together AI** (`mistral-7b-instruct`) | ~$0.20/1M tokens | Compatible con OpenAI SDK. |
| **OpenRouter** (`mistral-7b-instruct`) | ~$0.07/1M tokens | Agregador; elige proveedor más barato. |

**Costo real del prompt builder:** cada llamada genera ~150-300 tokens. A $0.20/1M tokens:
- 500 llamadas/mes × 300 tokens ≈ 150k tokens → **$0.03/mes**. Negligible.

**Para demo:** mantener Ollama en host. Si el host con GPU no está disponible, Groq free tier cubre perfectamente la carga de demo sin costo.

### 2.4 Auth — Clerk

| Plan | Precio | Límite |
|---|---|---|
| Free | $0/mes | Hasta 10.000 MAU |
| Pro | $25/mes | MAU ilimitado |

**Para demo privada (1-5 usuarios):** Free tier. Margen enorme antes de necesitar Pro.
El código de integración ya está en main (`auth_clerk.py`). Solo falta configurar el tenant en el dashboard de Clerk.

---

### 2.5 Storage — imágenes generadas

El backend S3 ya está implementado (`core/storage/s3_client.py` con boto3). Soporta AWS S3 real, Cloudflare R2 y Floci (demo local).

| Opción | Precio | Notas |
|---|---|---|
| **Cloudflare R2** | Free hasta 10 GB + 1M ops/mes | Egress gratuito. **Recomendado.** |
| Backblaze B2 | ~$0.006/GB/mes | Muy económico, egress $0.01/GB. |
| AWS S3 | ~$0.023/GB + egress $0.09/GB | Más caro. Solo si el destino es AWS. |
| Filesystem VPS (volumen) | Incluido en VPS | Simple pero no escala; imágenes se pierden si el volumen falla. |
| Floci (demo local) | $0 | Emulador S3 en Docker; ya activo en `make prod-up`. |

**Para demo:** Cloudflare R2 plan gratuito — suficiente para miles de imágenes sin costo.
Para activar: cambiar `S3_ENDPOINT_URL` + credenciales reales en `.env.production`.

### 2.6 Dominio + SSL

| Item | Precio |
|---|---|
| Dominio `.com` | ~$10-15/año (~$1/mes) |
| SSL (Let's Encrypt) | Gratis |
| Nginx reverse proxy | Gratis (en el VPS) |

---

## 3. Resumen — costo total estimado por escenario

### Hosting recomendado para el stack completo

El stack de producción corre 6 contenedores Docker (Nginx, FastAPI, PostgreSQL, Qdrant, Redis, Floci).
Requiere **mínimo 4 GB RAM, recomendado 6-8 GB**. Un único VPS cubre todo.

| Proveedor | Plan | $/mes | RAM | Veredicto |
|---|---|---|---|---|
| **Hetzner Cloud** | **CX32 (4 vCPU, 8 GB)** | **~$9.90** | 8 GB | **Recomendado** — mejor relación precio/RAM para los 6 servicios. |
| Hetzner Cloud | CX22 (2 vCPU, 4 GB) | ~$4.90 | 4 GB | Mínimo viable. Vigilar RAM con Qdrant activo. |
| Contabo | VPS S (4 vCPU, 6 GB) | ~$6 | 6 GB | Más barato que DO, soporte lento. |
| DigitalOcean | Basic Droplet (2 vCPU, 4 GB) | ~$24 | 4 GB | Caro para lo que ofrece; solo si ya se usa el ecosistema DO. |
| Fly.io | shared-cpu-2x (4 GB) | ~$10-15 | 4 GB | Pago por uso; arranques en frío. Complejo con 6 servicios stateful. |
| Railway | Hobby / Pro | ~$5-20 | Variable | No apto: Qdrant + PostgreSQL como volúmenes stateful no encajan bien. |

> **Nota Fly.io / Railway:** estos PaaS funcionan bien para aplicaciones sin estado o con bases de datos gestionadas.
> El stack de Lore Master tiene **Qdrant + PostgreSQL + Redis stateful**, lo que hace más simple un VPS clásico.

**Recomendación final de hosting: Hetzner CX32 (~$9.90/mes).** Soporta el stack completo con margen,
datacenter en EU (baja latencia a España), interfaz sencilla, y sin lock-in de PaaS.

---

### Demo privada (1-5 usuarios, GPU propia para LLM/imágenes)

| Componente | Proveedor | $/mes |
|---|---|---|
| VPS backend (8 GB RAM) | Hetzner CX32 | $9.90 |
| Auth | Clerk free tier | $0 |
| Storage imágenes | Cloudflare R2 free tier | $0 |
| Dominio | Namecheap / Porkbun | $1 |
| Prompt builder (mistral) | Ollama en GPU propia | $0 |
| Generación de imagen | ComfyUI en GPU propia | $0 + electricidad |
| **Total** | | **~$11/mes** |

> Con Hetzner CX22 ($4.90): **~$6/mes** — viable si el RAM alcanza.

### Demo privada (sin GPU propia — GPU cloud, cero cambio de código)

| Componente | Proveedor | $/mes |
|---|---|---|
| VPS backend (8 GB RAM) | Hetzner CX32 | $9.90 |
| Auth | Clerk free tier | $0 |
| Prompt builder (mistral) | Groq free tier | $0 |
| Generación de imagen (~50/mes) | RunPod Serverless + ComfyUI | ~$0.25 |
| Storage | Cloudflare R2 | $0 |
| Dominio | | $1 |
| **Total** | | **~$11/mes** |

> El costo de GPU para ~50 imágenes/mes es despreciable. El costo dominante es el VPS.

### Demo privada (sin GPU propia — fal.ai, máxima simplicidad)

| Componente | Proveedor | $/mes |
|---|---|---|
| VPS backend (8 GB RAM) | Hetzner CX32 | $9.90 |
| Auth | Clerk free tier | $0 |
| Prompt builder (mistral) | Groq free tier | $0 |
| Generación de imagen (~50/mes) | fal.ai FLUX schnell | ~$0.15 |
| Storage | Cloudflare R2 | $0 |
| Dominio | | $1 |
| **Total** | | **~$11/mes** |

> Requiere reemplazar `comfyui_client.py` por cliente fal.ai (~50 líneas). A cambio: sin gestión de GPU, sin arranques en frío.

### Producción pequeña (10-50 usuarios)

| Componente | Proveedor | $/mes |
|---|---|---|
| VPS backend (4 vCPU, 8 GB) | Hetzner CX32 | $9.90 |
| Auth | Clerk free tier (<10k MAU) | $0 |
| Prompt builder (mistral) | Groq / Together AI | ~$0.03 |
| Generación de imagen (~500/mes) | fal.ai FLUX schnell | ~$1.50 |
| Storage (~5 GB) | Cloudflare R2 | $0 |
| Dominio + extras | | $2 |
| **Total** | | **~$13/mes** |

> Si se requiere mayor calidad de imagen: fal.ai FLUX dev (~$12.50/mes para 500 imgs). Aún muy manejable.

---

## 4. Notas de arquitectura que impactan el costo

- **Semáforo LLM (`MAX_CONCURRENT_LLM_CALLS=1`):** limita el throughput pero evita costos por timeout o requests fallidas cuando el LLM está saturado. El HTTP 429 devuelve error rápido sin consumir GPU.
- **Llama Guard (`LLAMA_GUARD_ENABLED=true`):** si se activa en producción, añade una llamada extra a Ollama por cada respuesta generada. Con GPU propia: solo latencia. Con API externa: dobla el costo del prompt builder. Mantener desactivado en demo salvo que la moderación sea prioritaria.
- **`MAX_PDF_PAGES=100`:** limita el procesamiento de PDFs grandes — afecta CPU del VPS, no GPU.
- **Storage:** el backend S3 ya está implementado con boto3. Para demo usa Floci (gratis en Docker). Para cloud: Cloudflare R2 free tier cubre miles de imágenes sin costo de egress. El filesystem local del VPS se pierde si el volumen no está bien montado — preferir R2 para persistencia real.
- **6 contenedores Docker:** el stack completo (Nginx + FastAPI + PG + Qdrant + Redis + Floci) consume ~2-3 GB RAM en reposo. Qdrant puede crecer con el índice vectorial. Monitorear con `docker stats` en el VPS.
- **GPU cloud — rutas de implementación:**
  - **RunPod Serverless** (cero código): cambiar `COMFYUI_URL` en compose + añadir auth header en `ComfyUIClient._request`. Costo: ~$0.005-0.010/imagen. Arranque en frío ~15-30 s.
  - **fal.ai** (cliente nuevo): reemplazar `comfyui_client.py` por cliente REST (~50 líneas). Costo: ~$0.003/imagen (schnell) o $0.025 (dev). Sin arranques en frío, SLA gestionado.
  - Ambas opciones son negligibles en costo para demos. Para producción: fal.ai simplifica ops.

---

## 5. Checklist — activar GPU cloud (RunPod Serverless, Ruta A)

Pasos mínimos sin cambio de código:

1. Crear cuenta en [runpod.io](https://www.runpod.io) y fondear wallet (mínimo $10).
2. Crear **Serverless Endpoint** con plantilla `comfyui` → anotar `Endpoint ID`.
3. Subir el workflow JSON al endpoint (vía UI de RunPod o API).
4. En `.env.production`: `COMFYUI_URL=https://<endpoint-id>-8188.proxy.runpod.net`.
5. Añadir en `ComfyUIClient._request`:
   ```python
   headers = {}
   if settings.runpod_api_key:
       headers["Authorization"] = f"Bearer {settings.runpod_api_key}"
   response = client.request(method, url, headers=headers, **kwargs)
   ```
6. Añadir `RUNPOD_API_KEY=<tu-key>` en `.env.production`.
7. Verificar con una generación de prueba y confirmar que la imagen llega al bucket.

## 6. Checklist — activar GPU cloud (fal.ai, Ruta B)

Requiere reemplazar el cliente ComfyUI por uno fal.ai:

1. Crear cuenta en [fal.ai](https://fal.ai) y generar API key.
2. `pip install fal-client` o usar `httpx` directo (sin dependencia adicional).
3. Crear `backend/app/engine/fal_client.py` con el cliente REST (ver snippet en sección 2.2).
4. En `image_generation_service.py`: añadir rama `elif params.backend == "fal"` en `generate_images_service`.
5. En `docker-compose.prod.yml`: `IMAGE_BACKEND: fal`.
6. Añadir `FAL_API_KEY=<tu-key>` en `.env.production`.
7. Ajustar `_backends.py` para llamar al cliente fal.ai en vez de ComfyUI.
