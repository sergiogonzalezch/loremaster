# Reporte de Costos — Lore Master

Estimación de costos operativos mensuales para demo privada y producción.
Actualizado: 2026-05-27. Precios en USD, aproximados — verificar en los dashboards de cada servicio.

> **Estado actual:** Stack demo completamente containerizado (`make prod-up`).
> 6 servicios Docker corriendo en un único VPS. LLM + imágenes via Ollama/ComfyUI en el host.
> Decisión de GPU cloud (P1) pendiente — impacta el escenario "sin GPU propia".

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

> ⚠️ **Decisión pendiente (P1):** La elección de backend GPU cloud no está tomada.
> El costo varía significativamente según la opción elegida.

| Opción | Precio/imagen (est.) | Notas |
|---|---|---|
| GPU propia (RTX 3080+) | $0 + electricidad | Solución actual en demo local. |
| RunPod Serverless (RTX 4090) | ~$0.003-0.006/s ≈ $0.05-0.09/img (15-30s) | Paga por segundo. Sin costo en reposo. **Candidato principal.** |
| RunPod On-Demand (RTX 4090) | ~$0.74/hora | Rentable si se generan muchas imágenes en bloque. |
| Replicate (FLUX.1 schnell) | ~$0.003/imagen | Más barato por imagen, pero modelo puede diferir. |
| Replicate (FLUX.1 dev) | ~$0.055/imagen | Más calidad, más caro. |

**Estimación demo (~50 imágenes/mes):**
- RunPod Serverless: 50 × 25s × $0.000222/s (RTX 4090) ≈ **$0.28/mes** — prácticamente gratis.
- Replicate FLUX schnell: 50 × $0.003 ≈ **$0.15/mes**.

**Para demo 1-5 usuarios:** cualquiera de las dos opciones es negligible en costo. La decisión es de integración, no de precio.

### 2.3 LLM (Ollama)

Opciones si no hay GPU en el VPS:

| Opción | Precio | Notas |
|---|---|---|
| Ollama en GPU propia (host) | $0/mes | Solución actual en local. |
| RunPod On-Demand (RTX 3090) | ~$0.44/hora | Arrancar solo cuando se necesita. |
| Groq API (llama3) | Free tier / ~$0.05/1M tokens | Sin GPU propia, muy rápido. |
| Together AI | ~$0.20/1M tokens | Compatible con OpenAI SDK. |

**Para demo:** Mantener Ollama en el host (GPU propia) + el backend en el VPS apuntando a `host.docker.internal` — o bien la IP pública del host si el VPS es externo.

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

### Demo privada (1-5 usuarios, GPU propia para LLM/imágenes)

| Componente | Proveedor | $/mes |
|---|---|---|
| VPS backend (8 GB RAM) | Hetzner CX32 | $9 |
| Auth | Clerk free tier | $0 |
| Storage imágenes | Cloudflare R2 free tier | $0 |
| Dominio | Namecheap / Porkbun | $1 |
| LLM + Imágenes | GPU propia (local) | $0 + electricidad |
| **Total** | | **~$10/mes** |

> Con Hetzner CX22 ($4.50) en vez de CX32: **~$5.50/mes** — viable si el RAM alcanza.

### Demo privada (sin GPU propia — GPU cloud)

| Componente | Proveedor | $/mes |
|---|---|---|
| VPS backend (8 GB RAM) | Hetzner CX32 | $9 |
| Auth | Clerk free tier | $0 |
| LLM queries (~500/mes) | Groq free tier | $0 |
| Imágenes (~50/mes) | RunPod Serverless | ~$0.30 |
| Storage | Cloudflare R2 | $0 |
| Dominio | | $1 |
| **Total** | | **~$10/mes** |

> ⚠️ Nota: El costo de GPU en RunPod Serverless es prácticamente despreciable para ~50 imágenes/mes
> (~25s × $0.000222/s × 50 = $0.28). El costo dominante es el VPS.

### Producción pequeña (10-50 usuarios)

| Componente | Proveedor | $/mes |
|---|---|---|
| VPS backend (4 vCPU, 8 GB) | Hetzner CX32 | $9 |
| Auth | Clerk free tier (<10k MAU) | $0 |
| LLM API | Groq / Together AI | $5-30 |
| Imágenes (~500/mes) | RunPod Serverless | ~$3 |
| Storage (~5 GB) | Cloudflare R2 | $0 |
| Dominio + extras | | $2 |
| **Total** | | **~$15-45/mes** |

> Producción real con muchos usuarios concurrentes requeriría LLM API externa (Groq/Together) — sin GPU propia en VPS.

---

## 4. Notas de arquitectura que impactan el costo

- **Semáforo LLM (`MAX_CONCURRENT_LLM_CALLS=1`):** limita el throughput pero evita costos por timeout o requests fallidas cuando el LLM está saturado. El HTTP 429 devuelve error rápido sin consumir GPU.
- **Llama Guard (`LLAMA_GUARD_ENABLED=true`):** si se activa en producción, añade una llamada extra a Ollama por cada respuesta generada. Con GPU propia: solo latencia. Con API externa: dobla el costo de LLM. Mantener desactivado en demo salvo que la moderación sea prioritaria.
- **`MAX_PDF_PAGES=100`:** limita el procesamiento de PDFs grandes — afecta CPU del VPS, no GPU.
- **Storage:** el backend S3 ya está implementado con boto3. Para demo usa Floci (gratis en Docker). Para cloud: Cloudflare R2 free tier cubre miles de imágenes sin costo de egress. El filesystem local del VPS se pierde si el volumen no está bien montado — preferir R2 para persistencia real.
- **6 contenedores Docker:** el stack completo (Nginx + FastAPI + PG + Qdrant + Redis + Floci) consume ~2-3 GB RAM en reposo. Qdrant puede crecer con el índice vectorial. Monitorear con `docker stats` en el VPS.
- **GPU cloud (pendiente P1):** si se usa RunPod Serverless, el costo es despreciable para demos (pago por segundos de inferencia, $0 en reposo). Si se usa Replicate: similar. La decisión impacta la arquitectura más que el costo.
