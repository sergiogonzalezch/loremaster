# Lore Master — Documentación de Arquitectura

> Documento técnico de referencia. Los diagramas usan [Mermaid](https://mermaid.js.org/)
> y se renderizan en GitHub, VS Code (con extensión), Obsidian y exportadores a PDF.

**Versión:** 1.0 · **Fecha:** 2026-06-02 · **Stack:** FastAPI · React 19 · Qdrant · Ollama

---

## Tabla de contenidos

1. [Visión general](#1-visión-general)
2. [Stack tecnológico](#2-stack-tecnológico)
3. [Arquitectura de contexto (C4)](#3-arquitectura-de-contexto-c4)
4. [Arquitectura de contenedores](#4-arquitectura-de-contenedores)
5. [Estructura del monorepo](#5-estructura-del-monorepo)
6. [Modelo de datos (ERD)](#6-modelo-de-datos-erd)
7. [Diagrama de clases — capas del backend](#7-diagrama-de-clases--capas-del-backend)
8. [Diagramas de secuencia](#8-diagramas-de-secuencia)
9. [Diagramas de flujo](#9-diagramas-de-flujo)
10. [Máquinas de estado](#10-máquinas-de-estado)
11. [Modelo de seguridad](#11-modelo-de-seguridad)
12. [Despliegue e infraestructura](#12-despliegue-e-infraestructura)
13. [Referencia de API](#13-referencia-de-api)
14. [Parámetros clave del sistema](#14-parámetros-clave-del-sistema)
15. [Arquitectura del frontend](#15-arquitectura-del-frontend)
16. [Borrado en cascada](#16-borrado-en-cascada-soft-delete--qdrant--archivos)
17. [Infraestructura de evaluación](#17-infraestructura-de-evaluación-harnesses)

---

## 1. Visión general

**Lore Master** es una herramienta RAG para *world-building* colaborativo (escritores,
creadores de RPG). Los usuarios suben documentos a **colecciones** y los consultan
mediante respuestas generadas por un LLM. Dentro de cada colección existen **entidades**
(personajes, criaturas, localizaciones, facciones, ítems) que acumulan **contenidos**
generados por RAG por categoría; confirmar un contenido auto-descarta los demás
pendientes de la misma categoría.

**Propuesta de valor:**
- **RAG de texto:** consulta de lore fundamentada en los documentos subidos.
- **RAG de imagen:** generación de imágenes a partir del lore (prompt construido por LLM).
- **Multi-tenant:** todo cuelga del usuario propietario; aislamiento por ownership.
- **Moderación multicapa:** guardrails léxicos + capa semántica opcional.

**Principios de diseño:** dominio puro, separación de capas (rutas → servicios →
dominio/engine → modelos), *soft-delete* en toda la capa de datos, e inferencia
LLM/imagen *self-hosted* (sin enviar datos de usuarios a terceros).

---

## 2. Stack tecnológico

| Capa | Tecnología |
|---|---|
| **Frontend** | React 19 · TypeScript (strict) · Vite 8 · React Router 7 · React Bootstrap 5 · `fetch` nativo |
| **Backend** | FastAPI · SQLModel · Pydantic Settings · Uvicorn |
| **LLM (texto)** | Ollama — `llama3.2:latest` (generación) · `mistral:latest` (prompts de imagen) |
| **Embeddings** | `sentence-transformers` — `paraphrase-multilingual-MiniLM-L12-v2` (384 dims) |
| **Vector DB** | Qdrant (distancia coseno, colección por `lm_{collection_id}`) |
| **Imagen** | ComfyUI (local) · RunPod Serverless (skeleton) · mock (tests) |
| **Moderación** | Guard léxico (regex) + Llama Guard 3 (semántico, fail-open) |
| **Base de datos** | SQLite (local) · PostgreSQL (Docker/prod) |
| **Caché / rate limit** | Redis |
| **Storage** | S3-compatible vía `boto3` — Floci (demo local) · Cloudflare R2 (cloud) |
| **Auth** | JWT local (cookies HttpOnly + CSRF) · Clerk (RS256) |
| **Reverse proxy** | Nginx (un solo puerto `:80`) |
| **Exposición pública** | Cloudflare Named Tunnel + TLS de borde |
| **Migraciones** | Alembic (auto-aplicadas en startup) |

---

## 3. Arquitectura de contexto (C4)

```mermaid
graph TB
    user([👤 Usuario<br/>escritor / creador RPG])
    admin([👤 Administrador])

    subgraph LM[Lore Master]
        app[Sistema Lore Master<br/>RAG texto + imagen + moderación]
    end

    clerk[/Clerk<br/>identidad opcional/]
    ollama[/Ollama<br/>LLM local/]
    comfy[/ComfyUI · RunPod<br/>generación de imagen/]
    r2[/Cloudflare R2<br/>storage de media/]
    cf[/Cloudflare Tunnel<br/>TLS + exposición/]

    user -->|sube documentos, consulta lore,<br/>genera contenido e imágenes| app
    admin -->|gestiona usuarios y contenido| app
    app -->|verifica JWT| clerk
    app -->|prompts de texto| ollama
    app -->|prompts de imagen| comfy
    app -->|sube/sirve imágenes| r2
    app -.->|expuesto vía| cf
    cf -->|HTTPS| user
```

---

## 4. Arquitectura de contenedores

```mermaid
graph TB
    browser([Navegador del usuario])

    subgraph edge[Cloudflare Edge]
        tunnel[cloudflared<br/>Named Tunnel · TLS]
    end

    subgraph host[Máquina host · Docker]
        subgraph net[Red Docker interna]
            nginx[Nginx :80<br/>reverse proxy + SPA]
            api[loremaster-api :8000<br/>FastAPI]
            pg[(PostgreSQL)]
            qdrant[(Qdrant)]
            redis[(Redis)]
            floci[(Floci S3<br/>fallback local)]
        end
        ollama[Ollama :11434]
        comfy[ComfyUI :8188]
    end

    r2[(Cloudflare R2<br/>S3-compatible)]

    browser -->|HTTPS| tunnel
    tunnel -->|HTTP| nginx
    nginx -->|/api/*| api
    nginx -->|/*| nginx
    api --> pg
    api --> qdrant
    api --> redis
    api -->|host.docker.internal| ollama
    api -->|host.docker.internal| comfy
    api -->|boto3| r2
    api -.->|fallback| floci
    browser -->|carga imágenes directo| r2
```

**Notas:**
- Un único puerto (`:80`) expuesto al host; backend, BD, vector store y caché son
  invisibles desde fuera de la red Docker.
- Las imágenes se sirven **directamente desde R2** (no pasan por Nginx ni el túnel).
- Ollama y ComfyUI corren en el host y se acceden vía `host.docker.internal`.

---

## 5. Estructura del monorepo

```
loremaster/
├── backend/                      # FastAPI + SQLModel + Qdrant + Ollama
│   ├── app/
│   │   ├── api/
│   │   │   ├── middlewares/       # rate_limit · security_headers
│   │   │   └── routes/            # auth · collections · documents · entities · images · public · admin · media
│   │   ├── core/
│   │   │   ├── auth/              # JWT · CSRF · dependencies · clerk
│   │   │   ├── config/            # Pydantic Settings
│   │   │   ├── database/          # mixins · soft_delete · utils
│   │   │   └── storage/           # S3 client · FileValidator
│   │   ├── domain/                # content_guard · llama_guard · prompt_templates · category_rules
│   │   ├── engine/                # rag · rag_pipeline · llm · extractor · comfyui_client · runpod_client
│   │   ├── models/
│   │   │   ├── db/                # SQLModel (tablas)
│   │   │   ├── schemas/           # Pydantic (request/response)
│   │   │   └── enums.py
│   │   └── services/              # lógica de negocio por dominio
│   └── evaluations/              # harnesses de evaluación (RAG, LLM, guard)
├── frontend/                     # React 19 + TypeScript + Vite
│   └── src/
│       ├── api/                  # clientes HTTP tipados
│       ├── components/ · pages/  # UI
│       ├── contexts/ · hooks/    # estado y lógica reutilizable
│       └── utils/                # enums · errores (ES) · formatters
└── docs/                         # arquitectura · planning · completed · history
```

---

## 6. Modelo de datos (ERD)

Todas las tablas de dominio usan **soft-delete** (`is_deleted` + `deleted_at`),
excepto `GeneratedText`, `GeneratedTextChunk` y `ModerationLog` (inmutables / append-only).

```mermaid
erDiagram
    USER ||--o{ COLLECTION : "owns (owner_id)"
    COLLECTION ||--o{ DOCUMENT : contains
    COLLECTION ||--o{ ENTITY : contains
    ENTITY ||--o{ ENTITY_CONTENT : "has"
    ENTITY ||--o{ GENERATED_TEXT : "generates"
    GENERATED_TEXT ||--o{ GENERATED_TEXT_CHUNK : "cites"
    GENERATED_TEXT ||--|| ENTITY_CONTENT : "source of"
    ENTITY ||--o{ IMAGE_GENERATION : "requests"
    ENTITY_CONTENT |o--o{ IMAGE_GENERATION : "prompts (content_id)"
    IMAGE_GENERATION ||--o{ IMAGE_RECORD : "produces (batch)"
    DOCUMENT |o..o{ GENERATED_TEXT_CHUNK : "source (no FK)"

    USER {
        string id PK
        string username UK
        string hashed_password
        string email UK
        string display_name
        string avatar_path
        bool is_admin
        int token_version
        datetime created_at
    }
    COLLECTION {
        string id PK
        string name
        string description
        string owner_id FK
        datetime created_at
        string updated_by
    }
    DOCUMENT {
        string id PK
        string collection_id FK
        string filename
        string file_type
        string content_hash
        int chunk_count
        enum status "processing|completed|failed"
        text raw_text
        datetime created_at
    }
    ENTITY {
        string id PK
        string collection_id FK
        enum type "character|creature|faction|location|item"
        string name
        string description
        datetime created_at
    }
    ENTITY_CONTENT {
        string id PK
        string entity_id FK
        string collection_id FK
        string generated_text_id FK
        enum category "backstory|extended_description|scene"
        string content
        enum status "pending|confirmed|discarded"
        bool is_shared
        datetime confirmed_at
    }
    GENERATED_TEXT {
        string id PK
        string entity_id FK
        string collection_id FK
        enum category
        string query
        string raw_content
        int sources_count
        int token_count
        string model_used
    }
    GENERATED_TEXT_CHUNK {
        string id PK
        string generated_text_id FK
        string document_id "nullable, no FK"
        text chunk_text
        int position
        float score
    }
    IMAGE_GENERATION {
        string id PK
        string entity_id FK
        string collection_id FK
        string content_id FK
        string auto_prompt
        string final_prompt
        int batch_size
        string backend
        int width
        int height
    }
    IMAGE_RECORD {
        string id PK
        string generation_id FK
        string entity_id FK
        string collection_id FK
        int seed
        string storage_path
        string image_url
        int generation_ms
        bool is_shared
    }
    MODERATION_LOG {
        int id PK
        string layer "input|output|document"
        string snippet
        string user_id
        string operation
        string pattern_matched
        datetime created_at
    }
```

**Reglas de negocio clave:**
- `Collection.name` es único **por propietario** (`uq_collection_name_owner`).
- `Entity.name` es único **por colección** (`uq_entity_collection_name`).
- Un `EntityContent` referencia exactamente un `GeneratedText` (su origen inmutable).
- Confirmar un `EntityContent` auto-descarta los demás `pending` de la misma
  `(entity_id, category)`.
- `GeneratedTextChunk.document_id` no tiene FK dura: sobrevive al borrado del documento
  para preservar la auditoría de fuentes.

---

## 7. Diagrama de clases — capas del backend

```mermaid
classDiagram
    direction LR

    class Route {
        <<API layer>>
        +depends(get_current_user)
        +depends(get_collection_or_404_owned)
        +validate(schema)
    }
    class Service {
        <<business logic>>
        +orchestrate()
        +db_commit()
    }
    class Domain {
        <<pure domain>>
        +check_user_input()
        +check_generated_output()
        +render_prompt()
    }
    class Engine {
        <<infra adapters>>
        +invoke_rag_pipeline()
        +retrieve_context()
        +ingest_chunks()
    }
    class Model {
        <<SQLModel>>
        +soft_delete()
    }

    Route --> Service : delega
    Service --> Domain : valida / construye prompt
    Service --> Engine : RAG / LLM / imagen
    Service --> Model : persiste
    Engine --> Model : lee/escribe

    class ContentGuard {
        +check_user_input(text)
        +check_generated_output(text)
        +check_document_content(text)
        +check_prompt_length(text)
    }
    class LlamaGuard {
        +check_with_llama_guard(query, answer) async
    }
    class RagPipeline {
        +invoke_rag_pipeline() async
        +invoke_generation_pipeline() async
        -_llm_semaphore: Semaphore(1)
    }
    class Rag {
        +ingest_chunks()
        +retrieve_context()
        +search_context()
        +delete_collection_vectors()
    }

    Domain <|.. ContentGuard
    Domain <|.. LlamaGuard
    Engine <|.. RagPipeline
    Engine <|.. Rag
    RagPipeline --> Rag : retrieve_context()
```

**Convención de capas:** las rutas nunca tocan el ORM directamente para lógica de
negocio; delegan en servicios. El dominio (`content_guard`, `prompt_templates`) es
puro y testeable sin I/O. El engine encapsula Qdrant, Ollama y ComfyUI.

---

## 8. Diagramas de secuencia

### 8.1 Autenticación (dual: JWT local + Clerk)

```mermaid
sequenceDiagram
    actor U as Usuario
    participant FE as Frontend (React)
    participant API as FastAPI
    participant DB as PostgreSQL
    participant CK as Clerk (JWKS)

    rect rgb(235, 245, 255)
    note over U,DB: Flujo local (JWT propio)
    U->>FE: login(username, password)
    FE->>API: POST /api/v1/auth/login
    API->>DB: buscar usuario + verify_password (bcrypt)
    DB-->>API: usuario válido
    API->>API: crear access_token (15min) + refresh + CSRF
    API-->>FE: Set-Cookie HttpOnly (access, refresh, csrf)
    end

    rect rgb(240, 255, 240)
    note over U,CK: Flujo Clerk (RS256)
    U->>FE: sign-in con Clerk
    FE->>API: request con Clerk JWT (Bearer)
    API->>CK: validar firma contra JWKS (RS256, issuer, audience)
    CK-->>API: token válido
    API->>DB: get_or_create User por email · check is_deleted · token_version
    DB-->>API: usuario
    API-->>FE: respuesta autorizada
    end
```

### 8.2 Ingesta de documento (extracción síncrona + embedding en background)

```mermaid
sequenceDiagram
    actor U as Usuario
    participant API as FastAPI
    participant V as FileValidator
    participant EX as extractor
    participant G as ContentGuard
    participant DB as PostgreSQL
    participant BG as BackgroundTask
    participant Q as Qdrant

    U->>API: POST /collections/{id}/documents (UploadFile)
    API->>V: validar MIME, magic bytes, tamaño (≤50MB)
    V-->>API: ok
    API->>EX: extract_text (PDF/TXT, timeout 30s, run_in_executor)
    EX-->>API: texto extraído
    API->>G: check_document_content(texto)
    alt contenido bloqueado
        G-->>API: ContentNotAllowedError
        API-->>U: 400 (mensaje en ES)
    else permitido
        G-->>API: ok
        API->>DB: crear Document (status=processing, raw_text, content_hash)
        API-->>U: 201 (doc_id, processing)
        API->>BG: process_ingest_background(doc_id, texto)
        BG->>BG: chunking (size=400, overlap=150)
        BG->>Q: ingest_chunks → embeddings → upsert(lm_{collection_id})
        BG->>DB: status=completed, chunk_count=N
    end
```

### 8.3 Generación de contenido RAG (con moderación multicapa)

```mermaid
sequenceDiagram
    actor U as Usuario
    participant API as FastAPI
    participant SVC as generation_service
    participant G as ContentGuard
    participant RP as rag_pipeline
    participant Q as Qdrant
    participant O as Ollama
    participant LG as LlamaGuard
    participant DB as PostgreSQL

    U->>API: POST generar contenido (entity, category, query)
    API->>SVC: generate(...)
    SVC->>G: check_prompt_length + check_user_input(query)
    alt input bloqueado
        G-->>API: ContentNotAllowedError → 400
    end
    SVC->>RP: invoke_generation_pipeline()
    RP->>Q: retrieve_context (top_k=4, threshold=0.30)
    Q-->>RP: chunks + scores
    alt semáforo ocupado
        RP-->>API: LLMBusyError → 429 (Retry-After: 30)
    else disponible
        RP->>O: chain.invoke (run_in_executor, Semaphore=1)
        O-->>RP: texto generado
    end
    RP-->>SVC: respuesta + chunks citados
    SVC->>G: check_generated_output(answer)
    SVC->>LG: check_with_llama_guard(query, answer) [fail-open]
    SVC->>DB: GeneratedText + GeneratedTextChunk[] + EntityContent(pending)
    DB-->>API: contenido pending
    API-->>U: 201 contenido generado
```

### 8.4 Generación de imagen (dos pasos)

```mermaid
sequenceDiagram
    actor U as Usuario
    participant API as FastAPI
    participant PB as image_prompt_builder
    participant O as Ollama (mistral)
    participant SVC as image_generation_service
    participant BK as backend (ComfyUI/RunPod)
    participant S3 as R2 / Floci
    participant DB as PostgreSQL

    U->>API: POST build-prompt (content_id)
    API->>PB: construir prompt visual desde el lore
    PB->>O: extraer atributos visuales
    O-->>PB: auto_prompt
    PB-->>U: auto_prompt (editable)

    U->>API: POST generate (auto_prompt, final_prompt, batch_size)
    API->>SVC: generate_images()
    SVC->>BK: submit workflow (batch 1-4, 1024x1024)
    BK-->>SVC: imágenes (bytes)
    SVC->>S3: subir imágenes (boto3)
    S3-->>SVC: image_url pública
    SVC->>DB: ImageGeneration + ImageRecord[]
    API-->>U: 201 imágenes (URLs de R2)
```

### 8.5 Refresh de token (proactivo + reactivo con coalescing)

El frontend renueva el access token de dos formas complementarias: **proactiva**
(`AuthContext` programa el refresh 60s antes de expirar) y **reactiva** (`apiClient`
intenta refrescar al recibir un 401). Múltiples 401 concurrentes comparten una única
promesa de refresh (singleton) para evitar N llamadas paralelas.

```mermaid
sequenceDiagram
    participant FE as Frontend (apiClient)
    participant CTX as AuthContext
    participant API as FastAPI /auth/refresh
    participant DB as PostgreSQL

    rect rgb(235, 245, 255)
    note over CTX: Proactivo — 60s antes de expirar
    CTX->>CTX: scheduleRefresh(expires_at - 60s)
    CTX->>API: POST /auth/refresh (cookie refresh)
    API->>DB: validar refresh + token_version
    API-->>CTX: Set-Cookie nuevo access + reprogramar
    end

    rect rgb(255, 245, 235)
    note over FE,API: Reactivo — 401 con coalescing
    FE->>API: GET /recurso (access expirado)
    API-->>FE: 401
    alt endpoint en NO_REFRESH (login/refresh)
        FE->>FE: no refresca → redirige a /login
    else refresh ya en vuelo
        FE->>FE: reutiliza _refreshPromise (singleton)
    else primer 401
        FE->>API: POST /auth/refresh
        API->>DB: validar refresh + token_version
        alt refresh válido
            API-->>FE: Set-Cookie nuevo access
            FE->>API: reintentar request original (1 vez)
            API-->>FE: 200
        else refresh inválido/expirado
            API-->>FE: 401 → limpiar sesión → /login
        end
    end
    end
```

**Garantías:**
- La cookie de refresh está *scoped* a `/api/v1/auth/refresh` (no viaja en cada request).
- `token_version` permite invalidar todas las sesiones (logout global) de forma *timing-safe*.
- El *floor* mínimo entre refreshes evita bucles si el reloj del cliente está adelantado.

---

## 9. Diagramas de flujo

### 9.1 Pipeline RAG (ingesta → consulta)

```mermaid
flowchart LR
    subgraph Ingesta
        A[Documento PDF/TXT] --> B[Extracción de texto]
        B --> C[Moderación de documento]
        C --> D[Chunking<br/>400 chars / 150 overlap]
        D --> E[Embeddings<br/>MiniLM 384d]
        E --> F[(Qdrant<br/>lm_collection_id)]
    end

    subgraph Consulta
        G[Query del usuario] --> H[Moderación de input]
        H --> I[Embedding de query]
        I --> J[Búsqueda coseno<br/>top_k=4 · thr=0.30]
        F --> J
        J --> K[Ensamblar contexto]
        K --> L[Prompt template + LLM]
        L --> M[Moderación de output]
        M --> N[Respuesta + chunks citados]
    end
```

### 9.2 Pipeline de moderación (3 capas)

```mermaid
flowchart TB
    IN[Texto entrante] --> L1{Capa 1<br/>Guard léxico input}
    L1 -->|bloqueado| BLK[ContentNotAllowedError<br/>+ ModerationLog]
    L1 -->|permitido| LLM[Generación LLM]
    LLM --> L2{Capa 2<br/>Guard léxico output}
    L2 -->|bloqueado| BLK
    L2 -->|permitido| L3{Capa 3<br/>Llama Guard 3<br/>semántico · fail-open}
    L3 -->|unsafe| BLK
    L3 -->|safe / no disponible| OK[Persistir contenido]

    DOC[Texto de documento] --> L1
```

> La capa 3 es **fail-open**: si Llama Guard no está disponible, el contenido pasa
> (se registra) en lugar de bloquear el servicio. Activable con `LLAMA_GUARD_ENABLED=true`.

---

## 10. Máquinas de estado

### 10.1 Ciclo de vida del contenido de entidad

```mermaid
stateDiagram-v2
    [*] --> pending : generación RAG
    pending --> confirmed : usuario confirma
    pending --> discarded : usuario descarta
    confirmed --> discarded : se confirma otro de la misma categoría
    confirmed --> [*] : (puede compartirse al feed)
    discarded --> [*]

    note right of confirmed
        Confirmar auto-descarta
        los demás pending de la
        misma (entity, category)
    end note
```

### 10.2 Estado de procesamiento de documento

```mermaid
stateDiagram-v2
    [*] --> processing : upload + extracción ok
    processing --> completed : chunks indexados en Qdrant
    processing --> failed : error de embedding/indexado
    failed --> processing : retry_ingest
    completed --> [*]
```

---

## 11. Modelo de seguridad

### 11.1 Capas de defensa

```mermaid
flowchart TB
    req[Request] --> mw1[CORSMiddleware]
    mw1 --> mw2[RateLimitMiddleware<br/>Redis · req/min por IP]
    mw2 --> mw3[SecurityHeadersMiddleware<br/>HSTS · CSP · X-Frame-Options · nosniff]
    mw3 --> csrf{CSRF check<br/>métodos no seguros}
    csrf -->|inválido| r403[403]
    csrf -->|válido| auth{Autenticación}
    auth -->|local| jwtlocal[JWT HttpOnly cookie<br/>+ token_version]
    auth -->|clerk| jwtclerk[Clerk RS256<br/>issuer + audience]
    jwtlocal --> own{Ownership check<br/>get_*_or_404_owned}
    jwtclerk --> own
    own -->|ajeno| r403b[403/404]
    own -->|propio| route[Handler]
```

### 11.2 Controles implementados

| Control | Mecanismo |
|---|---|
| **Autenticación** | JWT local (cookies HttpOnly, access 15min + refresh 7d) o Clerk RS256 |
| **Revocación** | `token_version` con comparación *timing-safe* (`hmac.compare_digest`) |
| **CSRF** | Double-submit cookie; validado en POST/PUT/PATCH/DELETE |
| **Autorización** | Ownership por dependencia (`get_collection_or_404_owned`, etc.) — sin IDOR |
| **Rate limiting** | Middleware global + límites específicos para LLM e imagen |
| **Headers** | HSTS, CSP, X-Frame-Options DENY, X-Content-Type-Options nosniff |
| **Subida de archivos** | MIME + magic bytes + tamaño + límite de páginas PDF + strip EXIF |
| **Media** | Controller con auth + ownership; `is_shared` para feed público |
| **Path traversal** | `username` con regex estricta + contención bajo `media_root` |
| **Moderación** | 3 capas (input/output léxico + Llama Guard semántico) + `ModerationLog` |
| **Logging PII** | `PIIFilter` global redacta passwords, emails, tokens, secrets |
| **Concurrencia LLM** | `asyncio.Semaphore(1)` → HTTP 429 + `Retry-After: 30` |

---

## 12. Despliegue e infraestructura

### 12.1 Topología de despliegue (demo/portafolio)

```mermaid
flowchart TB
    subgraph internet[Internet]
        visitor([Evaluador / visitante])
    end

    subgraph cf[Cloudflare]
        edge[Edge · TLS gratuito]
        tun[Named Tunnel<br/>loremasterai.site]
        r2[(R2 · media<br/>10GB free · egress $0)]
    end

    subgraph pc[Máquina host del desarrollador]
        cfd[cloudflared daemon]
        subgraph docker[Docker Compose · prod]
            ng[Nginx :80]
            api[FastAPI]
            pg[(PostgreSQL)]
            qd[(Qdrant)]
            rd[(Redis)]
        end
        oll[Ollama :11434]
        cmf[ComfyUI :8188]
    end

    visitor -->|HTTPS| edge
    edge --> tun
    tun -->|conexión saliente| cfd
    cfd -->|HTTP| ng
    ng --> api
    api --> pg & qd & rd
    api --> oll & cmf
    api -->|boto3| r2
    visitor -->|imágenes directo| r2
```

**Características del despliegue gratuito:**
- **Sin VPS ni port-forwarding:** `cloudflared` hace una conexión HTTPS saliente.
- **URL fija:** Named Tunnel sobre dominio propio (`loremasterai.site`).
- **TLS:** terminado en el borde de Cloudflare, sin tocar `nginx.conf`.
- **Storage:** Cloudflare R2 (S3-compatible, free tier 10 GB, egress $0).
- **Costo:** ~$0/mes (solo el dominio, ~$1-3/año).

### 12.2 Modos de ejecución

| Modo | BD | Storage | Imagen | Exposición |
|---|---|---|---|---|
| **local** | SQLite | filesystem | mock/ComfyUI | localhost |
| **demo (Docker)** | PostgreSQL | Floci / R2 | ComfyUI | Cloudflare Tunnel |
| **producción** | PostgreSQL | R2 | ComfyUI / RunPod | Named Tunnel + dominio |

---

## 13. Referencia de API

Todas las rutas bajo `/api/v1/`. Recurso raíz: **colecciones** →
`documents | entities → contents | images`.

| Dominio | Endpoints principales |
|---|---|
| **Auth (local)** | `POST /auth/login` · `POST /auth/register` · `POST /auth/refresh` · `POST /auth/logout` |
| **Auth (Clerk)** | `POST /auth/clerk/verify` · sincronización por email |
| **Colecciones** | `POST /collections` · `GET /collections` · `GET/DELETE /collections/{id}` · `POST /collections/bulk-delete` |
| **RAG query** | `POST /collections/{id}/query` (consulta libre fundamentada) |
| **Documentos** | `POST /collections/{id}/documents` · `GET .../documents` · `GET .../documents/events` (SSE) · `POST .../bulk-delete` · retry |
| **Entidades** | `POST /collections/{id}/entities` · `GET/PATCH/DELETE .../entities/{eid}` · `POST .../bulk-delete` |
| **Contenidos** | generar · confirmar · descartar · editar · compartir |
| **Imágenes** | `POST .../image-generation/build-prompt` · `POST .../image-generation/generate` |
| **Media** | `GET /media/...` (controller con auth + ownership) |
| **Público** | `GET /public/...` (feed de contenido/imágenes compartidos) |
| **Usuarios** | `GET/PATCH /users/me` · avatar · perfil público |
| **Admin** | gestión de usuarios y contenido (requiere `is_admin`) |
| **Modelos / metadata** | `GET /models` (Ollama) · `GET /metadata` |
| **Health** | `GET /health` (Qdrant + Ollama) |

---

## 14. Parámetros clave del sistema

| Parámetro | Valor | Dónde |
|---|---|---|
| `chunk_size` | 400 chars | RAG ingesta |
| `chunk_overlap` | 150 chars | RAG ingesta |
| `top_k` | 4 | RAG retrieval |
| `rag_score_threshold` | 0.30 (coseno) | RAG retrieval |
| `embedding_model` | `paraphrase-multilingual-MiniLM-L12-v2` (384d) | embeddings |
| `ollama_model` | `llama3.2:latest` | generación de texto |
| `image_prompt_model` | `mistral:latest` | prompts de imagen |
| `max_concurrent_llm_calls` | 1 (semáforo async) | concurrencia |
| `max_tokens` | 2000 | salida LLM |
| `temperature` | 0.7 | LLM |
| `max_pending_contents` | 5 | por entidad/categoría |
| `document_max_upload_mb` | 50 | subida de documentos |
| `max_pdf_pages` | 100 | anti PDF-bomb |
| `profile_image_max_size_mb` | 10 | avatares |
| `image` (default) | 1024×1024, batch 1-4 | generación |
| `access_token_expire_minutes` | 15 | JWT local |
| `refresh_token_expire_days` | 7 | JWT local |

---

## 15. Arquitectura del frontend

### 15.1 Componentes y flujo de datos

```mermaid
graph TB
    main[main.tsx] --> provider[ClerkProvider<br/>+ AuthProvider]
    provider --> router[React Router 7]

    subgraph routing[Enrutamiento protegido]
        router --> prot[ProtectedRoute]
        router --> adminr[AdminRoute]
        prot --> layout[Layout + AppNavbar + AppFooter]
        adminr --> layout
    end

    subgraph pages[Páginas]
        layout --> login[LoginPage]
        layout --> cols[CollectionsPage]
        layout --> coldetail[CollectionDetailPage<br/>Documents · Entities · Generate]
        layout --> entity[EntityDetailPage]
        layout --> profile[ProfilePage]
        layout --> feed[PublicFeedPage]
        layout --> admin[AdminPage]
    end

    subgraph shared[Componentes reutilizables]
        contentcard[ContentCard]
        imagepanel[ImagePanel]
        entitypanel[EntityContentsPanel]
        safeimg[SafeImage]
        modals[ConfirmModal · SourcesModal · PublicImageModal]
        filters[FilterBar · PaginationControls]
    end

    coldetail --> entitypanel
    entitypanel --> contentcard
    entity --> imagepanel
    contentcard --> safeimg
    imagepanel --> safeimg

    subgraph state[Estado y lógica]
        ctx[AuthContext]
        hooks[useAuth · useGenerate · useEntityContents<br/>usePagination · useDeleteConfirm]
    end

    pages --> hooks
    hooks --> apilayer

    subgraph apilayer[Capa API]
        factory[factory.ts<br/>apiGet/Post/Patch/Delete]
        client[apiClient.ts<br/>fetch + refresh + ApiError]
        clients[collections · documents · entities<br/>contents · images · auth · users]
    end

    factory --> client
    clients --> factory
    client -->|/api/v1/*| backend[(FastAPI)]
    provider --> ctx
```

### 15.2 Decisiones de diseño del frontend

| Decisión | Detalle |
|---|---|
| **Sin librería de estado global** | `AuthContext` para sesión; estado local + hooks por feature |
| **`fetch` nativo** | Sin axios; `apiClient` centraliza errores y refresh |
| **Errores en español** | `utils/errors.ts` mapea status → mensaje descriptivo (nunca el código crudo) |
| **Abstracciones DRY** | `PaginationControls`, `FilterBar`, `useApiError`, `useFormSubmit`, `factory.ts` |
| **Seguridad de imágenes** | `SafeImage` + `isImageUrlAllowed` (allowlist de orígenes) con fallback |
| **Rutas protegidas** | `ProtectedRoute` (sesión) y `AdminRoute` (`is_admin` desde backend, no del JWT) |
| **Tabs divididos** | `CollectionDetailPage` separado en Documents/Entities/Generate para reducir tamaño de componente |

---

## 16. Borrado en cascada (soft-delete + Qdrant + archivos)

El borrado es **atómico**: las operaciones de soft-delete usan `commit=False` y se
confirman en una sola transacción; los efectos secundarios irreversibles (vectores
Qdrant, archivos en disco) se ejecutan con tolerancia a fallos parciales.

```mermaid
flowchart TB
    del[DELETE colección] --> docs[soft_delete documentos]
    docs --> ents[Por cada entidad:]
    ents --> cont[soft_delete contenidos<br/>cascade_service · commit=False]
    cont --> imgs[Por cada imagen:]
    imgs --> file[_delete_image_file<br/>is_relative_to media_root]
    file --> imgrec[soft_delete ImageRecord<br/>commit=False]
    imgrec --> col[soft_delete colección<br/>commit=False]
    col --> commit[(COMMIT único<br/>transacción atómica)]
    commit --> vectors[_delete_vectors_with_retry<br/>3 intentos · 0.5s · delete lm_collection_id]
    vectors -->|fallo total| log[log de error<br/>+ instrucción de limpieza manual]
```

**Garantías y separación de responsabilidades:**

| Servicio | Responsabilidad |
|---|---|
| `cascade_service` | **Solo soft-delete** de `EntityContent` (BD), `commit=False` |
| `deletion_service` | Orquesta todo: soft-delete BD + **borrado físico** de archivos + **vectores Qdrant** |
| `_delete_image_file` | Borra el archivo validando `is_relative_to(media_root)` (anti path-traversal) |
| `_delete_vectors_with_retry` | Borra la colección Qdrant `lm_{collection_id}` con reintentos |

- El soft-delete (`is_deleted=True` + `deleted_at`) preserva la fila para auditoría.
- Si Qdrant falla tras agotar reintentos, la transacción de BD ya está confirmada y
  queda un log con instrucción de limpieza manual (los vectores huérfanos no afectan
  consultas porque el filtro de ownership ya excluye la colección).

---

## 17. Infraestructura de evaluación (harnesses)

La calidad del RAG, los parámetros del LLM, la calidad de prompts y la moderación se
miden con **harnesses** independientes bajo `backend/evaluations/`. Todos siguen el
mismo patrón **runner → judge → reporter**.

```mermaid
flowchart LR
    subgraph harness[Patrón de harness]
        ds[(dataset /<br/>test_cases)] --> runner[runner.py<br/>ejecuta N configs × modelos]
        runner --> judge[judge.py<br/>mecánico o LLM-as-judge]
        judge --> reporter[reporter.py<br/>métricas + tablas]
        reporter --> res[(results/<br/>reportes .md)]
    end
```

| Harness | Qué mide | Decisión derivada |
|---|---|---|
| `rag_params_harness` | `chunk_size`, `overlap`, `threshold`, `top_k` | 400 / 150 / 0.30 / 4 |
| `llm_params_harness` | `temperature`, `max_tokens` por categoría | uniformes (Δ neutral) |
| `prompt_harness` | calidad de los prompt templates | iteración de plantillas |
| `image_prompt_harness` | calidad del prompt visual construido | reglas en `image_prompt_rules` |
| `metadata_harness` | cabeceras de fuente en el contexto RAG | descartado (Δ marginal) |
| `guard_harness` | efectividad de moderación (adversarial/bypass/legítimo) | refuerzo de patrones |

**Jueces:**
- **Mecánico (J1):** ¿el guard tomó la decisión correcta? (bloqueó lo que debía).
- **LLM-as-judge (J2/J3):** severidad del contenido no bloqueado / falsos positivos,
  con un modelo independiente como evaluador.

> Los resultados (`results/`) y los datasets del guard se mantienen fuera del control
> de versiones. La metodología prioriza definir el umbral de adopción **antes** de
> ejecutar el harness para evitar sesgo de confirmación.

---

*Documento generado a partir de la lectura directa del código fuente (2026-06-02).
Para detalle operacional ver `docs/architecture/DEPLOY.md` y `DEPLOY-CLOUDFLARE.md`.*
