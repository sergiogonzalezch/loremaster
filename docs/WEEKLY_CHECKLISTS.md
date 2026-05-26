# Checklists de Entregas Semanales — Lore Master

Documento de seguimiento basado en el roadmap de 12 semanas definido en `DOCUMENTATION.md`.
Cada semana incluye tareas verificables, criterios de aceptación y dependencias.

**Convenciones:**

- [ ] Tarea pendiente
- [x] Tarea completada
- **HU-XX** = Historia de usuario relacionada
- **O-X** = Objetivo del proyecto relacionado

---

# Fase 1 — Fundamentos de RAG (Semanas 1-4)

**Objetivo de fase:** API funcional con RAG básico. Sin imágenes, sin cloud.

---

## Semana 1 — FastAPI Skeleton

**Hito:** Repo Git funcional con estructura base y endpoints mock.
**Objetivos:** O-3
**Historias:** HU-01

### Infraestructura y Repo

- [x] Repositorio Git inicializado con `.gitignore` para Python
- [x] Estructura de carpetas creada: `backend/app/{api/routes, models, schemas, services, core}`
- [x] `requirements.txt` con dependencias base: `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `python-dotenv`
- [x] Archivo `.env.example` con variables documentadas
- [x] `Makefile` con target `run` (levanta uvicorn en modo dev)

### Aplicacion FastAPI

- [x] `main.py` con instancia FastAPI, metadata del proyecto y CORS configurado
- [x] Endpoint `GET /` retorna nombre del servicio y versión
- [x] Endpoint `GET /health` retorna `{"status": "ok"}`
- [x] Swagger UI accesible en `/docs`

### Endpoints Mock

- [x] `POST /api/v1/collections` — crea coleccion (mock, retorna `collection_id`)
- [x] `GET /api/v1/collections` — lista colecciones (mock)
- [x] `POST /api/v1/collections/{id}/generate/text` — retorna texto placeholder
- [x] Schemas Pydantic definidos para request/response de colecciones

### Criterios de aceptacion Semana 1

- [x] `make run` levanta el servidor sin errores
- [x] Swagger muestra todos los endpoints documentados
- [x] `POST /collections` retorna 201 con `collection_id`
- [x] `POST /generate/text` retorna 200 con texto mock

---

## Semana 2 — Ingesta + Embeddings

Nota de Mike:

- Agregar testing
- Agregar frontend folder
- Avanzar con la semana 2

**Hito:** Ingesta de documentos funcional con generacion de embeddings.
**Objetivos:** O-1
**Historias:** HU-02

### Dependencias

- [x] Agregar a `requirements.txt`: `pypdf`, `langchain`, `langchain-text-splitters`, `sentence-transformers`, `langchain-huggingface`, `python-multipart`
- [x] Verificar descarga del modelo `paraphrase-multilingual-MiniLM-L12-v2`

### Endpoint de Ingesta

- [x] `POST /api/v1/collections/{collection_id}/documents` acepta archivos via `UploadFile`
- [x] Validacion de tipo de archivo: solo `application/pdf` y `text/plain`
- [x] Validacion de tamano: maximo 50 MB
- [x] Retorna `HTTP 400` para formatos invalidos o archivos sin nombre
- [x] Retorna `HTTP 404` si `collection_id` no existe

### Extraccion de Texto

- [x] Extraccion de texto de PDF con `pypdf`
- [x] Lectura directa de archivos TXT (UTF-8)
- [x] Manejo de PDFs con paginas sin texto (fallback a string vacio por pagina)

### Chunking

- [x] `RecursiveCharacterTextSplitter` configurado: `chunk_size=512`, `chunk_overlap=50`
- [x] Separadores definidos: `["\n\n", "\n", ". ", " ", ""]`
- [x] Chunks almacenados en memoria (dict mock) con metadata: `doc_id`, `collection_id`, `chunk_idx`

### Embeddings

- [x] Generacion de embeddings con `sentence-transformers` (modelo MiniLM, 384 dims)
- [x] Batch size configurado a 32
- [x] Embeddings asociados a cada chunk en memoria

### Criterios de aceptacion Semana 2

- [x] Subir un PDF de prueba retorna 201 con `doc_id` y `chunk_count`
- [x] Subir un TXT retorna 201 con `doc_id` y `chunk_count`
- [x] Subir un `.docx` retorna 400
- [x] Subir archivo > 50 MB retorna 400
- [x] Los chunks se pueden consultar internamente por `collection_id`

---

## Semana 3 — Vector DB (RAG Basico)

**Hito:** Integracion con Qdrant y busqueda semantica funcional.
**Objetivos:** O-1
**Historias:** HU-03

### Infraestructura Qdrant

- [x] `docker-compose.yml` con servicio Qdrant (puerto 6333, volumen persistente)
- [x] Agregar `qdrant-client` a `requirements.txt`
- [x] Variables en `.env.example`: `QDRANT_URL`, `QDRANT_COLLECTION`
- [x] Verificar conectividad: Qdrant dashboard accesible en `http://localhost:6333/dashboard`

### RAG Engine

- [x] `rag_engine.py` con clase/funciones para operaciones vectoriales
- [x] Crear coleccion en Qdrant con prefijo `lm_{collection_id}` (384 dims, cosine)
- [x] Verificacion de coleccion existente antes de crear (evitar duplicados)
- [x] Insertar chunks con embeddings en Qdrant (payload: `doc_id`, `collection_id`, `chunk_idx`, `text`)
- [x] Busqueda semantica: recibir query, generar embedding, buscar `top_k=4` en Qdrant

### Endpoint Generate/Text con Contexto Real

- [x] `POST /api/v1/collections/{id}/generate/text` ahora usa contexto de Qdrant
- [x] Si no hay documentos en la coleccion → `HTTP 422`
- [x] Contexto ensamblado: chunks unidos con `\n\n---\n\n`
- [x] Respuesta temporal: retorna el contexto recuperado (sin LLM aun)

### Criterios de aceptacion Semana 3

- [x] `docker compose up qdrant` levanta sin errores
- [x] Ingestar documento → chunks aparecen en Qdrant dashboard
- [x] Query semantica retorna chunks relevantes del documento ingestado
- [x] Query en coleccion vacia retorna 422
- [x] Busqueda es especifica por `collection_id` (no cruza colecciones)

---

## Semana 4 — Pipeline RAG Completo

**Hito:** Pipeline end-to-end con LLM local (Ollama).
**Objetivos:** O-1, O-3
**Historias:** HU-03

### Integracion Ollama

- [x] Agregar a `requirements.txt`: `langchain-ollama`
- [x] Variables en `.env.example`: `OLLAMA_BASE_URL`, `OLLAMA_MODEL`
- [x] Verificar que Ollama esta corriendo con modelo `llama3.2` disponible
- [x] `config.py` con Pydantic Settings: `TEMPERATURE` (0.7), `MAX_TOKENS` (500)

### Generate Service

- [x] `generate_service.py` orquesta: query → retrieval → prompt → LLM → response
- [x] Prompt template en espanol para narrativa/worldbuilding
- [x] Parametros de generacion configurables: `temperature`, `max_tokens`
- [x] Respuesta incluye texto generado y conteo de fuentes usadas

### Endpoints Completos Fase 1

- [x] `POST /collections` — creacion con nombre unico (409 si duplicado)
- [x] `GET /collections` — listado completo
- [x] `GET /collections/{id}` — detalle
- [x] `DELETE /collections/{id}` — eliminacion
- [x] `POST /collections/{id}/documents` — ingesta completa
- [x] `GET /collections/{id}/documents` — listado de documentos
- [x] `POST /collections/{id}/generate/text` — generacion RAG completa

### Criterios de aceptacion Semana 4

- [x] Flujo completo: crear coleccion → subir PDF → hacer query → recibir respuesta coherente del LLM
- [x] La respuesta del LLM esta fundamentada en el contenido del documento (no inventa)
- [x] Si el contexto no tiene informacion suficiente, el LLM lo indica
- [x] Todos los endpoints documentados en Swagger
- [x] Crear coleccion con nombre duplicado retorna 409

### Checklist de Cierre Fase 1

- [x] Todos los criterios de Semanas 1-4 cumplidos
- [x] Pipeline RAG funcional de extremo a extremo
- [x] Cero errores criticos en flujo principal
- [x] Swagger documenta todos los endpoints activos
- [x] README actualizado con instrucciones de setup local

---

---

## Nota — Frontend implementado (fuera del plan original de backend)

El plan de 12 semanas se enfocaba en backend. El frontend fue implementado en paralelo y está completo.

### SPA React 19 (implementado durante Fase 1-2)

- [x] `CollectionsPage` — listar / crear / eliminar colecciones
- [x] `CollectionDetailPage` — tabs: Documentos, Entidades, Consulta RAG libre
- [x] `EntityDetailPage` — cabecera de entidad + formulario de generación + lista de contenidos por categoría
- [x] `GeneratePage` — consulta RAG en lenguaje libre
- [x] Capa API completa (`src/api/`) — todos los endpoints cubiertos con tipos TypeScript
- [x] Hook `useGenerate` — cancelación de requests LLM en curso
- [x] Hook `useEntityContents` — gestión de lista de contenidos
- [x] Renderizado Markdown sanitizado (`MarkdownContent` con `remark-gfm` + `rehype-sanitize`)
- [x] `TokenCounter` — estimación de tokens con advertencia en 400
- [x] Filtrado por status en tabs de contenidos (pending / confirmed / discarded)
- [x] Mensajes de error en español (`src/utils/errors.ts`)

### Preview de Imágenes en frontend (implementado en Semana 6)

- [x] `ImagePreviewPage` — página dedicada para preview de imágenes por contenido confirmado (`/collections/:id/entities/:eid/contents/:cid/image-preview`)
- [x] Botón "✦ Preview imagen" en `ContentCard` — solo visible en el bloque `isConfirmed`; redirige a `ImagePreviewPage`
- [x] Ruta registrada en `App.tsx` dentro del wrapper `<Layout>`
- [x] `src/api/images.ts` — llamada tipada al endpoint de generación de imágenes
- [x] `src/types/images.ts` — tipos `GenerateImageRequest` y `GenerateImageResponse`
- [x] `apiClient.ts` — mapa `HTTP_STATUS_MESSAGES` con texto descriptivo en español para todos los códigos 4xx/5xx; errores de validación FastAPI (arrays) no se muestran al usuario
- [x] `parseApiError()` diferencia `warning` (4xx) de `danger` (5xx) por rango numérico, sin overrides hardcodeados
- [x] 94 tests frontend pasando (13 archivos de test)

---

## Nota — Guardrails de contenido implementados (fuera del plan original)

Sistema de validación en 3 capas implementado en `backend/app/domain/content_guard.py`:

- [x] `check_user_input()` — valida input del usuario antes del pipeline RAG (raises `ValueError`)
- [x] `check_document_content()` — valida texto extraído de documentos al ingestar (raises `ValueError`)
- [x] `check_generated_output()` — valida salida del LLM antes de persistir (raises `RuntimeError`)
- [x] Lista de patrones bloqueados: contenido sexual explícito, discurso de odio, fabricación de armas/explosivos, síntesis de drogas, acoso

---

## Nota — Funcionalidades de Semana 8 implementadas anticipadamente

Las funcionalidades de gestión de entidades y borradores RAG, planificadas originalmente para la Semana 8, fueron implementadas durante las Semanas 4-5 junto con el pipeline RAG base. A continuación el estado real de cada ítem:

### CRUD de Entidades (previsto Semana 8 → implementado en Semana 5)

- [x] `POST /api/v1/collections/{id}/entities` — crear entidad (type, name, description)
- [x] `GET /api/v1/collections/{id}/entities` — listar entidades activas
- [x] `GET /api/v1/collections/{id}/entities/{entity_id}` — detalle
- [x] `PATCH /api/v1/collections/{id}/entities/{entity_id}` — actualización parcial (campos opcionales)
- [x] `DELETE /api/v1/collections/{id}/entities/{entity_id}` — soft-delete con cascada a drafts
- [x] Tipos soportados: `character`, `scene`, `faction`, `item`
- [x] Unicidad de nombre por colección (409 si duplicado)
- [x] Soft-delete: `is_deleted` + `deleted_at` en todos los modelos

### Sistema de Borradores RAG (previsto Semana 8 → implementado en Semana 5)

| Método | Ruta | Descripción | Status |
|---|---|---|---|
| `POST` | `.../entities/{eid}/generate` | Generar borrador con RAG | 201 |
| `GET` | `.../entities/{eid}/drafts` | Listar borradores activos (excluye discarded y soft-deleted) | 200 |
| `PATCH` | `.../entities/{eid}/drafts/{did}` | Editar contenido (solo pending) | 200 |
| `POST` | `.../entities/{eid}/drafts/{did}/confirm` | Confirmar → descarta hermanos pendientes de la categoría, retorna entidad | 200 |
| `PATCH` | `.../entities/{eid}/drafts/{did}/discard` | Cambiar status a descartado (acción reversible) | 200 |
| `DELETE` | `.../entities/{eid}/drafts/{did}` | Soft-delete real del borrador (`is_deleted=True`) | 204 |

- [x] Máximo 5 borradores `pending` por entidad (409 si se supera)
- [x] Confirmar un borrador auto-descarta los demás pending de la misma entidad
- [x] Eliminación en cascada: colección → documentos + entidades + drafts (soft-delete)
- [x] Eliminación de entidad → soft-delete de todos sus drafts (cualquier status)
- [x] Guards en `discard_pending_drafts` y `soft_delete_all_drafts`: requieren al menos un filtro
- [x] 131 tests passing (collections, content_guard, documents, entities, entity_content, generation_service, image_generation, prompt_builder, rag_query)

# Fase 2 — RAG Avanzado + Imagenes Locales (Semanas 5-8)

**Objetivo de fase:** Sistema RAG usable + introduccion progresiva de imagenes.
**Prerequisito:** Fase 1 estable y funcional.

> **ESTADO ACTUAL — 2026-05-20:**
> Estamos al final de la Semana 8. Las semanas 5-7 están esencialmente completas. Semana 8
> tiene un gap estructural: las imágenes NO usan contexto RAG (`build-prompt` no consulta Qdrant),
> evaluado y descartado en `metadata_harness` (sin mejora de calidad en modelos 3B). S3 también
> pendiente (filesystem local en producción). Semana 9+ (Fase 3) completamente sin iniciar.
>
> **Trabajo adicional realizado fuera del plan original (~3-4 semanas extra):**
> auth completo (Clerk + local + 6 fixes de seguridad), content guard con harness de evaluación,
> 53 issues de seguridad cerrados, React Doctor 100/100, ESLint 0/0, source attribution,
> perfiles de usuario, feed público, panel de admin, RAG params/LLM params/prompt/image harnesses.

---

## Semana 5 — RAG Intermedio

**Hito:** Mejora de calidad de retrieval y soporte para documentos grandes.
**Objetivos:** O-1
**Historias:** HU-02, HU-03

### Mejora de Chunking

- [x] Parametros de chunking configurables via `.env`: `CHUNK_SIZE`, `CHUNK_OVERLAP`
- [x] Experimentar con chunk sizes (256, 512, 1024) y documentar resultados
- [x] Verificar que overlap previene perdida de contexto en fronteras de chunks

### Mejora de Retrieval

- [x] `score_threshold` configurable para filtrar resultados de baja relevancia (`rag_score_threshold: float = 0.3` en config)
- [x] `top_k` configurable (default 4, se lee de `config.py` y se pasa como parametro)
- [x] Logging basico de queries y scores de retrieval (`logging` en todos los servicios)

### Soporte Documentos Grandes

- [x] Probar ingesta con PDFs > 10 paginas
- [x] Probar ingesta con PDFs > 50 paginas
- [x] Verificar que el chunking no pierde contenido en documentos largos — cubierto por RAG params harness (chunk=400, overlap=150 validados)
- [ ] Monitorear tiempo de ingesta y uso de memoria — pendiente (no bloqueante)

### Gestion de Documentos

- [x] `GET /collections/{id}/documents/{doc_id}` — detalle de documento con metadata
- [x] `DELETE /collections/{id}/documents/{doc_id}` — eliminar documento y sus chunks de Qdrant
- [x] Verificar que la eliminacion de chunks en Qdrant es efectiva

### Criterios de aceptacion Semana 5

- [x] Documento de 100+ paginas se ingesta correctamente
- [x] Queries retornan chunks mas relevantes — validado en RAG params harness; chunk=400/overlap=150/threshold=0.30/top_k=4 como parámetros óptimos
- [x] Eliminacion de documento limpia chunks de Qdrant
- [x] Parametros de chunking se leen de configuracion

---

## Semana 6 — QA + Preparacion de Imagenes

**Hito:** Sistema QA mas preciso. Mock de generacion de imagenes listo.
**Objetivos:** O-2, O-5
**Historias:** HU-04, HU-05

### Mejora de QA/RAG

- [x] Prompt template refinado para respuestas mas precisas y contextuales (instrucciones por categoria en `prompt_templates.py`, system prompt en `llm.py`)
- [x] Manejo de queries fuera de contexto: instruccion "Si el contexto no es suficiente, indícalo" + HTTP 422 cuando no hay chunks disponibles
- [x] Respuestas consistentes en espanol (todos los templates y system prompts en español)

### Prompt Builder (Opción C — plantillas deterministas por categoría de contenido)

- [x] `image_prompt_builder.py` creado con lógica de construcción de prompts visuales consolidado — `backend/app/engine/image_prompt_builder.py`
- [x] `build_visual_prompt()` implementada con tres estrategias deterministas por `ContentCategory`: `direct` (extended_description), `entity_only` (backstory/item), `first_sentences` (scene/chapter)
- [x] `STYLE_PREFIX` por tipo de entidad — la implementación evolucionó: el LLM extrae el tipo específico dinámicamente (`_extract_with_llm` en `image_prompt_builder.py`); el resultado se usa como prefijo del prompt visual. Enfoque más rico que un prefijo estático.
- [x] `QUALITY_SUFFIX` con tags de calidad — implementado: `QUALITY_SUFFIX = "high quality, masterpiece, sharp focus, professional digital art"` en `engine/image_prompt_builder.py`
- [x] Límite configurable de tokens en prompt visual (`image_prompt_max_tokens=512`)

### Filtrado de Contenido

- [x] `check_user_input()` en `content_guard.py` valida el contenido confirmado antes de construir el prompt visual (keywords bloqueadas: sexual explícito, discurso de odio, armas, drogas, acoso)
- [x] Rechazo de prompts menores a 10 caracteres — `min_length=10` enforced en schemas `RagQueryRequest`, `GenerateContentRequest`, `GenerateImagesRequest` (`feat(validation)` 2026-05-14)
- [x] Retorna razón de rechazo al cliente (HTTP 422 con mensaje descriptivo en español)

### Endpoint de Imagenes (Mock)

- [x] `POST /api/v1/collections/{id}/entities/{entity_id}/image-generation/build-prompt` — endpoint de construccion de prompt visual (`image_prompt_builder.py` consolidado)
- [x] `POST /api/v1/collections/{id}/entities/{entity_id}/image-generation/generate` — endpoint de generacion con mock (backend="mock" por defecto, configurable via `IMAGE_BACKEND`)
- [x] Request schema: `GenerateImageRequest` con `content_id` (UUID de contenido confirmado, obligatorio)
- [x] Response mock: retorna `images[]` con `image_url` generado, `seed`, `backend: "mock"` — sin URL real hasta integracion con Flux.2 (Semana 7)
- [x] Validacion: requiere `content_id` con status `confirmed` → HTTP 422 si pending, inexistente, o no pertenece a la entidad

### Criterios de aceptacion Semana 6

- [x] `build_visual_prompt` genera prompts coherentes por categoria de contenido (9 tests en `test_prompt_builder.py` pasando)
- [x] Contenido bloqueado es rechazado con HTTP 422 y mensaje descriptivo antes de construir el prompt
- [x] Endpoint `/image-generation/generate` retorna **201** con mock response (13 tests en `test_image_generation_service.py` pasando)
- [x] Endpoint `/image-generation/generate` retorna 422 si `content_id` no confirmado o inexistente

---

## Semana 7 — Imagenes LOCAL (ComfyUI)

**Hito:** Generacion de imagenes reales con ComfyUI + Flux.2 Klein local.
**Objetivos:** O-2
**Historias:** HU-04

### Infraestructura ComfyUI

- [x] ComfyUI instalado y corriendo en el host (puerto 8188)
- [x] Modelo Flux.2 Klein 4B Distilled (FP8) descargado (~8.4 GB VRAM)
- [x] Variables en `.env.example`: `COMFY_BACKEND=local`, `COMFY_URL`, `COMFY_TIMEOUT`
- [x] Script para levantar Ollama + ComfyUI — implementado como `dev.ps1` (Windows), `loremaster.sh` (Linux/Mac), `loremaster.bat` (menú interactivo); opción 9 levanta todo el stack

### Workflow ComfyUI

- [x] `workflows/flux2_klein_t2i.json` creado en formato API de ComfyUI
- [x] Parametros fijos: `steps=4`, `cfg=1.0`, `sampler=euler`, `scheduler=simple`
- [x] Resolucion: `1024x1024`
- [ ] Negative prompt base: nodo 100 ("CLIP Text Encode Negative Prompt") existe en `flux2-klein-4b-api.json` pero el campo `text` está vacío — `blurry, ugly, deformed…` documentado en DOCUMENTATION.md §10 pero no inyectado en el JSON del workflow (gap conocido)
- [x] Assert en cliente: `cfg` DEBE ser 1.0 (cfg > 1.0 produce imagenes degradadas)

### Cliente ComfyUI

- [x] `comfy_client.py` implementado con comunicacion HTTP/WebSocket a ComfyUI
- [x] Enviar workflow con prompt inyectado
- [x] Recibir imagen generada (bytes)
- [x] Timeout configurable vía `.env` — `COMFYUI_TIMEOUT` (default 300s) y `COMFYUI_REQUEST_TIMEOUT` (default 30s) en `Settings`; `ComfyUIClient` acepta `request_timeout` por constructor; el servicio pasa `settings.comfyui_timeout` a `get_history_until_complete`
- [x] Manejo de errores: ComfyUI no disponible → `HTTP 503` — `ComfyUIUnavailableError` (conexión rechazada) y `ComfyUITimeoutError` (timeout excedido) propagadas desde el servicio y capturadas en la ruta como 503

### Integracion con Endpoint

- [x] `/image-generation/generate` reemplaza mock por generacion real
- [x] Flujo: descripcion → build_visual_prompt → validate → ComfyUI → imagen
- [x] Retorna imagen (URL o bytes) + metadata (visual_prompt, seed)

### Criterios de aceptacion Semana 7

- [x] `POST /image-generation/generate` con descripcion genera imagen real (1024x1024)
- [x] Imagen corresponde visualmente a la descripcion proporcionada
- [x] Metadata incluye `visual_prompt` y `seed` usados
- [x] Timeout de ComfyUI retorna 503 con mensaje claro — `ComfyUITimeoutError` devuelve 503 con el mensaje del timeout configurado
- [x] `cfg=1.0` esta hardcodeado y validado

### Nota — Semana 7: integración real con ComfyUI implementada

La integración real con ComfyUI está funcional en `services/image/image_generation_service.py`:

- [x] Flujo de dos pasos implementado: `build-prompt` → `generate`
- [x] `image_backend` configurable: `"mock"` (default) o `"comfyui"`
- [x] `_generate_comfyui_images()` — envía workflow via `queue_prompt`, polling con `get_history_until_complete`, descarga imagen, guarda en filesystem local con protección anti-path-traversal
- [x] Límite de 512 tokens en prompt visual (`image_prompt_max_tokens=512`)
- [x] Seed generable por batch (base + offset por imagen)
- [x] Integración real con ComfyUI/Flux.2 Klein operativa cuando `IMAGE_BACKEND=comfyui` (requiere ComfyUI corriendo)
- [x] Errores de ComfyUI devuelven 503 diferenciado — `ComfyUIUnavailableError` y `ComfyUITimeoutError` en `core/exceptions/`

---

## Semana 8 — RAG + Imagenes Integradas

**Hito:** Generacion de imagenes usa contexto RAG. Storage S3 funcional.
**Objetivos:** O-2, O-5
**Historias:** HU-04, HU-05

### Imagenes con Contexto RAG

> **DECISIÓN (2026-05-19):** Evaluado en `metadata_harness` con llama3.2 y mistral. Añadir cabeceras
> de fuente al contexto RAG no mejoró la calidad de generación en modelos 3B (Δ D1 < +0.2).
> Feature descartada. El prompt visual se construye desde el texto del contenido confirmado (sin Qdrant).

- [ ] ~~`/image-generation/build-prompt` recupera contexto de Qdrant antes de construir prompt visual~~ — descartado (metadata_harness: sin mejora en modelos 3B)
- [ ] ~~`build_visual_prompt` recibe `lore_context` del retrieval (limitado a 200 chars)~~ — descartado
- [ ] ~~Flujo completo: documento → contexto RAG → prompt visual → ComfyUI → imagen~~ — flujo funciona sin el paso RAG intermedio

### Storage S3

> **Decisión de diseño:** S3/LocalStack reemplazado por almacenamiento local en filesystem (`core/storage/`). La integración con S3 queda pendiente para Semana 9+.

- [ ] ~~Agregar LocalStack al `docker-compose.yml` (puerto 4566)~~ — reemplazado por filesystem local
- [x] `core/storage/__init__.py` — abstracción de almacenamiento: `save_file`, `build_storage_url`, `build_generation_path` con protección anti-path-traversal
- [ ] ~~Variables: `STORAGE_BACKEND`, `S3_ENDPOINT_URL`, `S3_BUCKET`~~ — config actual: `media_root` + `storage_base_url` (filesystem local); S3 real **pendiente Fase 3**
- [x] Imágenes generadas se guardan con key única (`{uuid}.png`) bajo `users/{username}/img/generation/...`
- [x] URL de imagen retornada al cliente vía `storage_base_url + storage_path`

### Gestion de Entidades (CRUD)

- [x] `POST /api/v1/collections/{id}/entities` — crear entidad (type, name, attributes)
- [x] `GET /api/v1/collections/{id}/entities` — listar entidades
- [x] `GET /api/v1/collections/{id}/entities/{entity_id}` — detalle
- [x] `PATCH /api/v1/collections/{id}/entities/{entity_id}` — actualizar (implementado como PATCH, no PUT)
- [x] `DELETE /api/v1/collections/{id}/entities/{entity_id}` — soft delete
- [x] Tipos soportados: `character`, `creature`, `location`, `faction`, `item` (evolucionó respecto al plan original)
- [ ] ~~`attributes` como JSONB con validacion por tipo~~ — campo `description` string en su lugar

### Registro de Imagenes

- [x] Tabla/modelo `ImageRecord` (`generated_images`) con: `visual_prompt`, `prompt_token_count`, `prompt_source`, `prompt_strategy`, `backend`, `generation_ms`, `entity_id`, `content_id` — migración `ca1c120370d0`
- [x] Cada imagen generada queda registrada con trazabilidad completa (persiste en DB al generar)
- [x] Imagen asociada a `entity_id` y `content_id` (el diseño evolucionó: asociación directa, no opcional)

### Criterios de aceptacion Semana 8

- [ ] ~~Flujo completo: ingestar lore → build-prompt con contexto RAG → imagen coherente con el lore~~ — descartado (metadata_harness)
- [ ] ~~Imagen guardada en LocalStack S3 y URL retornada al cliente~~ — filesystem local en su lugar; S3 pendiente
- [x] CRUD de entidades funcional con soft delete
- [x] Metadata de generación registrada (`visual_prompt`, `prompt_token_count`, `prompt_source`, `prompt_strategy`, `backend`, `generation_ms`)

### Nota — Source Attribution (implementado en Fase 2, fuera del plan)

- [x] `source_doc_ids: list[str]` propagado en todo el stack RAG: `rag.py` → `rag_pipeline.py` → `generation_service.py` → `GeneratedText` (columna JSON)
- [x] `SourcesModal.tsx` — modal frontend que muestra los documentos fuente de cada respuesta (`Promise.allSettled` de `getDocument()` por id)
- [x] Botón "Fuentes" en `ContentCard` visible si `source_doc_ids.length > 0`

### Checklist de Cierre Fase 2

- [ ] Todos los criterios de Semanas 5-8 cumplidos
- [x] RAG genera respuestas de texto coherentes con el lore cargado — validado con baseline evals (82/83) y RAG params harness
- [x] Imágenes se generan localmente con ComfyUI + Flux.2 Klein (requiere `IMAGE_BACKEND=comfyui` y ComfyUI corriendo)
- [ ] ~~Imágenes usan contexto RAG~~ — **descartado** (metadata_harness: sin mejora en modelos 3B)
- [ ] ~~Storage S3 funcional (LocalStack)~~ — filesystem local funcional; S3 **pendiente Fase 3**
- [x] CRUD de entidades completo
- [x] README backend y frontend actualizados

---

## Nota — Integración Clerk + Mejoras de Auth (implementado Semanas 7-8, 2026-05-14)

Implementación completa del modo dual de autenticación (local / Clerk):

### Backend

- [x] `POST /api/v1/auth/clerk/sync` — intercambia JWT de Clerk (header `Authorization: Bearer`) por cookie de sesión local (JWT HS256); crea usuario local si no existe
- [x] `GET /api/v1/auth/clerk/verify` — verifica JWT de Clerk y confirma existencia del usuario en BD
- [x] `get_or_create_clerk_user(session, payload)` en `services/auth/auth_service.py` — crea User local con `hashed_password=""` si no existe, idempotente
- [x] Bug fix crítico: `get_current_user` en `dependencies.py` usaba `decode_clerk_token()` sobre la cookie (que contiene un JWT local, no de Clerk) → revertido a `verify_token()` en todos los entornos
- [x] 7 nuevos tests en `test_auth_clerk.py` (CLERK-01 a CLERK-06 + variante sin username) — total backend: **201 tests**

### Frontend

- [x] `@clerk/clerk-react` instalado y condicionado a `VITE_CLERK_PUBLISHABLE_KEY`
- [x] `ClerkBridge` en `App.tsx` — detecta login Clerk, llama `/sync`, actualiza `AuthContext`, navega a `/`
- [x] `ProtectedRoute` con modo dual: `useUser()` de Clerk (evita race condition) o `useAuth().user` (modo local)
- [x] `LoginPage` con modo dual: `<SignIn />` de Clerk o formulario propio con tabs
- [x] `AppNavbar` con `ClerkLogoutItem` separado (cumple restricción de `useClerk()` dentro de `ClerkProvider`)
- [x] `clerkSync.ts` — `syncClerkSession(token)` — `POST /auth/clerk/sync`
- [x] `clerkConfig.ts` — `clerkKey` exportado como módulo separado (cumple Fast Refresh)
- [x] Fix: 401 ya no causa flash en blanco — `apiClient.ts` emite `CustomEvent("auth:unauthorized")`, `UnauthorizedHandler` navega con React Router sin reload
- [x] Total frontend: **121 tests** pasando

### Seguridad y Auditoría (2026-05-12/13)

- [x] Auditoría de seguridad completa documentada en `docs/AUDIT-SECURITY.md` y `docs/AUDIT-SECURITY-REVIEW3-2026-05-12.md`
- [x] `REVIEW-2026-05-13.md` — revisión de arquitectura y decisiones de diseño
- [x] Tokens viajan exclusivamente por cookie HttpOnly (nunca `localStorage`, nunca header en peticiones normales)
- [x] CSRF doble-submit cookie activo en todas las mutaciones (POST/PUT/PATCH/DELETE)
- [x] `token_version` con `hmac.compare_digest` — invalidación de sesiones por logout
- [x] Soft-delete verificado en `get_current_user` — usuarios eliminados no pueden autenticarse
- [x] Rate limiting por IP en middleware global

---

## Nota — Funcionalidades de Autenticación y Seguridad implementadas (fuera del plan original)

Sistema completo de autenticación y seguridad implementado durante Fase 2 (Semanas 7-8):

### Autenticación y Usuarios

- [x] `core/auth/__init__.py` — JWT: creación, verificación y hash de contraseñas (bcrypt)
- [x] `core/auth/clerk.py` — `JWKSManager` con caché TTL 1h thread-safe; `decode_clerk_token()` — solo en `/auth/clerk/sync`
- [x] `core/auth/dependencies.py` — `get_current_user` usa siempre `verify_token()` (JWT local en cookie, uniforme en todos los entornos); `get_admin_user`
- [x] `core/auth/csrf.py` — CSRF token via cookie doble-submit
- [x] `models/db/user.py` — Modelo `User` con `username`, `email`, `hashed_password`, `is_admin`, `token_version` (para invalidación de sesiones)
- [x] `api/routes/auth/` — registro, login, logout, refresh con cookies HttpOnly
- [x] `api/routes/users/users.py` — perfil de usuario autenticado
- [x] `api/routes/admin/admin.py` — gestión de usuarios (requiere `is_admin=True`)
- [x] `services/profile/profile_service.py` — lógica de perfil

### Seguridad y Middlewares

- [x] `api/middlewares/rate_limit.py` — rate limiting por IP
- [x] `api/middlewares/security_headers.py` — cabeceras de seguridad (CSP, HSTS, X-Frame-Options, etc.)
- [x] `core/storage/validator.py` — `FileValidator`: validación de magic bytes, EXIF strip en imágenes, extensión y MIME

### Feed Público

- [x] `api/routes/public/public.py` — feed de imágenes compartidas públicamente (`is_shared=True`)
- [x] `services/public/public_service.py` — lógica de listado del feed
- [x] `api/routes/media.py` — servicio de imágenes estáticas con control de acceso (propias o compartidas)
- [x] Endpoint `PATCH .../share` — marcar/desmarcar imagen como pública
- [x] `services/moderation/moderation_service.py` + `models/db/moderation_log.py` — registro de moderación

---

## Nota — Correcciones de calidad y consistencia (2026-05-15)

Fixes de consistencia entre capas y eliminación de código muerto aplicados sobre el estado de Semana 8:

### Backend

- [x] **DOC-17 — filename > 255 chars → 422**: `Document.filename` validado en servicio antes de persistir; previene error DB-level en PostgreSQL (`VARCHAR(255)`). Mensaje: `"Nombre de archivo requerido o demasiado largo (máx. 255 caracteres)"`
- [x] **Timeout extraído a settings**: `_EXTRACTION_TIMEOUT_SECONDS = 30` (hardcoded en `document_service.py`) movido a `settings.document_extraction_timeout_seconds`; variable `DOCUMENT_EXTRACTION_TIMEOUT_SECONDS` añadida a `.env` y `.env.example`
- [x] **Schema tipado**: `ImageGenerationResponse.category` e `ImageGenerationListItem.category` cambiados de `str` a `ContentCategory` para type safety
- [x] **DB default alineado**: `ImageGeneration.backend` default corregido de `"mock"` a `"comfyui"` — consistente con `settings.image_backend`
- [x] **Dead code eliminado**: `backend/app/core/database/mixins.py` borrado — contenía `generate_id()`, `utc_now()` y `SoftDeleteMixin` duplicado, nunca importados en ningún fichero de `app/` ni `tests/`
- [x] Total backend: **201 tests** (18 archivos; 7 tests de `test_auth_clerk.py` ya contados)
- [x] `LIMITERS.md` actualizado: `Document.filename` max=255 chars y `document_extraction_timeout_seconds=30s` documentados en §2 y §4

### Documentación
- [x] `backend/README.md` y `frontend/README.md` actualizados con estructura de proyecto actual, variables `.env` completas y test counts

---

# Fase 3 — Produccion + RunPod (Semanas 9-12)

**Objetivo de fase:** Preparar sistema real con persistencia, cloud y optimizacion.
**Prerequisito:** Fase 2 estable y funcional.

---

## Semana 9 — Docker + Arquitectura Limpia ✅ (completada 2026-05-25)

**Hito:** Backend containerizado. Concurrencia LLM resuelta.
**Objetivos:** O-3, O-7
**Historias:** Todas

### Dockerizacion

- [x] `backend/Dockerfile` funcional (multi-stage) — builder instala deps y pre-descarga embedding model; runtime con usuario no-root `loremaster`
- [x] `backend/.dockerignore` — excluye venv, DB, media, tests, evals, caches
- [x] `docker-compose.prod.yml` con servicio `app` FastAPI containerizado — `depends_on` con condición `service_healthy` en PG, Redis y Qdrant
- [x] Health checks para PostgreSQL y Redis en compose — ya presentes en prod; Qdrant añadido (`/healthz`)
- [x] Volumenes persistentes para Qdrant — configurado en `docker-compose.yml`
- [x] Variables de entorno via `.env` (no hardcodeadas en compose) — Pydantic Settings completo

### Migracion a PostgreSQL

- [x] PostgreSQL real soportado via `docker-compose.postgres.yml` (overlay) — `make infra-pg` lo levanta
- [x] `database.py` con conexion SQLAlchemy/SQLModel y manejo de sesiones
- [x] Migraciones Alembic contra PostgreSQL — corren en startup via `lifespan.py` (`asyncio.to_thread`); `SKIP_MIGRATIONS=true` disponible para eval
- [x] Todas las tablas creadas correctamente por Alembic
- [x] Índice FK `ix_entities_collection_id` — migración `a1b2c3d4e5f6`

### Concurrencia LLM

- [x] HTTP 429 + `Retry-After: 30` cuando el semáforo LLM está ocupado — `LLMBusyError` en `rag_pipeline.py` e `image_prompt_builder.py`; capturado en `rag_query.py`, `content.py` e `image_generation.py`

### Moderación Semántica — Llama Guard 3 (implementado adelantado en Semana 9)

- [x] `app/domain/llama_guard.py` — módulo de moderación semántica con prompt exacto del formato LG3 (categorías S1-S13, evaluación del rol `Agent`)
- [x] Integrado en `rag_query_service` y `generation_service` tras `check_generated_output()` — segunda capa después de content_guard
- [x] Fail-open: timeout, error de red o parseo inesperado → `logger.warning` + pasa sin bloquear
- [x] `LLAMA_GUARD_ENABLED=false` por defecto (activar en demo/producción con `ollama pull llama-guard3:8b`)
- [x] Settings: `llama_guard_enabled`, `llama_guard_model` (`llama-guard3:8b`), `llama_guard_timeout` (5.0s)
- [x] 9 tests en `test_llama_guard.py` — total backend: **309 tests**

### Refactorizacion de Codigo

- [ ] ~~Estandarizar envelope de respuestas API~~ — no adoptado; schemas Pydantic directos + `PaginatedResponse`
- [x] HTTPException movido a routes — services usan excepciones de dominio; routes las capturan con try/except tipado
- [x] Try/except en rutas críticas — colecciones, documentos y entidades tienen manejo de excepciones de dominio
- [x] Logging en servicios principales — `logger.` activo en generation_service, rag_pipeline, documents_service y otros
- [x] Typo `exiting_collections` — verificado, no existe en el código actual

### Observabilidad Basica

- [ ] Prometheus + Grafana — diferido a Semana 12 (no bloquea el deploy privado)

### Criterios de aceptacion Semana 9

- [x] `docker compose -f docker-compose.prod.yml up` levanta TODO el stack (requiere `.env` con `SECRET_KEY`, `POSTGRES_*`, `STORAGE_BASE_URL`, `ALLOWED_ORIGINS`)
- [x] Datos persisten entre reinicios — PostgreSQL + Qdrant con volúmenes persistentes
- [x] Flujo completo funciona con PostgreSQL — validado; `make dev-pg` levanta el stack completo
- [x] LLM ocupado retorna 429 con `Retry-After` en lugar de bloquear el worker
- [ ] ~~Respuestas API usan formato estandarizado~~ — no adoptado
- [ ] Grafana muestra metricas basicas del sistema — diferido

---

## Semana 10 — RunPod Basico (Imagenes)

**Hito:** Worker RunPod funcional. Generacion de imagenes en la nube.
**Objetivos:** O-6
**Historias:** HU-04

### RunPod Worker

- [ ] `runpod_worker/Dockerfile` creado: base NVIDIA CUDA + ComfyUI + RunPod SDK
- [ ] `runpod_worker/builder/setup.sh` descarga modelo Flux.2 Klein durante build
- [ ] `runpod_worker/src/handler.py` implementado: recibe prompt → ComfyUI → retorna imagen
- [ ] `runpod_worker/requirements.txt`: `runpod`, `torch`, `httpx`

### Testing Manual

- [ ] Imagen Docker construida y probada localmente (si hay GPU disponible)
- [ ] Worker desplegado en RunPod Serverless
- [ ] Script de test: enviar prompt manualmente via API RunPod → recibir imagen
- [ ] Verificar cold start time (documentar: esperado 20-60s)
- [ ] Verificar que parametros fijos (cfg=1.0, steps=4) se mantienen

### Configuracion RunPod

- [ ] Variables en `.env.prod.example`: `RUNPOD_API_KEY`, `RUNPOD_ENDPOINT_ID`, `RUNPOD_ENDPOINT_URL`
- [ ] Limite de presupuesto configurado en RunPod dashboard
- [ ] Usar `runsync` (sincronico) para el prototipo

### Criterios de aceptacion Semana 10

- [ ] Worker RunPod genera imagen desde prompt enviado manualmente
- [ ] Imagen generada es de calidad comparable a la generacion local
- [ ] Cold start documentado
- [ ] Presupuesto configurado en RunPod

---

## Semana 11 — Integracion RunPod en API

**Hito:** API soporta ambos backends de imagenes (local y RunPod).
**Objetivos:** O-6
**Historias:** HU-04

### RunPod Client

- [ ] `runpod_client.py` implementado: cliente HTTP async para RunPod API
- [ ] Enviar prompt via `runsync` endpoint
- [ ] Recibir imagen (bytes o URL)
- [ ] Manejo de timeout (configurable, default 120s para RunPod)
- [ ] Manejo de errores: RunPod no disponible → `HTTP 503`

### Switch Local/RunPod

- [ ] `comfy_client.py` detecta `COMFY_BACKEND` env var
- [ ] `COMFY_BACKEND=local` → usa ComfyUI local
- [ ] `COMFY_BACKEND=runpod` → usa RunPod client
- [ ] Mismo endpoint `/generate/image` soporta ambos backends transparentemente
- [ ] Metadata de imagen incluye campo `backend: 'local' | 'runpod'`

### Storage Produccion

- [ ] `storage.py` soporta switch entre LocalStack (dev) y S3/R2 real (prod)
- [ ] Variable `STORAGE_BACKEND`: `localstack` o `s3`
- [ ] Probar con Cloudflare R2 si es posible (egress gratuito)

### Criterios de aceptacion Semana 11

- [ ] `/image-generation/generate` genera imagen via RunPod cuando `COMFY_BACKEND=runpod`
- [ ] `/image-generation/generate` genera imagen via ComfyUI local cuando `COMFY_BACKEND=local`
- [ ] Imagen se guarda en S3 real (no solo LocalStack)
- [ ] Metadata registra correctamente el backend usado
- [ ] Switch entre backends no requiere cambio de codigo

---

## Semana 12 — Cache + Evaluacion + Demo Final

**Hito:** Sistema completo con cache, evaluacion y documentacion.
**Objetivos:** O-7, O-8
**Historias:** Todas

### Cache Redis

- [ ] Redis integrado en el flujo de generacion de texto
- [ ] Cache semantico: queries con similitud coseno >= 0.95 reutilizan respuesta
- [ ] TTL configurable (default 3600s)
- [ ] Metrica `loremaster_cache_hit_ratio` exportada a Prometheus
- [ ] Verificar que cache reduce latencia en queries repetidas

### Evaluacion

- [ ] Evaluacion basica de calidad RAG (manual o con RAGAS)
- [ ] Documentar resultados: precision del retrieval, coherencia de respuestas
- [ ] Comparar tiempos de generacion: local vs RunPod
- [ ] Documentar metricas de rendimiento: latencia p95, throughput

### Observabilidad Completa

- [ ] Todas las metricas de la tabla 9.1 exportadas:
  - [ ] `loremaster_requests_total`
  - [ ] `loremaster_request_duration_seconds`
  - [ ] `loremaster_llm_tokens_generated_total`
  - [ ] `loremaster_image_generation_seconds`
  - [ ] `loremaster_comfy_queue_depth`
  - [ ] `loremaster_cache_hit_ratio`
  - [ ] `loremaster_qdrant_search_seconds`
  - [ ] `loremaster_storage_bytes_total`
- [ ] Dashboard Grafana con todas las metricas y alertas configuradas

### Documentacion Final

- [ ] README completo con:
  - [ ] Descripcion del proyecto
  - [ ] Instrucciones de setup local (paso a paso)
  - [ ] Instrucciones de despliegue en nube (RunPod + VPS)
  - [ ] Variables de entorno documentadas
  - [ ] Arquitectura y diagramas
- [ ] Guia de troubleshooting para problemas comunes
- [ ] Changelog con features implementadas por fase

### Demo Final

- [ ] Demo end-to-end grabada o en vivo:
  1. [ ] Crear coleccion
  2. [ ] Ingestar documento PDF con lore
  3. [ ] Hacer query de texto → respuesta RAG coherente
  4. [ ] Generar imagen desde contexto RAG (local)
  5. [ ] Generar imagen desde contexto RAG (RunPod)
  6. [ ] Mostrar entidades creadas
  7. [ ] Mostrar dashboard Grafana con metricas
  8. [ ] Mostrar cache hit en query repetida

### Criterios de aceptacion Semana 12

- [ ] Cache Redis reduce latencia en queries repetidas (medible)
- [ ] Dashboard Grafana muestra metricas en tiempo real
- [ ] Documentacion permite a un nuevo desarrollador hacer setup desde cero
- [ ] Demo completa ejecutada sin errores criticos

### Checklist de Cierre Fase 3

- [ ] Todos los criterios de Semanas 9-12 cumplidos
- [ ] Stack completo dockerizado y funcional
- [ ] PostgreSQL como DB principal (no mock)
- [ ] RunPod funcional como backend alternativo de imagenes
- [ ] Cache Redis activo y medible
- [ ] Observabilidad con Prometheus + Grafana
- [ ] Documentacion completa
- [ ] Demo exitosa

---

# Resumen de Objetivos por Fase

| Objetivo | Descripcion                        | Fase | Semanas               |
| -------- | ---------------------------------- | ---- | --------------------- |
| O-1      | Pipeline RAG completo              | 1    | 2-4                   |
| O-2      | Integracion ComfyUI + Flux.2 Klein | 2    | 6-8                   |
| O-3      | API REST completa con FastAPI      | 1-3  | 1, 4, 9               |
| O-4      | Interfaz de usuario web (SPA)      | 2    | Fuera del MVP backend |
| O-5      | Almacenamiento S3                  | 2    | 8                     |
| O-6      | Worker ComfyUI en RunPod           | 3    | 10-11                 |
| O-7      | Observabilidad (Grafana)           | 1-3  | 9, 12                 |
| O-8      | Documentacion y guia               | 3    | 12                    |

# Cobertura de Historias de Usuario

| Historia | Descripcion               | Semanas donde se trabaja |
| -------- | ------------------------- | ------------------------ |
| HU-01    | Crear coleccion           | 1, 4                     |
| HU-02    | Ingestion de documentos   | 2, 5                     |
| HU-03    | Generacion de texto (RAG) | 3, 4, 5, 6               |
| HU-04    | Generacion de imagenes    | 6, 7, 8, 10, 11          |
| HU-05    | Gestion de entidades      | 8                        |
