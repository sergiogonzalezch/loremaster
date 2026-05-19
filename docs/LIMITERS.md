# LIMITERS.md — Mapa completo de límites, validaciones y constantes

> Última actualización: 2026-05-19 (3.ª revisión)
> Rama: `main`
> Regla de conversión usada en todo el documento: **1 token ≈ 4 caracteres** (estimación del engine en `image_prompt_builder._estimate_tokens`).

---

## 1. Flujo general y puntos de validación

```
┌─────────────────────────────────────────────────────────────────────┐
│  USUARIO escribe                                                      │
│  query / final_prompt / nombre / descripción / bio                    │
└───────────────────┬─────────────────────────────────────────────────┘
                    │
          [1] Pydantic Schema — fast-fail HTTP 422
              min_length / max_length / ge / le
              (máx queries/prompts: 2 000 chars | máx edición contenido: 10 000 chars)
                    │
          [2] content_guard.check_prompt_length()  ← solo prompts LLM
              _MIN_PROMPT_LENGTH = 10 chars
                    │
          [3] content_guard.check_user_input()     ← guardrails
              _normalize() → _BLOCKED_PATTERNS (regex)
              _MAX_TEXT_LENGTH = 100 000 chars  ← techo interno anti-ReDoS
              (ver §4.1 para detalle de impacto)
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  OLLAMA genera respuesta                                              │
│  num_predict = MAX_TOKENS = 2 000 tokens (~8 000 chars)              │
└───────────────────┬─────────────────────────────────────────────────┘
                    │
          [4] content_guard.check_generated_output()
              _normalize() → _OUTPUT_BLOCKED_PATTERNS (regex, menos estrictos)
              _MAX_TEXT_LENGTH aplica también aquí (anti-ReDoS)
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ALMACENAMIENTO en BD                                                 │
│  EntityContent.content      max 10 000 chars (~2 500 tok)            │
│  GeneratedText.raw_content  max 10 000 chars (~2 500 tok)            │
│  ImageGeneration.auto_prompt / final_prompt  max 2 000 chars ✅      │
└─────────────────────────────────────────────────────────────────────┘

FLUJO IMAGEN (paralelo al flujo principal):
  build-prompt  → LLM genera auto_prompt
                → _truncate_to_tokens(attrs ≤ 482 tok ≈ 1 928 chars)  engine
                → auto_prompt = attrs + ", " + QUALITY_SUFFIX ≤ 1 997 chars
                → frontend muestra al usuario
  generate      → usuario edita → auto_prompt (schema min=1, max=2 000 chars ✅)
                               → final_prompt (schema min=10, max=2 000 chars)
                → check_user_input(auto_prompt) ← guardrails contenido
                → check_prompt_length + check_user_input(final_prompt)
                → inject_prompt(final_prompt) → ComfyUI (sin truncate adicional)
                → auto_prompt + final_prompt se persisten (DB max 2 000 chars ✅)
```

---

## 2. Variables de INPUT — lo que entra del usuario

| Variable / Constante | Valor | Chars | Tokens equiv. | Origen | Aplica a | Nivel |
|---|---|---|---|---|---|---|
| `_MIN_PROMPT_LENGTH` | 10 chars | 10 | ~2 | `content_guard.py` | RAG query, generación contenido, `final_prompt` imagen | Domain + Schema |
| `RagQueryRequest.query` min | 10 chars | 10 | ~2 | Schema Pydantic | Query RAG | Schema (duplica domain) |
| `RagQueryRequest.query` max | 2 000 chars | 2 000 | ~500 | Schema Pydantic | Query RAG | Solo Schema |
| `GenerateContentRequest.query` min | 10 chars | 10 | ~2 | Schema Pydantic | Generación de contenido | Schema (duplica domain) |
| `GenerateContentRequest.query` max | 2 000 chars | 2 000 | ~500 | Schema Pydantic | Generación de contenido | Solo Schema |
| `GenerateImagesRequest.auto_prompt` min | 1 char | 1 | — | Schema Pydantic | Prompt automático LLM (reenviado por frontend) | Solo Schema |
| `GenerateImagesRequest.auto_prompt` max | 2 000 chars | 2 000 | ~500 | Schema Pydantic | Prompt automático LLM — alineado con engine (≤ 1 997 chars) y DB | Solo Schema |
| `GenerateImagesRequest.final_prompt` min | 10 chars | 10 | ~2 | Schema Pydantic | Prompt final imagen | Schema (duplica domain) |
| `GenerateImagesRequest.final_prompt` max | 2 000 chars | 2 000 | ~500 | Schema Pydantic | Prompt final imagen | Solo Schema |
| `GenerateImagesRequest.batch_size` | ge=1, le=4 | — | — | Schema Pydantic | Cantidad de imágenes | Solo Schema |
| `CreateCollectionRequest.name` | min=1, max=255 | 1–255 | — | Schema Pydantic | Nombre de colección | Solo Schema |
| `CreateCollectionRequest.description` | max=2 000 | 2 000 | ~500 | Schema Pydantic | Descripción colección | Solo Schema |
| `CreateEntityRequest.name` | min=1, max=200 | 1–200 | — | Schema Pydantic | Nombre de entidad | Solo Schema |
| `CreateEntityRequest.description` | max=2 000 | 2 000 | ~500 | Schema Pydantic | Descripción entidad | Solo Schema |
| `UpdateContentRequest.content` | min=1, max=10 000 | 1–10 000 | ~2 500 | Schema Pydantic | Texto editado por usuario | Solo Schema |
| `UpdateProfileRequest.display_name` | max=100 | 100 | — | Schema Pydantic | Nombre visible | Solo Schema |
| `UpdateProfileRequest.bio` | max=500 | 500 | — | Schema Pydantic | Biografía | Solo Schema |
| `UpdateProfileRequest.email` | max=255 | 255 | — | Schema Pydantic | Email | Solo Schema |
| `page_size` (paginación) | ge=1, le=100 | — | — | `core/api/params.py` | Todos los listados | Query param |
| `Document.filename` max | 255 chars | — | — | Service (`document_service.py`) | Nombre de archivo subido (límite de VARCHAR(255) en PostgreSQL) | Service |
| `DOCUMENT_MAX_UPLOAD_MB` | 50 MB | — | — | Settings | Archivos subidos (PDF/TXT) | Service |
| `PROFILE_IMAGE_MAX_SIZE_MB` | 5 MB | — | — | Settings | Avatar de usuario | Service |
| `MAX_PDF_PAGES` | 100 páginas | — | — | Settings | Prevención PDF bomb | Service |

---

## 3. Variables de OUTPUT LLM / ALMACENAMIENTO

| Variable / Constante | Valor | Chars equiv. | Tokens | Origen | Aplica a | Nivel |
|---|---|---|---|---|---|---|
| `MAX_TOKENS` | 2 000 tok | ~8 000 chars | 2 000 | Settings → `llm.py:num_predict` | Respuesta generada por Ollama | LLM output |
| `IMAGE_PROMPT_TOKENS` | 512 tok | ~2 048 chars | 512 | Settings → `image_prompt_builder._truncate_to_tokens` | `auto_prompt` antes de ComfyUI | Engine |
| `EntityContent.content` DB | max=10 000 chars | 10 000 | ~2 500 | DB model | Contenido generado + editado | BD |
| `GeneratedText.raw_content` DB | max=10 000 chars | 10 000 | ~2 500 | DB model | Texto bruto del LLM | BD |
| `GeneratedText.query` DB | max=2 000 chars | 2 000 | ~500 | DB model | Query almacenada | BD |
| `ImageGeneration.auto_prompt` DB | max=2 000 chars ✅ | 2 000 | ~500 | DB model | `auto_prompt` almacenado | BD |
| `ImageGeneration.final_prompt` DB | max=2 000 chars ✅ | 2 000 | ~500 | DB model | `final_prompt` almacenado | BD |

---

## 4. Variables internas de infraestructura

| Variable / Constante | Valor | Chars equiv. | Tokens equiv. | Propósito | Nivel |
|---|---|---|---|---|---|
| `_MAX_TEXT_LENGTH` | 100 000 chars | 100 000 | ~25 000 | Anti-ReDoS interno (ver §4.1) | Domain interno |
| `CHUNK_SIZE` | 400 chars | 400 | ~100 | Tamaño de chunk al indexar documentos en Qdrant. Reducido de 512 para evitar truncación silenciosa del embedding (`paraphrase-multilingual-MiniLM-L12-v2` tiene límite de 128 tokens; 512 chars en español generan 100-160 tokens). | RAG / Qdrant |
| `CHUNK_OVERLAP` | 150 chars | 150 | ~37 | Solapamiento entre chunks consecutivos. Aumentado de 50 para preservar coherencia narrativa en límites de chunk (una oración de transición mide ~80-120 chars). | RAG / Qdrant |
| `TOP_K` | 4 chunks | ~1 600 ctx total | ~400 ctx total | Chunks recuperados por similitud en cada query RAG | RAG |
| `rag_score_threshold` | 0.3 | — | — | Score mínimo de similitud para incluir chunk como contexto | RAG |
| `document_extraction_timeout_seconds` | 30 s | — | — | Settings → `document_service.py` | Timeout de extracción de texto (PDF/TXT); configurable vía `DOCUMENT_EXTRACTION_TIMEOUT_SECONDS` | Service |
| `rate_limit_per_minute` | 30 req/min | — | — | Requests por IP/usuario por minuto (middleware global) | Middleware |
| `rate_limit_llm_per_minute` | 5 req/min | — | — | Endpoints que terminan en `/query` o `/image-generation/build-prompt` — llamadas LLM-intensivas | Middleware |
| `rate_limit_image_per_minute` | 3 req/min | — | — | Endpoint `/image-generation/generate` — llamadas ComfyUI-intensivas | Middleware |
| `max_pending_contents` | 5 | — | — | Máximo de contenidos en estado `pending` por entidad/categoría | Domain |
| `max_concurrent_llm_calls` | 1 | — | — | Semáforo de llamadas simultáneas a Ollama | Engine |
| `access_token_expire_minutes` | 60 min | — | — | TTL del JWT de sesión | Auth |
| `embedding_dims` | 384 | — | — | Dimensiones del vector de embedding (`paraphrase-multilingual-MiniLM-L12-v2`) | RAG / Qdrant |
| `ModerationLog.snippet` DB | max=200 chars | 200 | ~50 | Fragmento guardado al detectar contenido bloqueado | BD |
| `SKIP_MIGRATIONS` | ausente / `true` | — | — | Si `1`/`true`/`yes`, el lifespan omite Alembic al arrancar. Inyectado por `baseline_evals.py` cuando las migraciones ya se aplicaron en el proceso padre (evita deadlock SQLite + asyncio/greenlet en Windows). No definir en producción. | Startup |

---

### 4.1 `_MAX_TEXT_LENGTH` — análisis detallado

**Valor:** `100 000 chars` (~25 000 tokens)
**Definido en:** `backend/app/domain/content_guard.py:31`
**Usado en:** `_normalize()`, llamada internamente por `check_user_input()`, `check_document_content()` y `check_generated_output()`

**Propósito — prevención de ReDoS (Regular Expression Denial of Service):**
Las expresiones regulares con patrones anidados aplicadas sobre textos muy largos pueden ejecutarse en tiempo exponencial o cuadrático, bloqueando el worker de FastAPI. `_MAX_TEXT_LENGTH` es el techo que evita ese escenario.

**Cómo funciona:**
```python
def _normalize(text: str) -> str:
    if len(text) > _MAX_TEXT_LENGTH:          # 1. Comprueba longitud
        logger.warning("Texto excede límite") # 2. Log silencioso
        text = text[:_MAX_TEXT_LENGTH]        # 3. Trunca — no lanza excepción
    # ... NFKD + lowercase + leet + colapso de repetidos
```

**Flujo completo donde interviene:**
```
Input de cualquier fuente
        ↓
check_user_input(text)   /   check_document_content(text)   /   check_generated_output(text)
        ↓
_check_text() → _normalize(text)
        ↓
_MAX_TEXT_LENGTH actúa aquí (trunca si > 100 000 chars)
        ↓
regex sobre texto ya truncado y normalizado
```

**Impacto real en producción: prácticamente nulo**

El límite de 100 000 chars nunca es alcanzable a través de la API normal porque todas las entradas pasan primero por Pydantic con `max_length` máximo de 10 000 chars (edición de contenido). Ningún campo de input de usuario supera ese valor. Por tanto:

| Escenario | ¿Llega a _MAX_TEXT_LENGTH? |
|---|---|
| Query RAG / generación (max 2 000 chars) | ✅ Nunca — 50× por debajo |
| `final_prompt` imagen (max 2 000 chars) | ✅ Nunca — 50× por debajo |
| Contenido editado (max 10 000 chars) | ✅ Nunca — 10× por debajo |
| Output del LLM (max ~8 000 chars) | ✅ Nunca — ~12× por debajo |
| Texto extraído de documentos subidos | ⚠ Teórico — un PDF/TXT grande podría generar raw_text largo, pero `check_document_content` se aplica al texto completo extraído antes del chunking. En la práctica el limite de 50 MB y 100 páginas lo contiene. |

**Conclusión:** `_MAX_TEXT_LENGTH` es una red de seguridad defensiva de última línea. No impacta el comportamiento normal de la aplicación. Solo actuaría si alguien llamara directamente a las funciones del domain bypaseando la API, o si el extractor de documentos generara texto inusualmente largo. Opera en silencio (log warning) sin lanzar excepción al usuario.

---

## 5. Conflictos — historial

### ✅ RESUELTO — `GenerateImagesRequest.auto_prompt` sin validación + engine vs DB
| Capa | Antes | Después |
|---|---|---|
| Schema Pydantic `auto_prompt` | `auto_prompt: str` (sin `Field()`) — sin min ni max | `Field(..., min_length=1, max_length=2000)` ✅ |
| Engine buffer (`build_visual_prompt`) | `available = max_tokens - suffix_tokens - 5` → attrs ≤ 1 964 chars, total ≤ **2 033 chars** ⚠ | `available = max_tokens - suffix_tokens - 14` → attrs ≤ 1 931 chars, total ≤ **1 997 chars** ✅ |
| DB model `auto_prompt` | `max_length=2000` — en conflicto con engine | `max_length=2000` — alineado con engine (sin cambio) ✅ |



### ✅ RESUELTO — `ImageGeneration.auto_prompt` DB vs engine
| Capa | Antes | Después |
|---|---|---|
| Engine (`_truncate_to_tokens`) | 512 tok ≈ ~2 048 chars | 512 tok ≈ ~2 048 chars (sin cambio) |
| DB model `auto_prompt` | **max=1 000 chars** ⚠ | **max=2 000 chars** ✅ |
| Migración | — | `942c4e2fc4ac_expand_image_prompt_columns_to_2000` |

### ✅ RESUELTO — `ImageGeneration.final_prompt` DB vs schema
| Capa | Antes | Después |
|---|---|---|
| Schema Pydantic `final_prompt` | max=2 000 chars | max=2 000 chars (sin cambio) |
| DB model `final_prompt` | **max=1 000 chars** ⚠ | **max=2 000 chars** ✅ |
| Migración | — | `942c4e2fc4ac_expand_image_prompt_columns_to_2000` |

---

## 6. Resumen de consistencia por flujo

| Flujo | Input validado | Output acotado | BD consistente | Estado |
|---|---|---|---|---|
| RAG query | ✅ min=10, max=2 000 chars | ✅ MAX_TOKENS=2 000 tok | ✅ query max=2 000, raw_content max=10 000 | ✅ OK |
| Generación contenido | ✅ min=10, max=2 000 chars | ✅ MAX_TOKENS=2 000 tok | ✅ content max=10 000 | ✅ OK |
| Generación imagen — `auto_prompt` | ✅ engine trunca a 512 tok | ✅ ~2 048 chars max | ✅ DB max=2 000 chars | ✅ OK |
| Generación imagen — `final_prompt` | ✅ min=10, max=2 000 chars | — (va directo a ComfyUI) | ✅ DB max=2 000 chars | ✅ OK |
| Edición contenido | ✅ min=1, max=10 000 chars | — (texto de usuario) | ✅ content max=10 000 | ✅ OK |
| Perfil usuario | ✅ display_name 100, bio 500 | — | ✅ DB iguales | ✅ OK |
| Upload documento | ✅ filename max=255 chars, max 50 MB, max 100 páginas | — | ✅ raw_text TEXT sin límite | ✅ OK |
| Guardrails contenido | ✅ `_BLOCKED_PATTERNS` en input | ✅ `_OUTPUT_BLOCKED_PATTERNS` en output | — | ✅ OK |
| Anti-ReDoS (`_MAX_TEXT_LENGTH`) | ✅ inactivo en uso normal de API | ✅ inactivo en uso normal de API | — | ✅ OK (red de seguridad) |
