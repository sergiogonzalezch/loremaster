# 1. Resumen Ejecutivo

## ¿Qué es Lore Master?

Lore Master es una plataforma web interactiva para escritores, narradores de rol (RPG), diseñadores de videojuegos y creadores de contenido que necesitan construir, organizar y expandir mundos ficticios de manera coherente y visualmente rica.

A diferencia de los asistentes de IA genéricos basados en chat, Lore Master ofrece un flujo de trabajo estructurado donde el usuario carga documentos de referencia (PDF o TXT) con el lore de su mundo y el sistema genera texto enriquecido e imágenes coherentes con ese contexto, usando una arquitectura RAG (Retrieval-Augmented Generation).

## ¿Qué hace?

- Ingesta y vectoriza documentos de lore (PDF/TXT) proporcionados por el usuario.
- Recupera contexto relevante del lore antes de cada generación de texto o imagen.
- Genera texto narrativo expandido, consistente con la lore cargada.
- Genera **contenidos RAG por categoría** para cada entidad: el usuario puede editar, confirmar (descarta automáticamente los demás pendientes de la misma categoría) o descartar cada contenido.
- Construye prompts visuales automáticamente y genera imágenes a través de ComfyUI + Flux.2 Klein 4B.
- Gestiona entidades del mundo (personajes, escenarios, facciones, ítems) con atributos estructurados.
- Almacena todas las imágenes y metadatos generados en S3 (local o nube).

## ¿Qué problema resuelve?

| **Problema**                       | **Impacto en el creador**                                                         | **Solución de Lore Master**                                                        |
| ---------------------------------- | --------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| **Fragmentación del lore**         | Notas dispersas en documentos sin conexión; difícil mantener coherencia.          | Centraliza todo en una base vectorial consultable en tiempo real.                  |
| **Inconsistencia con IA genérica** | Los modelos no conocen el mundo del usuario y generan contradicciones.            | RAG ancla cada respuesta en el lore real del usuario.                              |
| **Fricción en generación visual**  | Pasar de descripción a imagen requiere múltiples herramientas y prompts manuales. | El sistema construye el prompt visual automáticamente desde el contexto RAG.       |
| **Costos de APIs externas**        | Dependencia de servicios de pago por token/imagen sin control del contexto.       | Stack local open-source. Sin costos por token. RunPod solo cuando se necesita GPU. |

## Propuesta de valor

| **Característica**              | **Beneficio**                                                                                  |
| ------------------------------- | ---------------------------------------------------------------------------------------------- |
| **Coherencia narrativa**        | El RAG garantiza que todo el contenido generado esté fundamentado en el lore real del usuario. |
| **Generación visual integrada** | Imágenes generadas directamente desde la plataforma, sin salir ni copiar prompts.              |
| **Flujo no-chat**               | Paneles especializados por tipo de entidad. Workflow orientado a la creación, no al chat.      |
| **Open Source + control total** | Modelos locales (Ollama + Flux.2 Klein). Sin lock-in de APIs de pago.                          |
| **Escalable por diseño**        | Local durante el desarrollo; RunPod en producción con cambios mínimos de configuración.        |

# 2. Objetivos del Proyecto

## Objetivo general

Construir un prototipo funcional y escalable de Lore Master que demuestre la viabilidad técnica del ciclo completo: ingestión de lore → generación de texto RAG → generación de imágenes → gestión de entidades, ejecutable en hardware local y desplegable en nube con RunPod.

## Objetivos específicos y entregables

| **#**   | **Objetivo**                               | **Entregable verificable**                                                        | **Fase** |
| ------- | ------------------------------------------ | --------------------------------------------------------------------------------- | -------- |
| **O-1** | Implementar el pipeline RAG completo       | Endpoint /generate/text retorna texto fundamentado en el lore con fuentes citadas | Fase 1   |
| **O-2** | Integrar ComfyUI con Flux.2 Klein 4B       | Endpoint /generate/image retorna URL de imagen generada en < 30 s localmente      | Fase 1   |
| **O-3** | Construir la API REST completa con FastAPI | “N” endpoints documentados y funcionales en /docs (Swagger)                       | Fase 1   |
| **O-4** | Desarrollar la interfaz de usuario web     | SPA con paneles de personajes, escenarios, facciones e ítems                      | Fase 2   |
| **O-5** | Implementar almacenamiento S3              | Imágenes guardadas en LocalStack S3 (dev) / AWS S3 o R2 (prod)                    | Fase 2   |
| **O-6** | Desplegar el worker de ComfyUI en RunPod   | Imagen Docker funcional en RunPod Serverless con Flux.2 Klein                     | Fase 3   |
| **O-7** | Configurar observabilidad                  | Dashboard Grafana con latencia p95, tasa de error y cola de imágenes              | Fase 1-2 |
| **O-8** | Documentar y guiar la realización          | README + guía paso a paso para setup local y despliegue en nube                   | Fase 3   |

## Alcance del MVP

- Soporte de archivos PDF y TXT de hasta 50 MB por documento.
- Generación de texto hasta 2 000 tokens por consulta, con streaming opcional.
- Generación de imágenes 1024 × 1024 px con Flux.2 Klein 4B Distilled (FP8).
- Cinco tipos de entidad: character, creature, location, faction, item.
- Un usuario por instancia en el prototipo (multi-tenant fuera del alcance del MVP).

# 3. Características e Historias de Usuario

Las historias cubren el ciclo completo del creador de mundos, utilizando **collections como unidad principal del sistema**.

## Tabla de historias

| **ID**    | **Historia**              | **Enunciado completo**                                                                                                                                 |
| --------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **HU-01** | Crear colección           | Como creador de mundos, quiero crear una colección (world) para organizar documentos, entidades e imágenes dentro de un mismo contexto narrativo.      |
| **HU-02** | Ingestión de documentos   | Como creador de mundos, quiero subir archivos PDF o TXT a una colección para que el sistema los procese y los use como base para futuras generaciones. |
| **HU-03** | Generación de texto (RAG) | Como creador de mundos, quiero hacer consultas sobre una colección para obtener texto coherente basado en el lore cargado.                             |
| **HU-04** | Generación de imágenes    | Como creador de mundos, quiero generar imágenes consistentes con mi lore utilizando contexto de la colección.                                          |
| **HU-05** | Gestión de entidades      | Como creador de mundos, quiero gestionar personajes, escenarios y objetos dentro de una colección para estructurar mi mundo.                           |
| **HU-06** | Contenidos RAG por categoría | Como creador de mundos, quiero generar contenidos RAG por categoría para una entidad y confirmar el mejor para actualizar su descripción automáticamente.   |

---

# HU-01 — Crear colección

### Diagramas

- Diagrama de flujo — Creación de colección

> *Diagrama pendiente de actualización — ver carpeta `docs/diagrams/`*

- Diagrama de secuencia — Cliente → FastAPI → DB

> *Diagrama pendiente de actualización — ver carpeta `docs/diagrams/`*

### Criterios de aceptación

- Permite crear una colección con nombre y descripción
- Retorna `collection_id`
- Permite listar colecciones existentes
- Cada colección es independiente

# HU-02 — Ingestión de documentos

### Diagramas

- Diagrama de flujo — Ingestión de documentos

> *Diagrama pendiente de actualización — ver carpeta `docs/diagrams/`*

- Diagrama de secuencia — Cliente → FastAPI → Qdrant

> *Diagrama pendiente de actualización — ver carpeta `docs/diagrams/`*

### Criterios de aceptación (corregidos)

- Acepta PDF (`application/pdf`) y TXT (`text/plain`) hasta 50 MB
- Rechaza formatos inválidos con `HTTP 400`
- El documento se asocia a una colección (`collection_id`)
- El procesamiento es síncrono en el MVP (asíncrono en versiones futuras)
- El contenido queda disponible para consultas RAG dentro de la colección

### Secuencia corregida

| **Paso** | **Actor → Actor** | **Mensaje / Operación**               |
| -------- | ----------------- | ------------------------------------- |
| 1        | Cliente → FastAPI | POST /collections/{id}/documents      |
| 2        | FastAPI           | Valida tipo y tamaño                  |
| 3        | FastAPI           | Extrae texto                          |
| 4        | FastAPI           | chunking                              |
| 5        | FastAPI → Qdrant  | Guarda embeddings con `collection_id` |
| 6        | FastAPI → Cliente | HTTP 200 { doc_id }                   |

# HU-03 — Generación de texto con RAG

### Diagramas

- Diagrama de flujo — Generación de texto RAG

> *Diagrama pendiente de actualización — ver carpeta `docs/diagrams/`*

- Diagrama de secuencia — Cliente → FastAPI → Qdrant → LLM

> *Diagrama pendiente de actualización — ver carpeta `docs/diagrams/`*

### Criterios de aceptación (MVP ajustado)

- Si no hay documentos en la colección → `HTTP 422`
- La búsqueda se limita a la colección (`collection_id`)
- Retorna texto generado con contexto relevante
- (Opcional futuro) incluye sources

### Secuencia corregida

| **Paso** | **Actor → Actor** | **Mensaje / Operación**              |
| -------- | ----------------- | ------------------------------------ |
| 1        | Cliente → FastAPI | POST /collections/{id}/generate/text |
| 2        | FastAPI → Qdrant  | search(filter=collection_id)         |
| 3        | Qdrant → FastAPI  | chunks relevantes                    |
| 4        | FastAPI           | Construye prompt                     |
| 5        | FastAPI → LLM     | Genera respuesta                     |
| 6        | FastAPI → Cliente | HTTP 200 { response }                |

# HU-04 — Generación de imágenes

### Diagramas

- Diagrama de flujo — Generación de imágenes

> *Diagrama pendiente de actualización — ver carpeta `docs/diagrams/`*

- Diagrama de secuencia — Cliente → FastAPI → ComfyUI / RunPod

> *Diagrama pendiente de actualización — ver carpeta `docs/diagrams/`*

### Criterios de aceptación (ajustados)

- La imagen se genera a partir de:
  - descripción del usuario
  - contexto RAG (colección)
  - (opcional) entidad
- Se retorna URL + metadata (prompt, seed)
- Timeout → `HTTP 503`

### Secuencia corregida

| **Paso** | **Actor → Actor**        | **Mensaje / Operación**               |
| -------- | ------------------------ | ------------------------------------- |
| 1        | Cliente → FastAPI        | POST /collections/{id}/generate/image |
| 2        | FastAPI → RAG            | Obtener contexto                      |
| 3        | FastAPI                  | Construir prompt                      |
| 4        | FastAPI → ComfyUI/RunPod | Generar imagen                        |
| 5        | ComfyUI → FastAPI        | image_bytes                           |
| 6        | FastAPI → Storage        | Guardar imagen                        |
| 7        | FastAPI → Cliente        | HTTP 200 { image_url }                |

# HU-05 — Gestión de entidades

### Diagramas

- Diagrama de flujo — CRUD de entidades

> *Diagrama pendiente de actualización — ver carpeta `docs/diagrams/`*

- Diagrama de secuencia — Cliente → FastAPI → DB

> *Diagrama pendiente de actualización — ver carpeta `docs/diagrams/`*

### Criterios de aceptación

- CRUD completo: character, creature, location, faction, item
- Soft delete (`deleted_at`)
- Nombre único por colección (validado en capa de servicio)
- Relación entre entidades (`entity_relations`) — planificada
- Cada entidad puede tener múltiples imágenes — planificado

# HU-06 — Contenidos RAG por categoría para entidades

### Diagramas

- Diagrama de flujo — Generación de contenido RAG por categoría

> *Diagrama pendiente de generación — ver carpeta `docs/diagrams/`*

- Diagrama de secuencia — Cliente → FastAPI → Qdrant → LLM → DB

> *Diagrama pendiente de generación — ver carpeta `docs/diagrams/`*

### Criterios de aceptación

- Se genera un contenido invocando el pipeline RAG con una `category` y un `query` libre del usuario
- La `category` debe ser válida para el tipo de entidad (`domain/category_rules.py`); de lo contrario `HTTP 422`
- Máximo 5 contenidos `pending` por entidad **y por categoría** (`HTTP 422` si se supera)
- El usuario puede editar el contenido antes de confirmar (pending o confirmed)
- **Confirmar** un contenido: descarta automáticamente los demás `pending` **de la misma categoría** (no afecta otras categorías)
- **Descartar** un contenido (PATCH): cambia `status → discarded` sin eliminar el registro
- Los contenidos `discarded` no pueden editarse via API
- Soft-delete independiente del estado (DELETE endpoint → `is_deleted=True`, `HTTP 204`)
- Cada generación registra un `GeneratedText` inmutable (log de la llamada RAG) y un `EntityContent` (contenido editable)

### Secuencia — Generar contenido

| **Paso** | **Actor → Actor**  | **Mensaje / Operación**                                                  |
| -------- | ------------------ | ------------------------------------------------------------------------ |
| 1        | Cliente → FastAPI  | POST /collections/{id}/entities/{eid}/generate/{category}                |
| 2        | FastAPI            | Valida categoría para el tipo de entidad                                 |
| 3        | FastAPI            | Verifica límite de 5 pending por categoría                               |
| 4        | FastAPI → Qdrant   | search(filter=collection_id, top_k=4)                                    |
| 5        | Qdrant → FastAPI   | chunks relevantes                                                        |
| 6        | FastAPI            | Construye prompt con query + contexto + descripción actual de la entidad |
| 7        | FastAPI → Ollama   | Genera texto (llama3.2:latest)                                           |
| 8        | FastAPI → DB       | Guarda GeneratedText (log inmutable) + EntityContent (status=pending)    |
| 9        | FastAPI → Cliente  | HTTP 201 { content_id, content, category, status, sources_count }        |

### Secuencia — Confirmar contenido

| **Paso** | **Actor → Actor** | **Mensaje / Operación**                                             |
| -------- | ----------------- | ------------------------------------------------------------------- |
| 1        | Cliente → FastAPI | POST /collections/{id}/entities/{eid}/contents/{cid}/confirm        |
| 2        | FastAPI → DB      | EntityContent.status = confirmed, confirmed_at = now()              |
| 3        | FastAPI → DB      | Otros pending de la misma categoría → status = discarded            |
| 4        | FastAPI → Cliente | HTTP 200 { entity }                                                 |

# 4. Arquitectura Técnica

La arquitectura se divide en dos configuraciones que comparten el mismo codebase: ejecución local para desarrollo y prototipado, y ejecución en nube usando RunPod como proveedor de GPU bajo demanda. La diferencia clave es únicamente la capa de inferencia de imágenes.

## Stack tecnológico completo

| **Tecnología**                | **Capa**                   | **Justificación**                                                                         |
| ----------------------------- | -------------------------- | ----------------------------------------------------------------------------------------- |
| **FastAPI + Uvicorn**         | Backend / API REST         | Framework async de alto rendimiento. Soporta SSE para streaming. Swagger UI incluido.     |
| **Pydantic v2**               | Validación de datos        | Modelos tipados para request/response. Valida el JSONB de attributes por tipo de entidad. |
| **LangChain**                 | Pipeline RAG               | Orquestación completa: carga → chunking → embeddings → retrieval → prompt building.       |
| **sentence-transformers**     | Embeddings locales         | Modelo `paraphrase-multilingual-MiniLM-L12-v2`, 384-d. Sin APIs externas. Vectoriza el lore del usuario.         |
| **Qdrant**                    | Base de datos vectorial    | Servidor Docker con persistencia en disco. Filtros por metadatos. Escalable a cloud.      |
| **Ollama**                    | LLM local (dev/proto)      | Sirve Llama 3.2, Mistral, Qwen2 localmente. Acceso directo a GPU del host.                |
| **ComfyUI**                   | Motor de difusión          | API HTTP/WebSocket para generación de imágenes. Acepta workflows JSON.                    |
| **Flux.2 Klein 4B Distilled** | Modelo de imagen           | FP8, 4 pasos, cfg=1.0. ~8.4 GB VRAM. Apache 2.0. Texto+edición unificados.                |
| **Redis**                     | Caché semántico            | Cachea respuestas del LLM por similitud coseno ≥ 0.95. TTL configurable.                  |
| **S3 / Cloudflare R2**        | Almacenamiento de imágenes | LocalStack en dev. S3 real o R2 (más barato) en producción.                               |
| **PostgreSQL**                | Base de datos relacional   | Metadatos de documentos, entidades e imágenes. SQLite en prototipo.                       |
| **Prometheus + Grafana**      | Observabilidad             | Métricas de latencia p95, tasa de error, cola de imágenes, uso VRAM.                      |
| **Docker Compose**            | Contenerización local      | Levanta todos los servicios de soporte con un solo comando.                               |
| **RunPod Serverless**         | GPU cloud bajo demanda     | RTX 4090 o A100. Pago por segundo de cómputo. Sin servidor GPU 24/7.                      |

## Diagrama de arquitectura general

> *Diagrama pendiente de actualización — ver carpeta `docs/diagrams/`*

**Diagrama de Arquitectura — Vista General Local y Cloud**

# 5. Estructura del Proyecto

## 5.1 Ejecución local (ComfyUI en el host)

En modo local, ComfyUI y Ollama corren en el host para acceder directamente a la GPU. El resto de servicios de soporte (Qdrant, Redis, Prometheus, Grafana, LocalStack) corren en Docker Compose.

```
loremaster/
├── backend/
│   ├── app/
│   │   ├── main.py                        # FastAPI app, CORS, lifespan, registro de routers
│   │   ├── database.py                    # SQLModel engine + dependencia get_session
│   │   ├── api/routes/
│   │   │   ├── collections.py             # HU-01: CRUD colecciones
│   │   │   ├── documents.py               # HU-02: ingestión PDF/TXT
│   │   │   ├── generate.py                # HU-03: RAG free-form por colección
│   │   │   ├── entities.py                # HU-05: CRUD entidades
│   │   │   └── entity_content.py          # HU-06: contenidos RAG por categoría
│   │   ├── models/                        # SQLModel (tabla ORM) + Pydantic (schemas) co-localizados
│   │   │   ├── collections.py             # Collection, CreateCollectionRequest, CollectionResponse
│   │   │   ├── documents.py               # Document, DocumentStatus (processing|completed|failed)
│   │   │   ├── entities.py                # Entity, EntityType (character|creature|location|faction|item)
│   │   │   ├── enums.py                   # ContentCategory, ContentStatus (enums compartidos)
│   │   │   ├── entity_content.py          # EntityContent + schemas de request/response
│   │   │   ├── generated_text.py          # GeneratedText — log inmutable de cada llamada RAG
│   │   │   └── generate.py                # GenerateTextRequest, GenerateTextResponse
│   │   ├── core/
│   │   │   ├── config.py                  # Pydantic Settings (lee .env)
│   │   │   ├── lifespan.py                # Startup: migraciones Alembic (crítico) + health checks
│   │   │   ├── deps.py                    # Dependencias FastAPI: get_collection_or_404, get_entity_or_404, get_document_or_404
│   │   │   └── common.py                  # Helpers DB: soft_delete, get_active_by_id, list_active_by_collection
│   │   ├── engine/                        # Pipeline IA — LLM + Qdrant + RAG
│   │   │   ├── rag.py                     # Qdrant: ingest_chunks, search_context, delete, ping_qdrant
│   │   │   ├── generate.py                # RAG orchestrator: search → prompt → chain.invoke
│   │   │   ├── llm.py                     # OllamaLLM + LangChain RunnableSequence (singleton)
│   │   │   └── extractor.py               # Extracción de texto PDF/TXT
│   │   ├── domain/                        # Lógica de dominio pura — sin I/O ni DB
│   │   │   ├── category_rules.py          # ENTITY_CATEGORY_MAP, validate_category_for_entity()
│   │   │   └── prompt_templates.py        # _TEMPLATES, get_template(), render_prompt()
│   │   └── services/                      # Lógica de negocio (reciben objetos ORM, no IDs)
│   │       ├── collection_service.py
│   │       ├── deletion_service.py            # cascade_delete_entity / cascade_delete_collection
│   │       ├── documents_service.py           # ingest (async), list, get, delete
│   │       ├── entities_service.py            # CRUD + nombre único por colección
│   │       ├── generation_service.py          # generate(): valida categoría, límite pending, RAG → GeneratedText + EntityContent
│   │       ├── content_management_service.py  # list, edit, confirm (discard category-scoped), discard, soft_delete, cascade
│   │       └── generate_service.py            # RAG free-form (sin session, sólo Qdrant + Ollama)
│   ├── alembic/                           # Migraciones (render_as_batch=True para SQLite)
│   ├── tests/                             # pytest con SQLite in-memory; stubs de engine.rag y LLM
│   ├── Makefile
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx                        # BrowserRouter + rutas principales
│   │   ├── api/                           # Capa de acceso al backend
│   │   │   ├── apiClient.ts               # fetch wrapper: apiFetch<T>, ApiError, ApiAbortError
│   │   │   ├── collections.ts / documents.ts / entities.ts / drafts.ts / generate.ts
│   │   │   └── index.ts                   # Re-exporta todos los módulos de api/
│   │   ├── pages/                         # CollectionsPage, CollectionDetailPage,
│   │   │                                  # EntityDetailPage, GeneratePage
│   │   ├── components/                    # Layout, ConfirmModal, LoadingSpinner,
│   │   │                                  # MarkdownContent, TokenCounter
│   │   ├── hooks/useGenerate.ts           # Hook para peticiones LLM cancelables con AbortSignal
│   │   ├── types/                         # Tipos TypeScript (espejo exacto de schemas del backend)
│   │   └── utils/                         # enums.ts, constants.ts, errors.ts (mensajes en español),
│   │                                      # formatters.ts, tokens.ts
│   └── package.json
│
├── docker-compose.yml
│   # Servicios: Qdrant · PostgreSQL · Redis · LocalStack · Prometheus · Grafana
│
├── monitoring/
│   ├── prometheus.yml
│   └── grafana/
│       └── dashboards/loremaster.json
│
├── .env.example
├── start_local.sh           # Levanta Ollama + ComfyUI --lowvram en el host
└── README.md

```

### Variables de entorno

```
PROJECT_NAME="Lore Master API"
ENVIRONMENT="local"

# LLM
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2:latest

# ComfyUI local
COMFY_BACKEND=local
COMFY_URL=http://host.docker.internal:8188
COMFY_WORKFLOW=workflows/flux2_klein_t2i.json
COMFY_TIMEOUT=60

# Qdrant
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=loremaster

# Redis
REDIS_URL=redis://redis:6379/0
CACHE_THRESHOLD=0.95
CACHE_TTL=3600

# Storage (LocalStack S3)
STORAGE_BACKEND=localstack
S3_ENDPOINT_URL=http://localstack:4566
S3_BUCKET=loremaster-images
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_REGION=us-east-1

# Base de datos
DATABASE_URL=sqlite:///./loremaster.db
```

## 5.2 Escalado a nube con RunPod (ComfyUI remoto)

En modo producción, el api_gateway corre en un VPS económico (sin GPU). Las peticiones de imagen se delegan a un worker RunPod Serverless que ejecuta ComfyUI + Flux.2 Klein dentro de un contenedor con GPU de alta gama.

```
loremaster-cloud/
├── api_gateway/               # Mismo codebase que backend/ local
│   ├── app/
│   │   ├── services/
│   │   │   ├── comfy_client.py        # Detecta COMFY_BACKEND=runpod → usa RunPodClient
│   │   │   └── runpod_client.py       # NUEVO: cliente HTTP async para RunPod API
│   │   └── core/config.py             # Lee RUNPOD_API_KEY, RUNPOD_ENDPOINT_ID
│   ├── Dockerfile
│   └── requirements.txt
│
├── runpod_worker/
│   ├── builder/
│   │   └── setup.sh           # Descarga modelos Flux.2 Klein durante el build
│   ├── src/
│   │   └── handler.py         # Puente RunPod SDK ↔ ComfyUI (mismo contenedor)
│   ├── Dockerfile             # Base: NVIDIA CUDA + ComfyUI + RunPod SDK
│   └── requirements.txt       # runpod, torch, httpx
│
├── docker-compose.prod.yml
│   # Servicios: api_gateway · Qdrant · Redis · PostgreSQL · Prometheus · Grafana
│   # SIN LocalStack — usa S3/R2 real
│
├── infra/
│   ├── init_s3.sh             # Crea bucket en S3 real o Cloudflare R2
│   └── deploy_vps.sh          # Script de deploy del api_gateway en VPS
│
├── .env.prod.example
└── README.md
```

### Variables de entorno (.env producción)

```
# .env.prod
ENVIRONMENT=production

# LLM (puede ser Ollama en VPS o RunPod también)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest

# ComfyUI via RunPod Serverless
COMFY_BACKEND=runpod
RUNPOD_API_KEY=rp_xxxxxxxxxxxxxxxxxxxx
RUNPOD_ENDPOINT_ID=xxxxxxxxxxxxxxxxxx
RUNPOD_ENDPOINT_URL=https://api.runpod.ai/v2/${RUNPOD_ENDPOINT_ID}/runsync
COMFY_TIMEOUT=120

# Qdrant (puede ser cloud o self-hosted)
QDRANT_URL=http://qdrant:6333

# Redis
REDIS_URL=redis://redis:6379/0

# Storage (Cloudflare R2 — más barato que S3)
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com
S3_BUCKET=loremaster-prod
AWS_ACCESS_KEY_ID=<r2_access_key>
AWS_SECRET_ACCESS_KEY=<r2_secret_key>
AWS_REGION=auto

# Base de datos
DATABASE_URL=postgresql://user:pass@postgres:5432/loremaster
```

## 5.3 Comparativa Local vs RunPod

| **Aspecto**          | **Local (ComfyUI en host)**     | **Cloud (RunPod Serverless)**          |
| -------------------- | ------------------------------- | -------------------------------------- |
| **GPU requerida**    | ≥ 8 GB VRAM propia              | RTX 4090 (24 GB) o A100 bajo demanda   |
| **Costo**            | $0 (hardware propio)            | ~$0.44-0.74/hr activo; $0 cuando idle  |
| **Cold start**       | Instantáneo                     | 20-60 s para el primer request         |
| **Escalabilidad**    | 1 petición a la vez             | Múltiples workers en paralelo          |
| **Privacidad**       | Total (datos locales)           | Datos salen al proveedor (revisar T&C) |
| **Mantenimiento**    | Alto (actualizaciones manuales) | Bajo (imagen Docker versionada)        |
| **Recomendado para** | Desarrollo, prototipo, demos    | Beta, producción, múltiples usuarios   |

# 6. Esquemas de Datos

## 6.1 Modelo relacional (tablas principales)

| **Tabla** | **Campos principales** | **Notas / Restricciones** |
|---|---|---|
| **collections** | id (UUID PK), name (unique), description, created_at, updated_at, is_deleted, deleted_at | Unidad principal del sistema (world). |
| **documents** | id (UUID PK), collection_id (FK), filename, file_type, chunk_count, status, created_at, is_deleted, deleted_at | Sin campo `content` — el texto vive en Qdrant. Sin `updated_at` — los documentos no se editan. `status`: processing \| completed \| failed. |
| **entities** | id (UUID PK), collection_id (FK), type (ENUM), name, description, created_at, updated_at, is_deleted, deleted_at | `type`: character \| creature \| location \| faction \| item. Nombre único por colección (validado en servicio). |
| **generated_texts** | id (UUID PK), entity_id (FK), collection_id (FK), category, query, raw_content, sources_count, created_at | Log inmutable de cada llamada RAG. No se edita. Referenciado por `entity_content`. |
| **entity_contents** | id (UUID PK), entity_id (FK), collection_id (FK), generated_text_id (FK), category, content, status, created_at, updated_at, is_deleted, deleted_at | `status`: pending \| confirmed \| discarded. Máx. 5 `pending` por entidad **y por categoría**. El discard al confirmar es category-scoped. |
| **generated_images** | id (UUID PK), collection_id (FK), entity_id (FK?), image_url, visual_prompt, seed, model_version, generation_ms, backend, created_at | Planificado (Fase 3). backend: local \| runpod. |
| **entity_relations** | id (UUID PK), source_id (FK entities), target_id (FK entities), relation_type, created_at | Planificado. ENUM: belongs_to, contains, allied_with, enemy_of. |

### Diagrama ERD

> *Diagrama pendiente de generación — ver carpeta `docs/diagrams/`*
>
> Tablas a incluir: collections, documents, entities, generated_texts, entity_contents (+ relaciones planificadas: generated_images, entity_relations)

# 7. Roadmap de Desarrollo — 12 Semanas (Final Ajustado)

Tres fases de 4 semanas. Cada semana cierra con un entregable concreto, verificable y no regresivo. El criterio de paso entre bloques es que el bloque anterior esté estable.

---

## Fase 1 — Fundamentos de RAG (Semanas 1-4)

**Objetivo:** API funcional con RAG básico. Sin imágenes, sin cloud.

| **Semana** | **Hito**               | **Entregables verificables**                                                                                                   |
| ---------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **Sem. 1** | FastAPI skeleton       | Repo Git funcional. Endpoints `/health`, `/generate/text` (mock). Estructura base (routes, services, schemas). Swagger activo. |
| **Sem. 2** | Ingesta + embeddings   | Endpoint `/documents/ingest` guarda TXT/PDF en memoria. Generación de embeddings básicos. Flujo simple: ingestión → consulta.  |
| **Sem. 3** | Vector DB (RAG básico) | Integración con Qdrant. Búsqueda semántica (`top_k`). `/generate/text` usa contexto real.                                      |
| **Sem. 4** | Pipeline RAG completo  | Chunking + embeddings + retrieval + prompt. Integración con LLM local (Ollama). Respuesta con sources.                         |

---

## Fase 2 — RAG avanzado + Imágenes locales (Semanas 5-8)

**Objetivo:** Sistema RAG usable + introducción progresiva de imágenes.

| **Semana** | **Hito**                     | **Entregables verificables**                                                                                                   |
| ---------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **Sem. 5** | RAG intermedio               | Mejora de chunking (overlap) y embeddings. Respuestas más coherentes. Soporte para documentos grandes.                         |
| **Sem. 6** | QA + preparación de imágenes | Sistema QA más preciso. Definición de `prompt_builder`. Endpoint `/generate/image` (mock funcional).                           |
| **Sem. 7** | Imágenes LOCAL (ComfyUI)     | Integración de ComfyUI local. Cliente básico (`comfy_client.py`). `/generate/image` genera imágenes reales desde descripción.  |
| **Sem. 8** | RAG + imágenes integradas    | Construcción de prompt visual usando contexto RAG. Guardado de metadata (prompt + seed). Flujo: documento → contexto → imagen. |

---

## Fase 3 — Producción + RunPod (Semanas 9-12)

**Objetivo:** Preparar sistema real con persistencia, cloud y optimización.

| **Semana**  | **Hito**                        | **Entregables verificables**                                                                                                                    |
| ----------- | ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| **Sem. 9**  | Docker + arquitectura limpia    | Dockerfile + docker-compose funcional. Separación clara (routes, services). Backend estable.                                                    |
| **Sem. 10** | RunPod básico (imágenes)        | Worker en RunPod funcional. Script que envía prompt y recibe imagen. Test manual sin integración completa.                                      |
| **Sem. 11** | Integración RunPod en API       | Implementación de `runpod_client.py`. Switch local/runpod en `/generate/image`. API soporta ambos backends.                                     |
| **Sem. 12** | Cache + evaluación + demo final | Integración de Redis para cache. Evaluación automática básica. Demo completa: ingestión → texto → imagen (local o RunPod). Documentación final. |

# 8. Plan de Gestión de Riesgos

| **Riesgo**                           | **Prob.** | **Impacto** | **Mitigación**                                                                                                                                                                                                |
| ------------------------------------ | --------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **VRAM insuficiente en local**       | Media     | Alto        | Flux.2 Klein 4B Distilled (FP8) necesita ~8.4 GB VRAM. Con 6 GB: usar variante GGUF Q4 (unsloth/FLUX.2-klein-4B-GGUF). Con < 6 GB: usar RunPod directamente desde la fase 1.                                  |
| **cfg ≠ 1.0 en modelo Distilled**    | Baja      | Crítico     | cfg > 1.0 con el modelo Distilled produce imágenes negras o completamente degradadas. Solución: hardcodear cfg=1.0 en el workflow JSON y añadir assert en comfy_client.py.                                    |
| **Cold start RunPod (20-60 s)**      | Alta      | Medio       | Workers GPU tardan al arrancar tras un período idle. Implementar cola con BackgroundTasks, mostrar progreso al usuario. Mantener 1 worker ‘caliente’ en horas pico (~$0.74/hr extra).                         |
| **Calidad RAG baja**                 | Media     | Alto        | Chunks mal dimensionados recuperan contexto irrelevante. Inicio con chunk_size=512, overlap=50. Evaluar con RAGAS tras sem. 2. Ajustar score_threshold e implementar filtros por tipo de entidad.             |
| **Coherencia visual entre sesiones** | Alta      | Medio       | Sin seed fijo, el mismo personaje puede variar radicalmente. Guardar seed + visual_prompt exacto por imagen. Reutilizar seed al regenerar. Futuro: LoRA de personaje.                                         |
| **Costos RunPod desbocados**         | Media     | Medio       | Sin control, múltiples workers activos pueden acumular costos altos. Configurar límite de presupuesto en RunPod. Usar runsync (síncrono) solo durante el prototipo; implementar cola asíncrona en producción. |

# 9. Monitoreo y Gestión de Costos

## 9.1 Métricas de monitoreo (Prometheus + Grafana)

| **Métrica**                               | **Tipo**  | **Descripción / Umbral de alerta**                                   |
| ----------------------------------------- | --------- | -------------------------------------------------------------------- |
| **loremaster_requests_total**             | Counter   | Peticiones por ruta y código HTTP. Alerta si tasa de 5xx > 2%.       |
| **loremaster_request_duration_seconds**   | Histogram | Latencia de respuesta. Alerta si p95 > 10 s.                         |
| **loremaster_llm_tokens_generated_total** | Counter   | Tokens generados por el LLM. Útil si se migra a LLM de pago.         |
| **loremaster_image_generation_seconds**   | Histogram | Tiempo de generación de imagen. Alerta si p95 > 45 s.                |
| **loremaster_comfy_queue_depth**          | Gauge     | Peticiones en cola hacia ComfyUI. Alerta si > 5 (cuello de botella). |
| **loremaster_cache_hit_ratio**            | Gauge     | Ratio de hits en Redis. Objetivo > 30%. Si < 10%, revisar TTL.       |
| **loremaster_qdrant_search_seconds**      | Histogram | Latencia de búsqueda vectorial. Alerta si p95 > 500 ms.              |
| **loremaster_storage_bytes_total**        | Counter   | Bytes almacenados en S3. Para proyectar costos de almacenamiento.    |

## 9.2 Gestión de costos en la nube

| **Componente**                   | **Estimación de costo**                       | **Optimización recomendada**                                                                 |
| -------------------------------- | --------------------------------------------- | -------------------------------------------------------------------------------------------- |
| **RunPod RTX 4090 (Serverless)** | ~$0.44-0.74/hr activo. $0 cuando idle.        | min_workers=0 por defecto. Subir a 1 solo en horarios de prueba o producción alta.           |
| **VPS para api_gateway**         | €4-8/mes (Hetzner CX22 o similar). Sin GPU.   | 2 vCPU, 4 GB RAM es suficiente para el api_gateway. No necesita GPU.                         |
| **Cloudflare R2 (imágenes)**     | $0.015/GB almacenado. Egress gratuito.        | Más barato que S3 para almacenar y servir imágenes públicas. Sin egress fees.                |
| **Qdrant Cloud (opcional)**      | Tier gratuito: 1 GB RAM. Paid desde ~$25/mes. | En prototipo: self-hosted en el VPS. Migrar a cloud cuando la colección supere 1 M vectores. |
| **PostgreSQL**                   | ~€0 en el VPS o ~$7/mes managed.              | Self-hosted en el VPS en MVP. Managed (Railway, Supabase) cuando haya > 1 usuario.           |

## 9.3 Estrategia de caché para reducir costos de LLM

- Redis semántico con umbral coseno ≥ 0.95: consultas similares reutilizan la misma respuesta sin llamar al LLM.
- TTL de caché ajustable: 3600 s por defecto. Reducir para documentos que cambien frecuentemente.
- Las imágenes generadas se guardan en S3: el usuario puede reutilizar una imagen sin regenerarla.
- El seed fijo permite reproducir la misma imagen sin consumir GPU adicional.

# 10. Guardrails de Imágenes

El sistema implementa tres capas de control para garantizar la calidad, coherencia y seguridad de las imágenes generadas.

## Capa 1 — Construcción estructurada del prompt visual

```python
# backend/app/services/prompt_builder.py

STYLE_PREFIX = {
    "character": "fantasy character portrait, detailed face, cinematic lighting, epic atmosphere,",
    "scene":     "fantasy landscape, wide establishing shot, atmospheric, detailed environment,",
    "faction":   "faction emblem, heraldic design, fantasy art, symbolic imagery,",
    "item":      "fantasy item showcase, clean background, detailed textures, magical aura,"
}

QUALITY_SUFFIX = (
    "high quality, masterpiece, 8k resolution, sharp focus, "
    "professional digital art, trending on artstation"
)

def build_visual_prompt(entity_type: str, user_description: str, lore_context: str) -> str:
    prefix   = STYLE_PREFIX.get(entity_type, '')
    combined = f'{prefix} {user_description}'
    if lore_context:
        combined += f', consistent with: {lore_context[:200]}'  # Limitar contexto RAG
    full = f'{combined}, {QUALITY_SUFFIX}'
    return full[:500]  # Flux.2 Klein acepta hasta ~512 tokens de texto
```

## Capa 2 — Filtrado de contenido en el prompt

```python
# backend/app/services/prompt_builder.py

BLOCKED_KEYWORDS = [
    # Lista de términos que activan rechazo antes de enviar a ComfyUI
    # Completar según política del proyecto
]

def validate_prompt(prompt: str) -> tuple[bool, str | None]:
    lower = prompt.lower()
    for kw in BLOCKED_KEYWORDS:
        if kw in lower:
            return False, f'El prompt contiene contenido no permitido: "{kw}"'
    if len(prompt.strip()) < 10:
        return False, 'El prompt es demasiado corto para generar una imagen útil.'
    return True, None

# En el endpoint /generate/image:
# valid, reason = validate_prompt(visual_prompt)
# if not valid: raise HTTPException(422, detail=reason)
```

## Capa 3 — Negative prompt y parámetros fijos en el workflow

| **Parámetro**       | **Valor fijo**                                                      | **Motivo**                                                                            |
| ------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| **steps**           | 4                                                                   | Modelo Distilled optimizado para 4 pasos. Más pasos no mejoran la calidad.            |
| **cfg**             | 1.0                                                                 | CRÍTICO: cfg > 1.0 produce imágenes completamente degradadas con el modelo Distilled. |
| **sampler**         | euler                                                               | Sampler compatible con el scheduler del modelo Distilled.                             |
| **scheduler**       | simple                                                              | Requerido por el modelo Flux.2 Klein Distilled.                                       |
| **width × height**  | 1024 × 1024 px                                                      | Resolución óptima para el modelo; otras resoluciones pueden producir artefactos.      |
| **negative_prompt** | blurry, ugly, deformed, watermark, text, extra limbs, worst quality | Filtro base para mejorar consistencia y evitar artefactos comunes.                    |

## Registro y trazabilidad de imágenes

Cada imagen generada se registra en la tabla generated_images con:

- visual_prompt exacto usado (para auditoría y reproducibilidad).
- seed utilizado (para regenerar la misma imagen si el usuario lo solicita).
- model_version (para detectar regresiones al actualizar el modelo).
- generation_ms (para monitorear rendimiento en el tiempo).
- backend: ‘local’ o ‘runpod’ (para comparar tiempos entre configuraciones).
