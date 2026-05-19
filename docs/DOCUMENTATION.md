# 1. Resumen Ejecutivo

> ⚠️ **NOTA SOBRE DIAGRAMAS** — Pendiente de recrear (2026-05-15):
> - **ERD**: no incluye `users`, `image_generations`, `image_records`, `generated_texts`, `moderation_log`; faltan campos `is_shared`, `owner_id`, `token_version`, `avatar_path`, `display_name`, `bio`.
> - **HU-01** (flujo y secuencia): omiten auth (`get_current_user`) y asignación de `owner_id`.
> - **HU-04** (flujo y secuencia): no refleja flujo de dos pasos `build-prompt → generate`.
> - **HU-06** (compartir contenido): no existe diagrama para el endpoint `PATCH .../share`.
> - **Arquitectura general**: no refleja multi-tenancy, rutas públicas, ni integración Clerk (modo dual local / Clerk).
> - **Flujo de autenticación (NUEVO)**: diagrama pendiente para los dos modos — modo local (formulario → JWT local → cookie) y modo Clerk (Clerk JWT → `/auth/clerk/sync` → JWT local → cookie).
> **→ Los diagramas necesitan ser recreados para reflejar el estado actual.**

## ¿Qué es Lore Master?

Lore Master es una plataforma web interactiva para escritores, narradores de rol (RPG), diseñadores de videojuegos y creadores de contenido que necesitan construir, organizar y expandir mundos ficticios de manera coherente y visualmente rica.

A diferencia de los asistentes de IA genéricos basados en chat, Lore Master ofrece un flujo de trabajo estructurado donde el usuario carga documentos de referencia (PDF o TXT) con el lore de su mundo y el sistema genera texto enriquecido e imágenes coherentes con ese contexto, usando una arquitectura RAG (Retrieval-Augmented Generation).

## ¿Qué hace?

**Implementado actualmente:**

- Ingesta y vectoriza documentos de lore (PDF/TXT) proporcionados por el usuario.
- Recupera contexto relevante del lore antes de cada generación de texto.
- Genera texto narrativo expandido, consistente con el lore cargado.
- Genera **contenidos RAG por categoría** para cada entidad: el usuario puede editar, confirmar (descarta automáticamente los demás pendientes de la misma categoría, sin afectar confirmados previos) o descartar cada contenido.
- Gestiona entidades del mundo (personajes, criaturas, escenarios, facciones, ítems) con atributos estructurados.
- Aplica moderación de contenido en tres capas (input, documentos y output del LLM) mediante filtros regex (`domain/content_guard.py`).
- **Sistema multi-tenant**: cada colección pertenece a un usuario (`owner_id`); otros usuarios no pueden acceder a colecciones, contenidos ni imágenes ajenas.
- **Generación de imágenes** (flujo de dos pasos):
  1. `build-prompt`: Genera `auto_prompt` (prompt visual LLM) a partir de un contenido confirmado de la entidad.
  2. `generate`: Genera imágenes usando el `auto_prompt` del frontend + `final_prompt` del usuario.
- **Compartir contenido**: textos (`is_shared`) e imágenes (`is_shared`) se pueden publicar selectivamente en el feed público (`/public/feed`, `/public/images`) y en perfiles de usuario (`/users/{username}/profile`).
- **Perfiles de usuario**: display_name, bio, avatar (upload/delete). Perfil público accesible sin autenticación.
- **Panel de administración**: listar usuarios, eliminar colecciones y usuarios (cascade atómico).
- Módulo consolidado `engine/image_prompt_builder.py`. Límite de 512 tokens para prompts visuales.

**Parcialmente implementado:**

- Almacenamiento S3 — staging (docker-compose incluye LocalStack).
- Integración con RunPod Serverless para generación de imágenes en la nube — pendiente. Backend local ComfyUI implementado y funcional.

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

| **Numero**   | **Objetivo**                               | **Entregable verificable**                                                        | **Fase** |
| ------- | ------------------------------------------ | --------------------------------------------------------------------------------- | -------- |
| **O-1** | Implementar el pipeline RAG completo       | Endpoint /query retorna texto fundamentado en el lore con `answer`, `query` y `sources_count` | Fase 1   |
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
- Multi-tenancy implementado: cada colección pertenece a un usuario (`owner_id`). Un usuario solo ve y edita sus propias colecciones. El contenido individual se puede compartir públicamente de forma selectiva.

# 3. Características e Historias de Usuario

Las historias cubren el ciclo completo del creador de mundos, utilizando **collections como unidad principal del sistema**.

## Tabla de historias

| **Identificador**    | **Historia**              | **Enunciado completo**                                                                                                                                 |
| --------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **HU-01** | Crear colección           | Como creador de mundos, quiero crear una colección (world) para organizar documentos, entidades e imágenes dentro de un mismo contexto narrativo.      |
| **HU-02** | Ingestión de documentos   | Como creador de mundos, quiero subir archivos PDF o TXT a una colección para que el sistema los procese y los use como base para futuras generaciones. |
| **HU-03** | Generación de texto (RAG) | Como creador de mundos, quiero hacer consultas sobre una colección para obtener texto coherente basado en el lore cargado.                             |
| **HU-04** | Generación de imágenes    | Como creador de mundos, quiero generar imágenes consistentes con mi lore utilizando contexto de la colección.                                          |
| **HU-05** | Gestión de entidades      | Como creador de mundos, quiero gestionar personajes, escenarios y objetos dentro de una colección para estructurar mi mundo.                           |
| **HU-06** | Contenidos RAG por categoría | Como creador de mundos, quiero generar contenidos RAG por categoría para una entidad y confirmar el mejor, descartando automáticamente los demás pendientes de esa categoría sin afectar confirmados previos.   |

### Diagramas

- Diagrama de flujo RAG
  
![Diagrama de flujo RAG](./diagrams/Diagrama-Flujo-RAG.png)

- Diagrama de secuencia RAG

![Diagrama de secuencia RAG](./diagrams/Diagrama-Secuencia-RAG.png)

---

# HU-01 — Crear colección

### Diagramas

- Diagrama de flujo — Creación de colección

> ⚠️ **Desactualizado (2026-05-07):** el flujo no refleja la dependencia de autenticación (`get_current_user`) ni la asignación de `owner_id` al crear la colección. Necesita recrearse.

![Diagrama de flujo HU-01](./diagrams/Diagrama-Flujo-HU-01.png)

- Diagrama de secuencia — Cliente → FastAPI → DB

> ⚠️ **Desactualizado (2026-05-07):** la secuencia omite el paso de validación JWT y la escritura de `owner_id` en la colección. Necesita recrearse.

![Diagrama de secuencia HU-01](./diagrams/Diagrama-Secuencia-HU-01.png)

### Criterios de aceptación

- Permite crear una colección con nombre y descripción
- Retorna `collection_id`
- Permite listar colecciones existentes
- Cada colección es independiente

# HU-02 — Ingestión de documentos

### Diagramas

- Diagrama de flujo — Ingestión de documentos

![Diagrama de flujo HU-02](./diagrams/Diagrama-Flujo-HU-02.png)

- Diagrama de secuencia — Cliente → FastAPI → Qdrant

![Diagrama de secuencia HU-02](./diagrams/Diagrama-Secuencia-HU-02.png)

### Criterios de aceptación (corregidos)

- Acepta PDF (`application/pdf`) y TXT (`text/plain`) hasta 50 MB
- Rechaza formatos inválidos con `HTTP 400`
- Rechaza archivos sin nombre o con nombre > 255 caracteres con `HTTP 422` (límite de `VARCHAR(255)` en PostgreSQL)
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

![Diagrama de flujo HU-03](./diagrams/Diagrama-Flujo-HU-03.png)

- Diagrama de secuencia — Cliente → FastAPI → Qdrant → LLM

![Diagrama de secuencia HU-03](./diagrams/Diagrama-Secuencia-HU-03.png)

### Criterios de aceptación (MVP ajustado)

- Si no hay documentos en la colección → `HTTP 422`
- La búsqueda se limita a la colección (`collection_id`)
- Retorna texto generado con contexto relevante
- (Opcional futuro) incluye sources

### Secuencia corregida

| **Paso** | **Actor → Actor** | **Mensaje / Operación**                          |
| -------- | ----------------- | ------------------------------------------------ |
| 1        | Cliente → FastAPI | POST /collections/{id}/query                     |
| 2        | FastAPI → Qdrant  | search_context(collection_id, top_k)             |
| 3        | Qdrant → FastAPI  | chunks relevantes                                |
| 4        | FastAPI           | Construye prompt                                 |
| 5        | FastAPI → LLM     | chain.invoke({ context, query })                 |
| 6        | FastAPI → Cliente | HTTP 200 { answer, query, sources_count }        |

# HU-04 — Generación de imágenes

> ⚠️ **NOTA**: Los diagramas de flujo y secuencia para esta historia necesitan actualización para reflejar el nuevo flujo de dos pasos (build-prompt → generate).

### Nuevo flujo (implementado)

1. **build-prompt** → `POST .../image-generation/build-prompt`: Genera el `auto_prompt` (prompt visual LLM) a partir de un contenido confirmado de la entidad.
2. **generate** → `POST .../image-generation/generate`: Genera imágenes usando el `auto_prompt` del frontend + `final_prompt` del usuario. No hay regeneración del prompt en backend.

**Endpoints:**

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/collections/{id}/entities/{eid}/image-generation/build-prompt` | Construye el prompt visual (`auto_prompt`) |
| `POST` | `/collections/{id}/entities/{eid}/image-generation/generate` | Genera batch de imágenes (1-4) |
| `GET` | `/collections/{id}/entities/{eid}/image-generation` | Lista generaciones |
| `GET` | `/collections/{id}/entities/{eid}/image-generation/{gid}` | Obtiene una generación |
| `DELETE` | `/collections/{id}/entities/{eid}/image-generation/{gid}/images/{iid}` | Elimina una imagen |

**Request (generate):** `{ content_id, auto_prompt, final_prompt, batch_size }`

### Criterios de aceptación (actualizados)

- `auto_prompt` viene del frontend (previamente generado en `build-prompt`)
- `auto_prompt` validado en schema: `min_length=1`, `max_length=2000`
- `final_prompt` es editable por el usuario (`min_length=10`, `max_length=2000`)
- `batch_size` entre 1 y 4
- Validación de contenido con `check_user_input()` antes de generar
- Límite de 512 tokens (`IMAGE_PROMPT_TOKENS`) para el prompt visual; buffer interno garantiza que el resultado ≤ 2 000 chars (límite DB)

### Secuencia (actualizada)

| **Paso** | **Actor → Actor**    | **Mensaje / Operación**                                              |
| -------- | --------------------- | ------------------------------------------------------------------- |
| 1        | Cliente → FastAPI    | POST /image-generation/build-prompt con content_id                  |
| 2        | FastAPI → DB         | Carga EntityContent confirmado (texto del contenido)                |
| 3        | FastAPI → LLM        | build_combined_prompt() → extrae tipo y atributos visuales          |
| 4        | FastAPI → Cliente    | HTTP 200 { auto_prompt }                                            |
| 5        | Cliente → FastAPI    | POST /image-generation/generate (auto_prompt + final_prompt)        |
| 6        | FastAPI              | Valida input con check_user_input()                                 |
| 7        | FastAPI → DB         | Guarda ImageGeneration con auto_prompt, final_prompt, batch_size   |
| 8        | FastAPI → ComfyUI    | Genera imágenes via ComfyUI local o RunPod Serverless              |
| 9        | FastAPI → Cliente    | HTTP 201 { generation_id, images }                                  |

### Integración con ComfyUI + Flux.2 Klein 4B

La generación de imágenes usa:
- **ComfyUI local** (implementado) — cliente en `engine/comfyui_client.py`, backend puro en `services/image/_backends.py`
- **Modelo Flux.2 Klein 4B Distilled** (FP8, ~8.4 GB VRAM) via workflow JSON `flux2-klein-4b-api.json`
- **RunPod Serverless** — pendiente; requiere `runpod_client.py` y cambio de `IMAGE_BACKEND=runpod`

El flujo de dos pasos (`build-prompt → generate`) y el módulo de prompts visuales (`image_prompt_builder.py`) están implementados. El switch `IMAGE_BACKEND=mock|comfyui` permite desarrollo sin GPU.

# HU-05 — Gestión de entidades

### Diagramas

- Diagrama de flujo — CRUD de entidades

![Diagrama de flujo HU-05](./diagrams/Diagrama-Flujo-HU-05.png)

- Diagrama de secuencia — Cliente → FastAPI → DB

![Diagrama de secuencia HU-05](./diagrams/Diagrama-Secuencia-HU-05.png)

### Criterios de aceptación

- CRUD completo: character, creature, location, faction, item
- Soft delete (`deleted_at`)
- Nombre único por colección, validado en capa de servicio y reforzado por constraint DB (`uq_entity_collection_name`). Los nombres de entidades eliminadas quedan reservados en esa colección.
- Relación entre entidades (`entity_relations`) — planificada
- Cada entidad puede tener múltiples imágenes — planificado

# HU-06 — Contenidos RAG por categoría para entidades

### Diagramas

- Diagrama de flujo — Generación de contenido RAG por categoría

![Diagrama de flujo HU-06](./diagrams/Diagrama-Flujo-HU-06.png)

- Diagrama de secuencia (generación) — Cliente → FastAPI → Qdrant → LLM → DB

![Diagrama de secuencia HU-06](./diagrams/Diagrama-Secuencia-HU-06-(Generacion).png)

- Diagrama de secuencia (confirmación) — Cliente → FastAPI → DB

![Diagrama de secuencia HU-06](./diagrams/Diagrama-Secuencia-HU-06-(Confirmar).png)


### Criterios de aceptación

- Se genera un contenido invocando el pipeline RAG con una `category` y un `query` libre del usuario
- Cada categoría usa un prompt específico que incluye `entity_name` y `entity_type` (`domain/prompt_templates.py` → `invoke_generation_pipeline()`)
- La `category` debe ser válida para el tipo de entidad (`domain/category_rules.py`); de lo contrario `HTTP 422`
- Máximo 5 contenidos `pending` por entidad **y por categoría** (`HTTP 422` si se supera)
- El usuario puede editar el contenido antes de confirmar (pending o confirmed)
- **Confirmar** un contenido: descarta automáticamente los demás `pending` **de la misma categoría** (no afecta otras categorías)
- **Descartar** un contenido (PATCH): cambia `status → discarded` sin eliminar el registro
- Los contenidos `discarded` no pueden editarse via API
- Soft-delete independiente del estado (DELETE endpoint → `is_deleted=True`, `HTTP 204`)
- El listado de contenidos (`GET /contents`) está paginado (`PaginatedResponse` con `data`, `meta.total`, `meta.page`, `meta.page_size`, `meta.total_pages`)

### Secuencia — Generar contenido

| **Paso** | **Actor → Actor**  | **Mensaje / Operación**                                                                        |
| -------- | ------------------ | ---------------------------------------------------------------------------------------------- |
| 1        | Cliente → FastAPI  | POST /collections/{id}/entities/{eid}/generate/{category}                                      |
| 2        | FastAPI            | Valida categoría para el tipo de entidad (`domain/category_rules.py`)                          |
| 3        | FastAPI            | Verifica límite de 5 pending por categoría                                                     |
| 4        | FastAPI → Qdrant   | search_context(collection_id, top_k=4)                                                         |
| 5        | Qdrant → FastAPI   | chunks relevantes                                                                              |
| 6        | FastAPI            | `render_prompt(category, entity_name, entity_type, context, query)` → prompt string completo   |
| 7        | FastAPI → Ollama   | `generation_chain.invoke(rendered_prompt)` (semáforo: max 1 llamada concurrente)               |
| 8        | FastAPI → DB       | Guarda EntityContent (status=pending) con query y sources_count                                |
| 9        | FastAPI → Cliente  | HTTP 201 { content_id, content, category, status, sources_count }                              |

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
| **Redis**                     | Rate limiting              | Sliding window para `RateLimitMiddleware`. La caché semántica planificada no está implementada. |
| **S3 / Cloudflare R2**        | Almacenamiento de imágenes | LocalStack en dev. S3 real o R2 (más barato) en producción.                               |
| **PostgreSQL**                | Base de datos relacional   | Metadatos de documentos, entidades e imágenes. SQLite en prototipo.                       |
| **Prometheus + Grafana**      | Observabilidad             | Métricas de latencia p95, tasa de error, cola de imágenes, uso VRAM.                      |
| **Docker Compose**            | Contenerización local      | Levanta todos los servicios de soporte con un solo comando.                               |
| **RunPod Serverless**         | GPU cloud bajo demanda     | RTX 4090 o A100. Pago por segundo de cómputo. Sin servidor GPU 24/7.                      |

## Diagrama de arquitectura general

![Diagrama arquitectura general](./diagrams/Diagrama-Arquitectura-General.png)

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
│   │   │   ├── auth/                      # auth.py: registro/login/logout JWT local; auth_clerk.py: POST /sync (Clerk JWT → cookie local), GET /verify
│   │   │   ├── collections/                # HU-01: CRUD colecciones (solo owner) + HU-03: consulta RAG libre por colección
│   │   │   ├── documents/                 # HU-02: ingestión PDF/TXT
│   │   │   ├── entities/                   # HU-05: CRUD entidades + HU-06: contenidos RAG por categoría
│   │   │   ├── images/                     # Generación de imágenes (build-prompt + generate + share + delete)
│   │   │   ├── public/                     # Feed público e imágenes compartidas
│   │   │   ├── users/                      # Perfil propio, avatar, perfil público
│   │   │   ├── admin.py                    # Admin: listar usuarios, eliminar colección/usuario
│   │   │   └── metadata.py
│   │   ├── models/                        # SQLModel (ORM) + Pydantic (schemas)
│   │   │   ├── enums.py                   # ContentCategory, ContentStatus (enums compartidos)
│   │   │   ├── shared.py                  # PaginatedResponse[T] + PaginationMeta genéricos
│   │   │   ├── db/                        # Modelos SQLModel (tablas ORM)
│   │   │   │   ├── collection.py          # Collection (owner_id FK → users)
│   │   │   │   ├── document.py            # Document, DocumentStatus (processing|completed|failed)
│   │   │   │   ├── entity.py              # Entity, EntityType (character|creature|location|faction|item)
│   │   │   │   ├── entity_content.py      # EntityContent (is_shared)
│   │   │   │   ├── generated_text.py      # GeneratedText: raw_content, query, sources_count, token_count
│   │   │   │   ├── image_generation.py    # ImageGeneration + ImageRecord
│   │   │   │   ├── moderation_log.py      # Registro de rechazos del content guard
│   │   │   │   └── user.py                # User (is_admin, token_version, is_deleted)
│   │   │   └── schemas/                   # Schemas Pydantic (request/response)
│   │   │       ├── collection.py          # CreateCollectionRequest, CollectionResponse
│   │   │       ├── document.py
│   │   │       ├── entity.py
│   │   │       ├── entity_content.py      # EntityContentResponse
│   │   │       ├── image_generation.py
│   │   │       ├── public.py              # Schemas para feed público
│   │   │       ├── rag_query.py           # RagQueryRequest, RagQueryResponse
│   │   │       └── user_schemas.py        # UserProfileResponse, UpdateProfileRequest
│   │   ├── core/                          # Infraestructura y dependencias transversales
│   │   │   ├── __init__.py                # Minimal; evita imports circulares
│   │   │   ├── lifespan.py                # Startup: migraciones Alembic + health checks
│   │   │   ├── auth/                      # JWT, password hashing, CSRF, Clerk
│   │   │   │   ├── dependencies.py        # get_current_user (siempre verify_token → JWT local), get_admin_user
│   │   │   │   └── clerk.py               # JWKSManager (caché TTL 1h), decode_clerk_token() — solo para /sync
│   │   │   ├── config/                    # Pydantic Settings (lee .env)
│   │   │   ├── database/                  # Mixins, utils, soft_delete, dependencies
│   │   │   │   ├── soft_delete.py         # SoftDeleteMixin (UUIDPrimaryKey + TimestampedModel aquí también)
│   │   │   │   ├── utils.py               # pagination helpers
│   │   │   │   └── dependencies.py
│   │   │   ├── api/                       # Query params, filters, schema_mixin
│   │   │   │   ├── params.py              # PaginationParams
│   │   │   │   ├── filters.py
│   │   │   │   └── schema_mixin.py        # FromAttributesMixin
│   │   │   ├── exceptions/                # Custom exception classes
│   │   │   └── storage/                   # File storage and validation
│   │   │       └── validator.py           # FileValidator
│   │   ├── engine/                        # Pipeline IA — LLM + Qdrant + RAG + Imágenes
│   │   │   ├── rag.py                     # Qdrant: ingest_chunks, search_context, delete, ping_qdrant
│   │   │   ├── rag_pipeline.py            # invoke_rag_pipeline() (libre) + invoke_generation_pipeline() (por entidad/categoría)
│   │   │   ├── llm.py                     # OllamaLLM singletons: llm (bare) + chain (PromptTemplate pipeline)
│   │   │   ├── extractor.py               # Extracción de texto PDF/TXT
│   │   │   ├── comfyui_client.py          # Cliente HTTP/WebSocket para ComfyUI local/RunPod
│   │   │   └── image_prompt_builder.py    # Consolidado: build_prompt_from_content + generación visual
│   │   ├── domain/                        # Lógica de dominio pura — sin I/O ni DB
│   │   │   ├── category_rules.py          # ENTITY_CATEGORY_MAP, validate_category_for_entity()
│   │   │   ├── content_guard.py           # Moderación: check_user_input(), check_document_content(), check_generated_output()
│   │   │   ├── image_prompt_rules.py      # Reglas de construcción de prompts visuales
│   │   │   └── prompt_templates.py        # _TEMPLATES, get_template(), render_prompt()
│   │   └── services/                      # Lógica de negocio por dominio (reciben objetos ORM, no IDs)
│   │       ├── collection/                # collection_service + rag_query_service
│   │       │   ├── collection_service.py  # delete_collection_service (wraps cascade + commit)
│   │       │   └── rag_query_service.py   # execute_rag_query(): guard input → pipeline → guard output
│   │       ├── document/                  # documents_service
│   │       │   └── documents_service.py   # ingest, list, get, delete
│   │       ├── entity/                    # entities, content, generation
│   │       │   ├── entities_service.py    # CRUD + nombre único por colección
│   │       │   ├── content_service.py     # list, edit, confirm, discard, share, soft_delete
│   │       │   └── generation_service.py  # generate(): RAG → EntityContent
│   │       ├── image/                     # image_generation_service + backends
│   │       │   ├── image_generation_service.py  # build_prompt, generate_images, share, delete (orquesta DB)
│   │       │   └── _backends.py           # funciones puras: _generate_mock_images, _generate_comfyui_images
│   │       ├── moderation/                # moderation_service
│   │       │   └── moderation_service.py
│   │       ├── profile/                   # profile_service
│   │       │   └── profile_service.py     # upload/delete avatar
│   │       ├── cascade_service.py         # Helpers de cascada
│   │       └── deletion_service.py        # cascade_delete_entity / cascade_delete_collection
│   ├── alembic/                           # Migraciones (render_as_batch=True para SQLite)
│   ├── evaluations/                       # Evaluación end-to-end contra API en ejecución
│   │   ├── baseline_evals.py              # Runner: 81 casos del golden dataset
│   │   └── dataset/
│   │       ├── golden_dataset.json        # Casos: RAG, CRUD, entity_content, guardrail, imagen, feed
│   │       └── golden_seed.txt            # Documento semilla (Mundo de Valdorath)
│   ├── tests/                             # pytest con SQLite in-memory; stubs de engine.rag y LLM (262 tests)
│   ├── Makefile                           # Comandos: run, test, format, lint, install, clean, clean-all. Centraliza pycache en `.pycache/` (PYTHONPYCACHEPREFIX)
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx                        # BrowserRouter + rutas + AuthProvider + ClerkBridge (sync Clerk→backend) + UnauthorizedHandler (401→navigate sin reload)
│   │   ├── api/                           # Capa de acceso al backend
│   │   │   ├── apiClient.ts               # fetch wrapper: apiFetch<T>, ApiError, ApiAbortError
│   │   │   ├── factory.ts                 # Factory pattern para endpoints CRUD reutilizables
│   │   │   ├── auth.ts                    # login() / register() / logoutApi()
│   │   │   ├── clerkSync.ts               # syncClerkSession(clerkToken) — POST /auth/clerk/sync
│   │   │   ├── collections.ts / documents.ts / entities.ts / contents.ts / generate.ts
│   │   │   ├── images.ts                  # buildPrompt, generate, list, get, shareImage, deleteImage
│   │   │   ├── users.ts                   # getMyProfile, updateMyProfile, getPublicProfile, getPublicFeed,
│   │   │   │                              # getPublicImages, getMyAvatar, uploadMyAvatar, deleteMyAvatar
│   │   │   ├── admin.ts                   # Endpoints de administración
│   │   │   ├── metadata.ts                # Metadatos de la API
│   │   │   ├── query.ts                   # buildQuery() — utilidad interna para query strings de URL
│   │   │   └── index.ts                   # Re-exporta todos los módulos de api/ (no incluye query.ts)
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx              # Dual: modo Clerk → <SignIn /> de Clerk; modo local → formulario login/registro con tabs
│   │   │   ├── CollectionsPage.tsx        # Listado, creación y eliminación de colecciones
│   │   │   ├── CollectionDetailPage/      # Tabs: Documentos / Entidades / Generar texto
│   │   │   │   ├── index.tsx
│   │   │   │   ├── DocumentsTab.tsx
│   │   │   │   ├── EntitiesTab.tsx
│   │   │   │   └── GenerateTab.tsx
│   │   │   ├── EntityDetailPage.tsx       # Detalle de entidad + generación de contenido + imágenes
│   │   │   ├── GeneratePage.tsx           # Consulta RAG libre
│   │   │   ├── ProfilePage.tsx            # Edición de perfil propio: display_name, bio, avatar, email
│   │   │   ├── AdminPage.tsx              # Tabla de usuarios con avatar; eliminar usuario/colección
│   │   │   ├── PublicFeedPage.tsx         # Feed global paginado: imágenes + cards de textos
│   │   │   └── PublicProfilePage.tsx      # Perfil público: galería + contenidos; Compartir + ⚙ (solo owner)
│   │   ├── components/
│   │   │   ├── AppNavbar.tsx              # Dropdown: avatar/iniciales, Mi perfil público, Admin, Cerrar sesión
│   │   │   ├── ContentCard.tsx            # Card de EntityContent: acciones por estado, busy-lock, badge ✎ editado
│   │   │   ├── ConfirmModal.tsx           # Modal de confirmación reutilizable
│   │   │   ├── EntityContentsPanel.tsx    # Panel de contenidos de entidad
│   │   │   ├── EntityEditForm.tsx         # Formulario de edición de entidad
│   │   │   ├── FilterBar.tsx              # Barra de filtros reutilizable
│   │   │   ├── ImageGallery.tsx           # Galería de imágenes
│   │   │   ├── ImageGenerator.tsx         # Componente de generación de imágenes
│   │   │   ├── ImagePanel.tsx             # Panel de imágenes de entidad
│   │   │   ├── Layout.tsx                 # AppNavbar + Outlet + StarfieldCanvas
│   │   │   ├── LoadingSpinner.tsx         # Spinner centrado con texto opcional
│   │   │   ├── MarkdownContent.tsx        # Markdown sanitizado (remark-gfm + rehype-sanitize)
│   │   │   ├── PaginationControls.tsx     # Controles de paginación reutilizables
│   │   │   ├── ProtectedRoute.tsx         # Guard dual: modo Clerk usa useUser() (evita race), modo local usa useAuth().user
│   │   │   ├── PublicContentModal.tsx     # Modal de texto compartido (markdown, badges, link al autor)
│   │   │   ├── PublicImageModal.tsx       # Modal de imagen: imagen, seed, prompts, descarga
│   │   │   ├── StarfieldCanvas.tsx        # Fondo canvas: estrellas + fugaces (evento lm:collections)
│   │   │   └── TokenCounter.tsx           # Estimación de tokens (aviso a los 400)
│   │   ├── contexts/
│   │   │   └── AuthContext.tsx            # AuthProvider: verifica sesión via GET /users/me al montar (cookie HttpOnly), auto-logout timer, server logout al cerrar sesión
│   │   ├── hooks/
│   │   │   ├── useAuth.ts                       # Acceso al contexto de autenticación
│   │   │   ├── useApiError.ts                   # Manejo centralizado de errores de API
│   │   │   ├── useCollectionDocumentsStatus.ts  # Polling cada 3s si hay documentos processing
│   │   │   ├── useDebouncedValue.ts             # Debounce configurable (default 300 ms)
│   │   │   ├── useDeleteConfirm.ts              # Confirmación antes de eliminar
│   │   │   ├── useEntityContents.ts             # Fetching/refresco de contenidos de entidad
│   │   │   ├── useFormSubmit.ts                 # Manejo de submits de formulario
│   │   │   ├── useGenerate.ts                   # Peticiones LLM cancelables con AbortSignal
│   │   │   └── usePagination.ts                 # Paginación reutilizable
│   │   ├── test/                          # Tests unitarios (React Testing Library)
│   │   ├── types/                         # Tipos TypeScript (espejo exacto de schemas del backend)
│   │   │   ├── collection.ts / content.ts / document.ts / entity.ts / generate.ts
│   │   │   ├── images.ts / user.ts
│   │   │   └── index.ts
│   │   └── utils/                         # clerkConfig.ts, enums.ts, constants.ts, errors.ts (mensajes en español),
│   │                                      # formatters.ts, strings.ts, tokens.ts
│   └── package.json
│
├── backend/
│   ├── docker-compose.yml           # Base: Qdrant + Redis
│   ├── docker-compose.postgres.yml  # Overlay: PostgreSQL
│   └── docker-compose.prod.yml      # Producción: sin puertos expuestos
├── Makefile                 # Targets: dev, dev-pg, infra, infra-pg, down, prod-up, prod-down
├── dev.ps1                  # Arranque completo local (Windows): Docker infra + espera /health + backend + frontend
├── loremaster.sh            # Arranque completo local (Linux/Mac): Docker infra + espera /health + backend + frontend
└── README.md

```

### Variables de entorno

> ⚠️ **Desactualizado (2026-05-17):** Los nombres de variables han cambiado. Ver [`docs/ENVIRONMENT.md`](./ENVIRONMENT.md) para la referencia completa y actualizada. Diferencias clave:
> - `OLLAMA_URL` → `OLLAMA_BASE_URL`
> - `COMFY_BACKEND` → `IMAGE_BACKEND` (`comfyui` | `mock`)
> - `COMFY_URL` → `COMFYUI_URL`
> - `CACHE_THRESHOLD` / `CACHE_TTL` — Redis se usa para rate limiting (sliding window), no caché semántico
> - `STORAGE_BACKEND=localstack` → `local` (dev) / `s3` / `r2` (prod)
> - Variables añadidas: `RATE_LIMIT_ENABLED`, `RATE_LIMIT_PER_MINUTE`, `RATE_LIMIT_LLM_PER_MINUTE`, `RATE_LIMIT_IMAGE_PER_MINUTE`, `OLLAMA_EXCLUDED_MODELS`

```
PROJECT_NAME="Lore Master API"
ENVIRONMENT="local"

# LLM
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest
OLLAMA_EXCLUDED_MODELS=          # prefijos a ocultar en GET /models (modelos con thinking mode)

# ComfyUI local
IMAGE_BACKEND=comfyui
COMFYUI_URL=http://localhost:8188
COMFYUI_TIMEOUT=300

# Qdrant
QDRANT_URL=http://localhost:6333

# Redis (rate limiting)
REDIS_URL=redis://localhost:6379
RATE_LIMIT_ENABLED=false

# Storage
STORAGE_BACKEND=local

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
| **users** | id (UUID PK), username (unique), hashed_password, email (unique), display_name, bio, avatar_path, is_admin, token_version, created_at, is_deleted, deleted_at | Campos de perfil opcionales. `is_admin` designado vía `scripts/make_admin.py`, nunca por API pública. Un admin soft-deleted no puede autenticarse. `token_version` se incrementa en cada logout para invalidar tokens previos. |
| **collections** | id (UUID PK), name, description, owner_id (FK → users), is_public, created_at, updated_at, is_deleted, deleted_at | `UNIQUE(name, owner_id)`. `owner_id` nullable para datos migrados. `is_public=False` por defecto; el contenido se comparte de forma selectiva a nivel de ítem. |
| **documents** | id (UUID PK), collection_id (FK), filename (VARCHAR 255), file_type, chunk_count, status, created_at, is_deleted, deleted_at | El texto vive en Qdrant, no en esta tabla. `status`: processing \| completed \| failed. `filename` validado en servicio: vacío o > 255 chars → HTTP 422. |
| **entities** | id (UUID PK), collection_id (FK), type (ENUM), name, description, created_at, updated_at, is_deleted, deleted_at | `type`: character \| creature \| location \| faction \| item. Nombre único por colección: `uq_entity_collection_name`. Los nombres de entidades eliminadas quedan reservados. |
| **generated_texts** | id (UUID PK), entity_id (FK), collection_id (FK), category, query, raw_content, sources_count, token_count, model_used (VARCHAR 100, nullable), created_at | Salida bruta del LLM antes de cualquier edición del usuario. `model_used`: nombre del modelo Ollama usado. Vinculada 1:1 con `entity_contents`. Los IDs de documentos fuente se devuelven en `RagQueryResponse.source_doc_ids` pero no se persisten en esta tabla. |
| **entity_contents** | id (UUID PK), entity_id (FK), collection_id (FK), generated_text_id (FK), category, content, status, is_shared, confirmed_at, created_at, updated_at, is_deleted, deleted_at | `status`: pending \| confirmed \| discarded. Máx. 5 `pending` por entidad y por categoría. Confirmar descarta los demás `pending` de esa categoría. `is_shared`: solo `confirmed` puede compartirse. |
| **image_generations** | id (UUID PK), entity_id (FK), collection_id (FK), content_id (FK), category, auto_prompt, final_prompt, prompt_token_count, batch_size, backend, width, height, created_at, is_deleted, deleted_at | Una generación produce N imágenes (batch_size 1-4). `backend`: comfyui \| mock. `category` vincula el contenido base usado para el prompt. |
| **image_records** | id (UUID PK), generation_id (FK), entity_id (FK), collection_id (FK), seed, storage_path, image_url, filename, extension, width, height, generation_ms, is_shared, is_deleted, deleted_at, created_at | Una fila por imagen del batch. `is_shared` controla visibilidad en feed público. `filename` y `extension` identifican el archivo generado. `generation_ms` mide el tiempo de generación. |
| **moderation_log** | id (UUID PK), layer, snippet, created_at | `layer`: input \| document \| output. Registra cada rechazo del guardrail con los primeros 200 chars. |
| **entity_relations** | id (UUID PK), source_id (FK entities), target_id (FK entities), relation_type, created_at | Planificado. ENUM: belongs_to, contains, allied_with, enemy_of. |

### Diagrama ERD

> ⚠️ **Desactualizado:** el diagrama no refleja el estado actual del esquema. Necesita recrearse para incluir las tablas `users`, `generated_texts`, `image_generations`, `image_records`, `moderation_log` y los campos `is_shared`, `owner_id`, `avatar_url`, `is_admin`, `is_deleted`.

![Diagrama ERD](./diagrams/Diagrama-ERD.png)

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
| **Calidad RAG baja**                 | Media     | Alto        | Chunks mal dimensionados recuperan contexto irrelevante. Configuración actual: `chunk_size=400`, `overlap=150` (ajustado desde los valores originales de planificación 512/50). Evaluar con RAGAS. Ajustar `score_threshold` e implementar filtros por tipo de entidad. |
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

> ⚠️ **Desactualizado (2026-05-17):** La caché semántica de Redis descrita aquí **no está implementada**. Redis se usa actualmente exclusivamente para rate limiting (`RateLimitMiddleware` con sliding window). El resto del contenido de esta sección es planificación futura.

- *(Planificado)* Redis semántico con umbral coseno ≥ 0.95: consultas similares reutilizan la misma respuesta sin llamar al LLM.
- *(Planificado)* TTL de caché ajustable: 3600 s por defecto.
- Las imágenes generadas se guardan en storage (local / S3 / R2): el usuario puede reutilizar una imagen sin regenerarla.
- El seed fijo permite reproducir la misma imagen sin consumir GPU adicional.

# 10. Guardrails de Contenido

El sistema implementa control de contenido en el texto y en el pipeline visual (imágenes).

## Capa 1 — Moderación de texto (IMPLEMENTADO)

`backend/app/domain/content_guard.py` aplica cinco grupos de patrones regex en tres puntos del pipeline:

| **Función** | **Punto de aplicación** | **Error si activa** |
| --- | --- | --- |
| `check_user_input(text)` | Antes de llamar al LLM (`generation_service`, `rag_query_service`) | `ContentNotAllowedError` → HTTP 422 |
| `check_document_content(text)` | Tras extraer texto del documento (`documents_service`) | `ContentNotAllowedError` → HTTP 422 |
| `check_generated_output(text)` | Tras recibir la respuesta del LLM | `GeneratedContentBlockedError` → HTTP 422 |

Cada rechazo se persiste en `moderation_log` con `layer` (`input` \| `document` \| `output`) y `snippet` (primeros 200 chars del texto bloqueado).

Patrones bloqueados: contenido sexual explícito, discurso de odio / supremacismo, instrucciones de armas o explosivos, síntesis de drogas, y lenguaje de acoso.

## Capa 2 — Construcción estructurada del prompt visual (IMPLEMENTADO)

Los módulos `backend/app/domain/image_prompt_rules.py` y `backend/app/engine/image_prompt_builder.py` construyen el prompt visual en una sola llamada LLM que extrae el tipo específico y los atributos visuales directamente del texto del contenido confirmado:

- **`image_prompt_rules.py`** — tablas de reglas de extracción:
  - `_COMBINED_TYPE_OPTIONS`: opciones de tipo específico por `EntityType` (p.ej. `"human, alien, robot, android, cyborg…"` para `character`)
  - `_ATTRIBUTOS_BY_ENTITY_CATEGORY`: atributos a extraer según `(EntityType, ContentCategory)` — colores, materiales, texturas, emblemas, postura, etc.
  - `build_combined_prompt()`: construye el prompt de extracción LLM que pide "extract specific type and ALL visual attributes, output as comma-separated list"
- **`image_prompt_builder.py`** — orquesta el flujo:
  1. `build_combined_prompt(entity_type, category, content_text)` → prompt de extracción
  2. LLM devuelve comma-separated: `<tipo>, <atributo1>, <atributo2>, …`
  3. `_truncate_to_tokens(attrs, available_tokens)` acota la lista (disponible: `IMAGE_PROMPT_TOKENS − suffix_tokens − 14` tokens)
  4. `auto_prompt = f"{attributes}, {QUALITY_SUFFIX}"` → prompt final ≤ 1 997 chars

```python
QUALITY_SUFFIX = "high quality, masterpiece, sharp focus, professional digital art"
```

La validación de prompts se realiza con `check_user_input()` antes de cualquier generación.

## Capa 3 — Parámetros fijos del workflow de imágenes (IMPLEMENTADO)

Los parámetros se definen en el workflow JSON `flux2-klein-4b-api.json` cargado por `engine/comfyui_client.py`. `inject_seed` y `inject_prompt` son los únicos puntos de variación por generación.

| **Parámetro**       | **Valor fijo**                                                      | **Motivo**                                                                            |
| ------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| **steps**           | 4                                                                   | Modelo Distilled optimizado para 4 pasos. Más pasos no mejoran la calidad.            |
| **cfg**             | 1.0                                                                 | CRÍTICO: cfg > 1.0 produce imágenes completamente degradadas con el modelo Distilled. |
| **sampler**         | euler                                                               | Sampler compatible con el scheduler del modelo Distilled.                             |
| **scheduler**       | simple                                                              | Requerido por el modelo Flux.2 Klein Distilled.                                       |
| **width × height**  | 1024 × 1024 px (configurable vía `IMAGE_WIDTH` / `IMAGE_HEIGHT`)   | Resolución óptima para el modelo; otras resoluciones pueden producir artefactos.      |
| **negative_prompt** | blurry, ugly, deformed, watermark, text, extra limbs, worst quality | Filtro base para mejorar consistencia y evitar artefactos comunes.                    |

## Registro y trazabilidad de imágenes (IMPLEMENTADO)

Cada imagen generada queda registrada en las tablas `image_generations` + `image_records`:

- `final_prompt` exacto usado en `image_generations` (para auditoría y reproducibilidad).
- `seed` en `image_records` (permite reproducir la misma imagen exacta si se usa ComfyUI).
- `generation_ms` en `image_records` (actualmente 0; se puede rellenar con el tiempo real de ComfyUI).
- `backend` en `image_generations`: `’mock’` o `’comfyui’`.
- `storage_path` en `image_records`: ruta relativa dentro de `MEDIA_ROOT`; `image_url` como fallback para el backend mock (URL de placehold.co).
