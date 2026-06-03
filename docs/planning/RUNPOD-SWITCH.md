# RunPod ↔ ComfyUI — Switch de backend de imágenes

Estado: **código implementado** · **verificación en GPU pendiente** (sin saldo RunPod).

El backend de generación de imágenes se selecciona con una sola variable de
entorno. Cambiar entre ComfyUI local y RunPod Serverless no requiere tocar código.

```bash
IMAGE_BACKEND=comfyui   # local (default) — usa COMFYUI_URL
IMAGE_BACKEND=runpod    # GPU cloud — usa RUNPOD_API_KEY + RUNPOD_ENDPOINT_ID
IMAGE_BACKEND=mock      # placeholders (tests / sin GPU)
```

## Qué quedó implementado

| Archivo | Cambio |
|---|---|
| `engine/runpod_client.py` | `RunPodClient` con `submit_workflow`, `get_status`, `wait_for_completion`, `extract_image_bytes`. Diseñado para el **worker-comfyui oficial** de RunPod. |
| `services/image/_backends.py` | `_generate_runpod_images()` — espejo de `_generate_comfyui_images`: reusa el mismo template (`flux2-klein-4b-api.json`) e `inject_prompt`/`inject_seed`; solo cambia el transporte (job serverless). |
| `services/image/image_generation_service.py` | branch `elif params.backend == "runpod"`. |
| `tests/test_image_generation_service.py` | `test_ig_14_generate_batch_runpod` (mockeado, sin GPU). |

### Contrato con el worker-comfyui oficial

- **Envío** — `POST /v2/{endpoint_id}/run` con `{"input": {"workflow": <ComfyUI API dict>}}`.
- **Estado** — `GET /v2/{endpoint_id}/status/{job_id}`; estados `IN_QUEUE → IN_PROGRESS → COMPLETED | FAILED | CANCELLED`.
- **Salida** — `output.images = [{"filename", "type": "base64", "data": "<b64>"}]`.
  Si el worker está configurado con S3, `type` es `s3_url`/`url` y `data` es la URL
  pública (ya contemplado: `extract_image_bytes` descarga el contenido).

## Verificación en GPU pendiente (cuando haya saldo)

No es código — es validación en vivo. Orden recomendado para gastar lo mínimo:

1. **Montar el endpoint** en RunPod → Serverless → template **worker-comfyui** oficial.
2. **⚠️ Riesgo #1 — el modelo.** El worker debe tener **Flux.2 Klein 4B + los custom
   nodes** que usa `flux2-klein-4b-api.json` (nodo `12` `PrimitiveStringMultiline`,
   nodo `104` `RandomNoise`). Si no los trae, el job falla. Opciones: imagen Docker
   custom con el modelo, o network volume con los checkpoints. **Confirmar ANTES de
   gastar GPU.**
3. **Confirmar el schema de salida** en el dashboard (Request/Response): que
   `output.images[].data` venga en base64 (asumido). Si es `s3_url`, ya está cubierto.
4. **Primera prueba barata:** `batch_size=1`. Cada imagen es 1 job; un batch de 4 son
   4 jobs (~4× costo). Con cold-start de 15-30 s, una sola imagen valida la conexión
   gastando centavos.
5. **Setear el `.env`:** `IMAGE_BACKEND=runpod`, `RUNPOD_API_KEY`, `RUNPOD_ENDPOINT_ID`.

## Tradeoffs / deuda conocida

- Si RunPod no responde, se reutilizan `ComfyUIUnavailableError` / `ComfyUITimeoutError`
  (mapean a HTTP 503). El usuario verá "Verifica que ComfyUI esté corriendo", que es
  impreciso para RunPod. Decisión deliberada (YAGNI, mínimo blast radius). Si se quiere
  precisión: generalizar el mensaje o añadir excepciones backend-agnósticas.
- El batch hace 1 job por seed (paridad con ComfyUI local). No hay batching nativo en
  un solo job; para más volumen convendría enviar el batch dentro del workflow.
