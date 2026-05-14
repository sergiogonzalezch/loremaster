# Prompt Builder Fix — Consolidación de llamadas LLM

**Fecha:** 2026-05-14
**Branch:** `feature/model-harness`
**Commit:** `89859b6`
**Archivos modificados:**
- `backend/app/engine/image_prompt_builder.py`
- `backend/app/domain/image_prompt_rules.py`

---

## Contexto

El `image_prompt_builder` construye prompts visuales a partir del contenido confirmado de una entidad para enviárselos a modelos de imagen (Flux, Stable Diffusion, ComfyUI). El prompt resultante es una lista comma-separated de atributos visuales en inglés.

---

## Problema: dos llamadas LLM secuenciales bajo el mismo semáforo

El flujo anterior en `_extract_with_llm()` hacía **dos llamadas** al LLM dentro de un único bloque `with _llm_semaphore`:

```
with _llm_semaphore:
    # Llamada 1 — extraer el tipo específico
    tipo_result = chain.invoke(TYPE_EXTRACT_PROMPT + content)
    tipo_especifico = tipo_result.strip().lower()   # → "human", "alien", "dragon"...

    # Llamada 2 — extraer atributos visuales
    result = chain.invoke(llm_instruction + content + ATTRIBUTE_EXTRACT_SUFFIX)
```

El semáforo (`max_concurrent_llm_calls = 1`) bloqueaba otras generaciones durante el **doble del tiempo** necesario. Además, el ensamblado final requería combinar manualmente el tipo extraído con los atributos:

```python
prefix = f"{tipo_especifico}, "
prompt = ", ".join([prefix, attributes, QUALITY_SUFFIX])
```

---

## Solución: prompt combinado en una sola llamada

Se reemplazaron las dos llamadas por una instrucción unificada que pide al LLM la salida en el formato final directamente usable por el modelo de imagen:

**Formato de salida esperado:**
```
human, tall, dark hooded cloak, silver eyes, weathered skin, iron pauldrons
```

El tipo específico va como **primer token** (convención de Flux/SD para el sujeto), seguido de todos los atributos visuales. El `QUALITY_SUFFIX` se concatena después en `build_visual_prompt()`.

### Ejemplo de prompt enviado al LLM

```
From the following text, extract the specific type of character and ALL visual attributes mentioned.
Output as a single comma-separated list: start with the specific type (human, alien, robot, android,
cyborg, demon, angel, beast, mythical creature), then ALL visual details — colors, materials, body
shapes, textures, clothing, accessories, equipment, marks, distinctive details, facial expressions,
posture, physical conditions, items carried, surrounding environment mentioned.
IGNORE: narrative, motivations, history, names.
ENGLISH ONLY. No explanation, no sentences, no extra lines.
Example: human, tall, dark hooded cloak, silver eyes, weathered skin

TEXT:
---
{content_text}
---
```

### Nuevo flujo simplificado

```
build_visual_prompt()
  └── _extract_with_llm()
        └── with _llm_semaphore:
              └── LLM call única → "human, tall, dark hooded cloak, silver eyes..."
        └── _truncate_to_tokens(result, available)
  └── prompt = f"{attributes}, {QUALITY_SUFFIX}"
```

---

## Cambios en `image_prompt_rules.py`

| Eliminado | Motivo |
|---|---|
| `ENGLISH_RESPONSE_INSTRUCTION` | Integrado en el prompt combinado (`ENGLISH ONLY.`) |
| `_TYPE_EXTRACT_SUFFIX` | Solo usado en `_TYPE_EXTRACT_PROMPT`, que se elimina |
| `_ATTRIBUTE_EXTRACT_SUFFIX` | Integrado en `build_combined_prompt()` |
| `_BASE_EXTRACT` | Integrado |
| `_FORMAT_ATTRS` | Integrado |
| `_TYPE_LABEL_BY_ENTITY` | Integrado en `_COMBINED_TYPE_OPTIONS` |
| `_TYPE_EXTRACT_PROMPT` | Reemplazado por el prompt combinado |
| `_PREFIX_BY_CATEGORY` | Integrado en `build_combined_prompt()` |
| `_build_instruction()` | Reemplazado por `build_combined_prompt()` |
| `_llm_instruction_by_entity_category` | Reemplazado por `build_combined_prompt()` |

| Añadido | Descripción |
|---|---|
| `_COMBINED_TYPE_OPTIONS` | Opciones de tipo específico por `EntityType`, usadas en el prompt combinado |
| `build_combined_prompt(entity_type, category, content_text)` | Construye el prompt único que produce la salida final para el modelo de imagen |

`_IGNORA_BY_CATEGORY`, `_ENTITY_NAME_EN` y `_ATTRIBUTOS_BY_ENTITY_CATEGORY` se conservan sin cambios — siguen siendo la fuente de verdad de qué ignorar y qué atributos extraer por combinación entidad/categoría.

---

## Cambios en `image_prompt_builder.py`

- `_extract_with_llm()` pasa de retornar `tuple[str, str]` (tipo, atributos) a retornar `str` (lista comma-separated lista para usar).
- `build_visual_prompt()` elimina el ensamblado manual de prefix + attributes + suffix; ahora simplemente:
  ```python
  prompt = f"{attributes}, {QUALITY_SUFFIX}"
  ```
- La API pública (`build_visual_prompt`) no cambia: mismos parámetros, mismo dict de retorno `{prompt, token_count, category}`.

---

## Impacto en fases anteriores

| Fase | Impacto |
|---|---|
| **PHASE-1** (mejora de prompts RAG) | Ninguno. Afecta `prompt_templates.py` / `rag_pipeline.py`, sistemas completamente separados. |
| **PHASE-2** (per-query model selection) | Ninguno. El image prompt builder usa el LLM global (`app.engine.llm.llm`), no el factory `get_llm(model)`. |

---

## Tests

- `test_prompt_builder.py` — 7/7 ✅ (PB-01 a PB-06 + `test_estimate_tokens`)
- `test_image_generation_service.py` — 13/13 ✅ (IG-01 a IG-13)
- Suite completa backend — 183/183 ✅
- `ruff check app` — sin errores ✅
