# LIMITERS.md — Mapa completo de límites, validaciones y constantes

> Última actualización: 2026-05-14
> Rama: `dev`
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
                    │
          [2] content_guard.check_prompt_length()  ← solo prompts LLM
              _MIN_PROMPT_LENGTH = 10 chars
                    │
          [3] content_guard.check_user_input()     ← guardrails
              _BLOCKED_PATTERNS (regex sobre texto normalizado)
              _MAX_TEXT_LENGTH = 100 000 chars anti-ReDoS (trunca internamente)
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  OLLAMA genera respuesta                                              │
│  num_predict = MAX_TOKENS = 2 000 tokens (~8 000 chars)              │
└───────────────────┬─────────────────────────────────────────────────┘
                    │
          [4] content_guard.check_generated_output()
              _OUTPUT_BLOCKED_PATTERNS (regex, menos estrictos que input)
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ALMACENAMIENTO en BD                                                 │
│  EntityContent.content     max 10 000 chars                           │
│  GeneratedText.raw_content max 10 000 chars                           │
│  ImageGeneration.auto_prompt / final_prompt  max 1 000 chars ← ⚠ VER §5 │
└─────────────────────────────────────────────────────────────────────┘

FLUJO IMAGEN (paralelo):
  build-prompt  → LLM genera auto_prompt
                → _truncate_to_tokens(512 tok ≈ 2 048 chars)   engine
                → frontend muestra al usuario
  generate      → usuario edita → final_prompt (schema max 2 000 chars)
                → inject_prompt() → ComfyUI (sin truncate adicional)
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
| `ImageGeneration.auto_prompt` DB | max=1 000 chars | 1 000 | ~250 | DB model | `auto_prompt` almacenado | BD ⚠ |
| `ImageGeneration.final_prompt` DB | max=1 000 chars | 1 000 | ~250 | DB model | `final_prompt` almacenado | BD ⚠ |

---

## 4. Variables internas de infraestructura

| Variable / Constante | Valor | Propósito | Nivel |
|---|---|---|---|
| `_MAX_TEXT_LENGTH` | 100 000 chars (~25 000 tok) | Anti-ReDoS en `content_guard._normalize()` — trunca texto masivo antes de aplicar regex. Opera silenciosamente (log warning). No es límite de API. | Domain interno |
| `CHUNK_SIZE` | 512 chars (~128 tok) | Tamaño de cada chunk al indexar documentos en Qdrant | RAG / Qdrant |
| `CHUNK_OVERLAP` | 50 chars (~12 tok) | Solapamiento entre chunks consecutivos | RAG / Qdrant |
| `TOP_K` | 4 chunks | Chunks recuperados por similitud en cada query RAG (~2 048 chars de contexto total) | RAG |
| `rag_score_threshold` | 0.3 | Score mínimo de similitud para incluir un chunk como contexto | RAG |
| `rate_limit_per_minute` | 30 req/min | Requests por IP/usuario por minuto (middleware global) | Middleware |
| `max_pending_contents` | 5 | Máximo de contenidos en estado `pending` por entidad/categoría | Domain |
| `max_concurrent_llm_calls` | 1 | Semáforo de llamadas simultáneas a Ollama | Engine |
| `access_token_expire_minutes` | 60 min | TTL del JWT de sesión | Auth |
| `embedding_dims` | 384 | Dimensiones del vector de embedding (`paraphrase-multilingual-MiniLM-L12-v2`) | RAG / Qdrant |
| `ModerationLog.snippet` DB | max=200 chars | Fragmento guardado al detectar contenido bloqueado | BD |

---

## 5. ⚠ Conflictos detectados

### CONFLICTO 1 — `ImageGeneration.auto_prompt` DB vs engine
| Capa | Límite | Chars |
|---|---|---|
| Engine (`_truncate_to_tokens`) | 512 tokens | ~2 048 chars |
| **DB model** (`ImageGeneration.auto_prompt`) | **max_length=1 000** | **1 000 chars** |

**Problema:** el engine puede producir un `auto_prompt` de hasta ~2 048 chars, pero la columna de BD solo acepta 1 000. Si el `auto_prompt` supera 1 000 chars, falla al persistir.

**Solución:** actualizar `ImageGeneration.auto_prompt` en el DB model a `max_length=2000` y generar migración.

---

### CONFLICTO 2 — `ImageGeneration.final_prompt` DB vs schema
| Capa | Límite | Chars |
|---|---|---|
| Schema Pydantic (`GenerateImagesRequest.final_prompt`) | max_length=2 000 | 2 000 chars |
| **DB model** (`ImageGeneration.final_prompt`) | **max_length=1 000** | **1 000 chars** |

**Problema:** Pydantic acepta hasta 2 000 chars, pero la columna de BD solo guarda 1 000. Un `final_prompt` entre 1 001–2 000 chars pasa la validación HTTP pero falla al persistir en BD.

**Solución:** actualizar `ImageGeneration.final_prompt` en el DB model a `max_length=2000` y generar migración.

---

## 6. Resumen de consistencia por flujo

| Flujo | Input validado | Output acotado | BD consistente | Estado |
|---|---|---|---|---|
| RAG query | ✅ min=10, max=2 000 chars | ✅ MAX_TOKENS=2 000 tok | ✅ query max=2 000, raw_content max=10 000 | ✅ OK |
| Generación contenido | ✅ min=10, max=2 000 chars | ✅ MAX_TOKENS=2 000 tok | ✅ content max=10 000 | ✅ OK |
| Generación imagen — `auto_prompt` | ✅ engine trunca a 512 tok | ✅ ~2 048 chars max | ⚠ DB solo 1 000 chars | ⚠ CONFLICTO |
| Generación imagen — `final_prompt` | ✅ min=10, max=2 000 chars | — (va directo a ComfyUI) | ⚠ DB solo 1 000 chars | ⚠ CONFLICTO |
| Edición contenido | ✅ min=1, max=10 000 chars | — (texto de usuario) | ✅ content max=10 000 | ✅ OK |
| Perfil usuario | ✅ display_name 100, bio 500 | — | ✅ DB iguales | ✅ OK |
| Upload documento | ✅ max 50 MB, max 100 páginas | — | ✅ raw_text TEXT sin límite | ✅ OK |
| Guardrails contenido | ✅ `_BLOCKED_PATTERNS` en input | ✅ `_OUTPUT_BLOCKED_PATTERNS` en output | — | ✅ OK |
