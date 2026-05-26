# Reporte de Costos — Lore Master

Estimación de costos operativos mensuales para demo privada y producción.
Actualizado: 2026-05-25. Precios en USD, aproximados — verificar en los dashboards de cada servicio.

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

El backend necesita mínimo: 2 vCPU, 4 GB RAM, 30 GB disco.

| Proveedor | Plan | Precio/mes | Notas |
|---|---|---|---|
| Hetzner Cloud | CX22 (2 vCPU, 4 GB) | ~$4.50 | EU/US. Mejor precio/calidad. |
| DigitalOcean | Basic (2 vCPU, 4 GB) | ~$24 | Más caro, mejor soporte. |
| Contabo | VPS S (4 vCPU, 6 GB) | ~$6 | Muy económico, soporte lento. |
| Fly.io | shared-cpu-2x (4 GB) | ~$10-15 | Serverless, paga por uso. |

**Recomendación demo:** Hetzner CX22 (~$4.50/mes). Espacio suficiente para PG + Qdrant + Redis + API.

### 2.2 GPU — generación de imágenes

Opciones si Ollama y ComfyUI no pueden correr en el VPS (sin GPU):

| Opción | Precio | Notas |
|---|---|---|
| RunPod Serverless | ~$0.20-0.40/imagen | Paga por generación. Sin costo si no se usa. |
| RunPod On-Demand (RTX 4090) | ~$0.74/hora | Más barato si generas muchas imágenes en bloque. |
| Replicate (FLUX) | ~$0.055/imagen | Más caro pero más simple de integrar. |
| GPU propia (RTX 3080+) | $0/mes (electricidad) | Lo que tienes en local. |

**Para demo de 1-5 usuarios:** RunPod Serverless. Si se generan ~50 imágenes/mes → ~$10-20/mes.

### 2.3 LLM (Ollama)

Opciones si no hay GPU en el VPS:

| Opción | Precio | Notas |
|---|---|---|
| Ollama en GPU propia (host) | $0/mes | Solución actual en local. |
| RunPod On-Demand (RTX 3090) | ~$0.44/hora | Arrancar solo cuando se necesita. |
| Groq API (llama3) | Free tier / ~$0.05/1M tokens | Sin GPU propia, muy rápido. |
| Together AI | ~$0.20/1M tokens | Compatible con OpenAI SDK. |

**Para demo:** Mantener Ollama en el host (GPU propia) + el backend en el VPS apuntando a `host.docker.internal` — o bien la IP pública del host si el VPS es externo.

### 2.4 Storage — imágenes generadas

| Opción | Precio | Notas |
|---|---|---|
| Cloudflare R2 | Free hasta 10 GB + 1M ops | Egress gratuito. **Recomendado.** |
| Backblaze B2 | ~$0.006/GB/mes | Muy económico. |
| AWS S3 | ~$0.023/GB + egress $0.09/GB | Más caro. Solo si destino es AWS. |
| Filesystem VPS (volumen) | Incluido en VPS o ~$0.05/GB | Simple pero no escala. |

**Para demo:** Cloudflare R2 (plan gratuito suficiente para cientos de imágenes).

### 2.5 Dominio + SSL

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
| VPS backend | Hetzner CX22 | $4.50 |
| Storage imágenes | Cloudflare R2 | $0 (free tier) |
| Dominio | Namecheap / Porkbun | $1 |
| LLM + Imágenes | GPU propia (local) | $0 + electricidad |
| **Total** | | **~$5.50/mes** |

### Demo privada (sin GPU propia)

| Componente | Proveedor | $/mes |
|---|---|---|
| VPS backend | Hetzner CX22 | $4.50 |
| LLM queries (~500/mes) | Groq free tier | $0 |
| Imágenes (~50/mes) | RunPod Serverless | ~$15 |
| Storage | Cloudflare R2 | $0 |
| Dominio | | $1 |
| **Total** | | **~$20/mes** |

### Producción pequeña (10-50 usuarios)

| Componente | Proveedor | $/mes |
|---|---|---|
| VPS backend (4 vCPU, 8 GB) | Hetzner CX32 | $10 |
| LLM API | Groq / Together AI | $5-30 |
| Imágenes (~500/mes) | RunPod Serverless | ~$100-200 |
| Storage | Cloudflare R2 | $0-5 |
| Dominio + extras | | $2 |
| **Total** | | **~$120-250/mes** |

---

## 4. Cómo elaborar el reporte para tu proyecto

### Metodología — 4 pasos

**Paso 1 — Medir el uso real**

Antes de proyectar costos, medir cuánto se usa realmente:
- Queries RAG por día: revisar logs `logger.info("Executing RAG query...")` en `rag_query_service.py`
- Imágenes generadas: tabla `generated_images` en la DB → `SELECT COUNT(*), DATE(created_at) FROM generated_images GROUP BY DATE(created_at)`
- Tokens estimados: campo `token_count` en `generated_texts`
- Tamaño de imágenes: `du -sh media/`

**Paso 2 — Calcular por componente**

Para cada componente del stack, calcular: `unidad × precio_unitario = costo_mensual`

Ejemplo para RunPod:
```
imágenes/mes × segundos_por_imagen × precio_por_segundo = costo/mes
50 imágenes × 15s × $0.000222/s (RTX 4090) = ~$0.17/mes (muy bajo con GPU propia)
```

**Paso 3 — Añadir buffer**

Añadir 20-30% sobre el estimado base para picos de uso, errores que consumen recursos, o crecimientos inesperados.

**Paso 4 — Documentar y revisar mensualmente**

Mantener una tabla con el costo real vs estimado cada mes. Los dashboards de cada servicio (Hetzner, RunPod, Cloudflare) muestran el gasto acumulado del mes.

### Herramientas útiles

| Herramienta | Para qué |
|---|---|
| [Hetzner Cloud Calculator](https://www.hetzner.com/cloud) | Calcular costo de VPS |
| [RunPod Pricing](https://www.runpod.io/gpu-instance/pricing) | GPUs por hora y serverless |
| [Cloudflare R2 Calculator](https://r2-calculator.cloudflare.com/) | Storage y operaciones |
| [Infracost](https://www.infracost.io/) | Estimación de costos AWS/GCP/Azure desde IaC |
| Google Sheets | Tracking mensual manual (suficiente para esta escala) |

---

## 5. Notas de arquitectura que impactan el costo

- **Semáforo LLM (`MAX_CONCURRENT_LLM_CALLS=1`):** limita el throughput pero evita costos por timeout o requests fallidas cuando el LLM está saturado. El HTTP 429 devuelve error rápido sin consumir GPU.
- **Llama Guard (`LLAMA_GUARD_ENABLED=true`):** si se activa en producción, duplica las llamadas a Ollama (una para RAG, otra para el guard). Considerar al calcular costo de GPU o API LLM.
- **`MAX_PDF_PAGES=100`:** limita el procesamiento de PDFs grandes — afecta CPU del VPS, no GPU.
- **Storage local vs S3:** el filesystem local del VPS es gratis hasta el límite del disco, pero las imágenes se pierden si el volumen no está montado correctamente. S3/R2 tiene costo pero es más fiable.
