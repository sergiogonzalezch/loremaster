# Plan: Análisis y recomendación — Token usage en respuestas de generación

## Contexto

Los endpoints de generación (`/generate/text` y `/entities/{id}/generate`) llaman a Ollama vía LangChain y devuelven el texto generado. La pregunta es si conviene incluir metadatos de uso de tokens (tokens usados en el prompt, tokens generados, total) en la respuesta, como base para un futuro feature de tracking de uso y quotas.

---

## Diagnóstico técnico

### Estado actual de la cadena LLM

```
# app/core/llm_client.py
chain = _PROMPT | _llm | StrOutputParser()
```

El problema está en `StrOutputParser()`: convierte la salida de `OllamaLLM` a `str` puro, descartando **todos los metadatos** de la respuesta, incluidos los tokens.

```python
# app/core/rag_generate.py
answer = chain.invoke({"context": context, "query": query})
# → devuelve str, sin metadatos
```

### Qué expone Ollama nativamente

Ollama devuelve en su API REST un JSON completo con contadores de tokens por cada inferencia:

```json
{
  "response": "El texto generado...",
  "prompt_eval_count": 512,
  "eval_count": 350,
  "eval_duration": 4200000000,
  "total_duration": 4800000000,
  "load_duration": 200000000
}
```

LangChain's `OllamaLLM.generate()` expone estos datos en `LLMResult.generations[0][0].generation_info`. Actualmente se pierden porque el chain usa `StrOutputParser`.

### Cómo recuperarlos (sin romper lo existente)

En lugar de `chain.invoke()`, llamar a `_llm.generate()` directamente desde `rag_generate.py` tras formatear el prompt:

```python
from app.core.llm_client import _PROMPT, _llm

formatted = _PROMPT.format(context=context, query=query)
result = _llm.generate([formatted])

answer = result.generations[0][0].text
info = result.generations[0][0].generation_info or {}
prompt_tokens     = info.get("prompt_eval_count", 0)
completion_tokens = info.get("eval_count", 0)
total_tokens      = prompt_tokens + completion_tokens
```

> **Riesgo menor:** `generation_info` puede ser `None` en versiones antiguas de Ollama o si la conexión falla. Defendible con `or {}` y defaults a 0.

---

## ¿Conviene incluirlo en la respuesta? — Recomendación

**Sí, con un alcance mínimo en esta fase.** Razones:

1. **Coste de implementación bajo**: el cambio de `chain.invoke()` → `_llm.generate()` es local a `rag_generate.py`. El resto de la arquitectura no cambia.
2. **Valor inmediato**: el frontend o el equipo puede empezar a observar cuántos tokens consumen las queries reales sin esperar al feature completo.
3. **Fundamento necesario para el feature de quotas**: sin capturar los tokens ahora, el feature futuro de "tokens sobrantes" requeriría instrumentación retroactiva o estimaciones. Capturarlos desde el principio da datos reales acumulables.
4. **Ollama es self-hosted**, no hay coste económico directo por token, pero el tracking sigue siendo útil para:
   - Observabilidad (Prometheus/Grafana ya están en `docker-compose.yml`)
   - Detectar prompts descontrolados (context window overflow)
   - Planificación de hardware y capacidad

---

## Propuesta de respuesta enriquecida

### `POST /collections/{id}/generate/text`

```json
{
  "query":         "¿Quién es el rey de Gondor?",
  "answer":        "Aragorn, hijo de Arathorn...",
  "sources_count": 4,
  "token_usage": {
    "prompt_tokens":     512,
    "completion_tokens": 350,
    "total_tokens":      862
  }
}
```

### `POST /collections/{id}/entities/{id}/generate` (draft)

```json
{
  "id":            "a3f1...",
  "entity_id":     "b7e2...",
  "collection_id": "c9d4...",
  "query":         "Describe los orígenes",
  "content":       "Aragorn nació en...",
  "sources_count": 3,
  "status":        "pending",
  "created_at":    "2026-04-21T10:30:00Z",
  "confirmed_at":  null,
  "updated_at":    null,
  "token_usage": {
    "prompt_tokens":     480,
    "completion_tokens": 290,
    "total_tokens":      770
  }
}
```

---

## Alcance recomendado (mínimo viable, YAGNI)

| Capa | Cambio | ¿Persistir en DB? |
|---|---|---|
| `app/core/rag_generate.py` | Cambiar `chain.invoke()` por `_llm.generate()`, retornar `(answer, sources_count, token_usage)` | No |
| `app/models/generate.py` | Añadir clase `TokenUsage` + campo `token_usage` a `GenerateTextResponse` | No (sin tabla) |
| `app/models/entity_text_draft.py` | Añadir campo `token_usage` a `EntityTextDraftResponse` (no en la tabla) | No en esta fase |
| `app/services/generate_service.py` | Propagar el nuevo retorno de `generate_rag_response` | No |
| `app/services/entity_text_draft_service.py` | Ídem | No |

> **¿Por qué no persistir en DB ahora?** Siguiendo YAGNI: almacenar tokens por draft requiere una migración de Alembic y columnas nuevas en `entity_text_drafts`. Tiene sentido diferirlo hasta que el feature de quota/tracking sea un requerimiento concreto. Por ahora los tokens se devuelven en la respuesta para que el consumidor los pueda usar o ignorar.

---

## Archivos a modificar (cuando se apruebe implementar)

| Archivo | Cambio |
|---|---|
| `app/core/rag_generate.py` | Reemplazar `chain.invoke()` por `_llm.generate()`, retornar `(str, int, dict)` |
| `app/core/llm_client.py` | Exportar `_PROMPT` y `_llm` además de `chain` (o exponer función helper) |
| `app/models/generate.py` | `TokenUsage(BaseModel)` + `token_usage: TokenUsage` en `GenerateTextResponse` |
| `app/models/entity_text_draft.py` | `token_usage: TokenUsage` en `EntityTextDraftResponse` |
| `app/services/generate_service.py` | Adaptar para propagar `token_usage` |
| `app/services/entity_text_draft_service.py` | Adaptar `generate_draft_service` para propagar `token_usage` |
| `tests/test_generate.py` | Verificar presencia de `token_usage` en respuesta |
| `tests/test_entity_drafts.py` | Verificar presencia de `token_usage` en draft generado |

---

## Consideración futura — Feature completo de quota/tracking

Si en el futuro se quiere tracking de consumo acumulado y quotas:

1. **Columnas nuevas en `entity_text_drafts`**: `prompt_tokens INT`, `completion_tokens INT`
2. **Tabla nueva `token_usage_log`** (opcional): para registrar cada llamada con `collection_id`, `timestamp`, `prompt_tokens`, `completion_tokens`
3. **Endpoint de resumen**: `GET /collections/{id}/usage` → tokens totales usados, media por query, etc.
4. **Integración con Prometheus**: métricas `loremaster_tokens_total{type="prompt|completion", collection_id="..."}` aprovechando el `prometheus` ya en `docker-compose.yml`

---

## Verificación (cuando se implemente)

1. `make test` — todos los tests pasan
2. `POST /generate/text` → respuesta incluye `token_usage.prompt_tokens > 0`
3. `POST /entities/{id}/generate` → draft incluye `token_usage.total_tokens > 0`
4. Ollama down → `token_usage` con valores `0` (degraded gracefully, no error)