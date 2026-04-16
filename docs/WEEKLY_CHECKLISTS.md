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
- [ ] Verificar conectividad: Qdrant dashboard accesible en `http://localhost:6333/dashboard`

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

- [ ] `docker compose up qdrant` levanta sin errores
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

- [ ] Agregar a `requirements.txt`: `langchain-ollama`
- [ ] Variables en `.env.example`: `OLLAMA_BASE_URL`, `OLLAMA_MODEL`
- [ ] Verificar que Ollama esta corriendo con modelo `llama3.2` disponible
- [ ] `config.py` con Pydantic Settings: `TEMPERATURE` (0.7), `MAX_TOKENS` (500)

### Generate Service

- [ ] `generate_service.py` orquesta: query → retrieval → prompt → LLM → response
- [ ] Prompt template en espanol para narrativa/worldbuilding
- [ ] Parametros de generacion configurables: `temperature`, `max_tokens`
- [ ] Respuesta incluye texto generado y conteo de fuentes usadas

### Endpoints Completos Fase 1

- [ ] `POST /collections` — creacion con nombre unico (409 si duplicado)
- [ ] `GET /collections` — listado completo
- [ ] `GET /collections/{id}` — detalle
- [ ] `DELETE /collections/{id}` — eliminacion
- [ ] `POST /collections/{id}/documents` — ingesta completa
- [ ] `GET /collections/{id}/documents` — listado de documentos
- [ ] `POST /collections/{id}/generate/text` — generacion RAG completa

### Criterios de aceptacion Semana 4

- [ ] Flujo completo: crear coleccion → subir PDF → hacer query → recibir respuesta coherente del LLM
- [ ] La respuesta del LLM esta fundamentada en el contenido del documento (no inventa)
- [ ] Si el contexto no tiene informacion suficiente, el LLM lo indica
- [ ] Todos los endpoints documentados en Swagger
- [ ] Crear coleccion con nombre duplicado retorna 409

### Checklist de Cierre Fase 1

- [ ] Todos los criterios de Semanas 1-4 cumplidos
- [ ] Pipeline RAG funcional de extremo a extremo
- [ ] Cero errores criticos en flujo principal
- [ ] Swagger documenta todos los endpoints activos
- [ ] README actualizado con instrucciones de setup local

---

# Fase 2 — RAG Avanzado + Imagenes Locales (Semanas 5-8)

**Objetivo de fase:** Sistema RAG usable + introduccion progresiva de imagenes.
**Prerequisito:** Fase 1 estable y funcional.

---

## Semana 5 — RAG Intermedio

**Hito:** Mejora de calidad de retrieval y soporte para documentos grandes.
**Objetivos:** O-1
**Historias:** HU-02, HU-03

### Mejora de Chunking

- [ ] Parametros de chunking configurables via `.env`: `CHUNK_SIZE`, `CHUNK_OVERLAP`
- [ ] Experimentar con chunk sizes (256, 512, 1024) y documentar resultados
- [ ] Verificar que overlap previene perdida de contexto en fronteras de chunks

### Mejora de Retrieval

- [ ] `score_threshold` configurable para filtrar resultados de baja relevancia
- [ ] `top_k` configurable (default 4, permitir ajuste por request)
- [ ] Logging basico de queries y scores de retrieval

### Soporte Documentos Grandes

- [ ] Probar ingesta con PDFs > 10 paginas
- [ ] Probar ingesta con PDFs > 50 paginas
- [ ] Verificar que el chunking no pierde contenido en documentos largos
- [ ] Monitorear tiempo de ingesta y uso de memoria

### Gestion de Documentos

- [ ] `GET /collections/{id}/documents/{doc_id}` — detalle de documento con metadata
- [ ] `DELETE /collections/{id}/documents/{doc_id}` — eliminar documento y sus chunks de Qdrant
- [ ] Verificar que la eliminacion de chunks en Qdrant es efectiva

### Criterios de aceptacion Semana 5

- [ ] Documento de 100+ paginas se ingesta correctamente
- [ ] Queries retornan chunks mas relevantes (mejora cualitativa vs Semana 4)
- [ ] Eliminacion de documento limpia chunks de Qdrant
- [ ] Parametros de chunking se leen de configuracion

---

## Semana 6 — QA + Preparacion de Imagenes

**Hito:** Sistema QA mas preciso. Mock de generacion de imagenes listo.
**Objetivos:** O-2, O-5
**Historias:** HU-04, HU-05

### Mejora de QA/RAG

- [ ] Prompt template refinado para respuestas mas precisas y contextuales
- [ ] Manejo de queries fuera de contexto (el LLM responde "no hay informacion suficiente")
- [ ] Respuestas consistentes en espanol

### Prompt Builder

- [ ] `prompt_builder.py` creado con logica de construccion de prompts visuales
- [ ] `STYLE_PREFIX` definido por tipo de entidad: character, scene, faction, item
- [ ] `QUALITY_SUFFIX` con tags de calidad para Flux.2
- [ ] Funcion `build_visual_prompt(entity_type, user_description, lore_context)` implementada
- [ ] Limite de 500 caracteres en prompt visual (restriccion Flux.2 Klein)

### Filtrado de Contenido

- [ ] `validate_prompt()` implementado con lista de keywords bloqueadas
- [ ] Rechazo de prompts menores a 10 caracteres
- [ ] Retorna razon de rechazo al cliente

### Endpoint de Imagenes (Mock)

- [ ] `POST /api/v1/collections/{id}/generate/image` — endpoint creado
- [ ] Request schema: `description`, `entity_type` (opcional), `entity_id` (opcional)
- [ ] Response mock: retorna URL placeholder + visual_prompt generado
- [ ] Validacion: requiere al menos 1 documento en la coleccion

### Criterios de aceptacion Semana 6

- [ ] `build_visual_prompt` genera prompts coherentes por tipo de entidad
- [ ] `validate_prompt` rechaza contenido bloqueado con mensaje claro
- [ ] Endpoint `/generate/image` retorna 200 con mock response
- [ ] Endpoint `/generate/image` retorna 422 si coleccion sin documentos

---

## Semana 7 — Imagenes LOCAL (ComfyUI)

**Hito:** Generacion de imagenes reales con ComfyUI + Flux.2 Klein local.
**Objetivos:** O-2
**Historias:** HU-04

### Infraestructura ComfyUI

- [ ] ComfyUI instalado y corriendo en el host (puerto 8188)
- [ ] Modelo Flux.2 Klein 4B Distilled (FP8) descargado (~8.4 GB VRAM)
- [ ] Variables en `.env.example`: `COMFY_BACKEND=local`, `COMFY_URL`, `COMFY_TIMEOUT`
- [ ] `start_local.sh` script para levantar Ollama + ComfyUI

### Workflow ComfyUI

- [ ] `workflows/flux2_klein_t2i.json` creado en formato API de ComfyUI
- [ ] Parametros fijos: `steps=4`, `cfg=1.0`, `sampler=euler`, `scheduler=simple`
- [ ] Resolucion: `1024x1024`
- [ ] Negative prompt base: `blurry, ugly, deformed, watermark, text, extra limbs, worst quality`
- [ ] Assert en cliente: `cfg` DEBE ser 1.0 (cfg > 1.0 produce imagenes degradadas)

### Cliente ComfyUI

- [ ] `comfy_client.py` implementado con comunicacion HTTP/WebSocket a ComfyUI
- [ ] Enviar workflow con prompt inyectado
- [ ] Recibir imagen generada (bytes)
- [ ] Timeout configurable (default 60s)
- [ ] Manejo de errores: ComfyUI no disponible → `HTTP 503`

### Integracion con Endpoint

- [ ] `/generate/image` reemplaza mock por generacion real
- [ ] Flujo: descripcion → build_visual_prompt → validate → ComfyUI → imagen
- [ ] Retorna imagen (URL o bytes) + metadata (visual_prompt, seed)

### Criterios de aceptacion Semana 7

- [ ] `POST /generate/image` con descripcion genera imagen real (1024x1024)
- [ ] Imagen corresponde visualmente a la descripcion proporcionada
- [ ] Metadata incluye `visual_prompt` y `seed` usados
- [ ] Timeout de ComfyUI retorna 503 con mensaje claro
- [ ] `cfg=1.0` esta hardcodeado y validado

---

## Semana 8 — RAG + Imagenes Integradas

**Hito:** Generacion de imagenes usa contexto RAG. Storage S3 funcional.
**Objetivos:** O-2, O-5
**Historias:** HU-04, HU-05

### Imagenes con Contexto RAG

- [ ] `/generate/image` recupera contexto de Qdrant antes de construir prompt visual
- [ ] `build_visual_prompt` recibe `lore_context` del retrieval (limitado a 200 chars)
- [ ] Flujo completo: documento → contexto RAG → prompt visual → ComfyUI → imagen

### Storage S3

- [ ] Agregar LocalStack al `docker-compose.yml` (puerto 4566)
- [ ] `storage.py` con abstraccion para subir/descargar de S3
- [ ] Variables: `STORAGE_BACKEND`, `S3_ENDPOINT_URL`, `S3_BUCKET`
- [ ] Imagenes generadas se guardan en S3 con key unica
- [ ] Retornar URL de S3 al cliente

### Gestion de Entidades (CRUD)

- [ ] `POST /api/v1/collections/{id}/entities` — crear entidad (type, name, attributes)
- [ ] `GET /api/v1/collections/{id}/entities` — listar entidades
- [ ] `GET /api/v1/collections/{id}/entities/{entity_id}` — detalle
- [ ] `PUT /api/v1/collections/{id}/entities/{entity_id}` — actualizar
- [ ] `DELETE /api/v1/collections/{id}/entities/{entity_id}` — soft delete
- [ ] Tipos soportados: `character`, `scene`, `faction`, `item`
- [ ] `attributes` como JSONB con validacion por tipo

### Registro de Imagenes

- [ ] Tabla/modelo `generated_images` con: `visual_prompt`, `seed`, `model_version`, `generation_ms`, `backend`
- [ ] Cada imagen generada queda registrada con trazabilidad completa
- [ ] Imagen puede asociarse opcionalmente a una entidad (`entity_id`)

### Criterios de aceptacion Semana 8

- [ ] Flujo completo: ingestar lore → query de imagen → imagen coherente con el lore
- [ ] Imagen guardada en LocalStack S3 y URL retornada al cliente
- [ ] CRUD de entidades funcional con soft delete
- [ ] Metadata de generacion registrada (prompt, seed, tiempo, backend)

### Checklist de Cierre Fase 2

- [ ] Todos los criterios de Semanas 5-8 cumplidos
- [ ] RAG genera respuestas de texto de alta calidad
- [ ] Imagenes se generan localmente con ComfyUI + Flux.2 Klein
- [ ] Imagenes usan contexto RAG para coherencia con el lore
- [ ] Storage S3 funcional (LocalStack)
- [ ] CRUD de entidades completo
- [ ] README actualizado con instrucciones de ComfyUI y S3

---

# Fase 3 — Produccion + RunPod (Semanas 9-12)

**Objetivo de fase:** Preparar sistema real con persistencia, cloud y optimizacion.
**Prerequisito:** Fase 2 estable y funcional.

---

## Semana 9 — Docker + Arquitectura Limpia

**Hito:** Todo containerizado. Codigo refactorizado y estable.
**Objetivos:** O-3, O-7
**Historias:** Todas

### Dockerizacion

- [ ] `backend/Dockerfile` funcional (multi-stage build recomendado)
- [ ] `docker-compose.yml` completo con todos los servicios: FastAPI, Qdrant, PostgreSQL, Redis, LocalStack
- [ ] Health checks configurados para PostgreSQL y Redis
- [ ] Volumenes persistentes para Qdrant y PostgreSQL
- [ ] Variables de entorno via `.env` (no hardcodeadas en compose)

### Migracion a PostgreSQL

- [ ] Reemplazar `documents_db_mock.py` (dicts en memoria) por PostgreSQL real
- [ ] `database.py` con conexion SQLAlchemy/SQLModel y manejo de sesiones
- [ ] Ejecutar migracion Alembic (`bbf7508d7c6c_init.py`) contra PostgreSQL
- [ ] Verificar que todas las tablas se crean correctamente: `collections`, `documents`, `entities`
- [ ] Agregar indices faltantes (ej: `collection_id` en entities)

### Refactorizacion de Codigo

- [ ] Estandarizar envelope de respuestas API: `{"data": ..., "status": "success", "count": N}`
- [ ] Mover HTTPException de services a routes (desacoplar capa de servicio)
- [ ] Agregar try/except en rutas criticas: extraccion PDF, embeddings, operaciones Qdrant
- [ ] Implementar logging estructurado (al menos en servicios principales)
- [ ] Corregir typo: `exiting_collections` → `existing_collections` en `rag_engine.py`

### Observabilidad Basica

- [ ] Agregar Prometheus a `docker-compose.yml` (puerto 9090)
- [ ] Agregar Grafana a `docker-compose.yml` (puerto 3000)
- [ ] Exportar metricas basicas: `loremaster_requests_total`, `loremaster_request_duration_seconds`
- [ ] Dashboard Grafana con latencia p95 y tasa de error

### Criterios de aceptacion Semana 9

- [ ] `docker compose up` levanta TODO el stack sin errores
- [ ] Datos persisten entre reinicios del contenedor (PostgreSQL + Qdrant)
- [ ] Flujo completo funciona con PostgreSQL (no mas mock DB)
- [ ] Respuestas API usan formato estandarizado
- [ ] Grafana muestra metricas basicas del sistema

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

- [ ] `/generate/image` genera imagen via RunPod cuando `COMFY_BACKEND=runpod`
- [ ] `/generate/image` genera imagen via ComfyUI local cuando `COMFY_BACKEND=local`
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
