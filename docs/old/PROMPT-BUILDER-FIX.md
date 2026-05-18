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

---

# Mejoras Post-Harness — Evaluación comparativa de modelos

**Fecha:** 2026-05-14
**Commit base (snapshot):** ver historial git
**Archivos modificados:**
- `backend/app/core/config/__init__.py`
- `backend/app/engine/image_prompt_builder.py`
- `backend/app/domain/image_prompt_rules.py`

## Contexto

Se ejecutó el `image_prompt_harness` contra los 6 modelos Ollama disponibles con 12 casos de prueba, evaluando dos métricas: **tipo correcto** (primer token) y **en inglés** (sin tokens función en español).

### Resultados del harness

| Modelo | Tipo correcto | En inglés |
|---|---|---|
| mistral:latest | 10/12 (83.3%) | **12/12 (100.0%)** |
| llama3.2:latest | 10/12 (83.3%) | 11/12 (91.7%) |
| qwen2.5:latest | 10/12 (83.3%) | 11/12 (91.7%) |
| gemma2:9b | 10/12 (83.3%) | 11/12 (91.7%) |
| llama3.1:latest | 8/12 (66.7%) | 11/12 (91.7%) |
| qwen3.5:9b | 0/12 (0.0%) | 0/12 (0.0%) — modelo de razonamiento |

`qwen3.5:9b` es incompatible: envuelve su salida en `<think>...</think>` y causa timeouts frecuentes.

### Fallos por causa raíz

| Caso | Causa |
|---|---|
| tc-05 creature/backstory | La categoría `backstory` orienta al modelo hacia contexto narrativo; la instrucción de tipo no era suficientemente explícita. Fallaba en 4/5 modelos. |
| tc-11 item/backstory | `_COMBINED_TYPE_OPTIONS` para item no incluía `orb` ni `sphere`, que sí estaban en `expected_types`. Contradicción de datos. |
| tc-02 character/alien | Solo llama3.2 falla; error de consistencia del modelo, no del prompt. |
| tc-12 character/backstory inglés | Solo llama3.2; se "contagia" del español en backstory. |

---

## Mejora 1 — Modelo independiente para image prompts

### Problema
El builder usaba el global `llm` (instancia del modelo de generación de contenido, `ollama_model`). El modelo elegido para narrativa no es necesariamente el mejor para extracción estructurada en inglés. Acoplar ambas decisiones degrada la calidad del auto prompt cuando el usuario usa modelos como llama3.1.

### Solución
Añadir `image_prompt_model` a Settings (por defecto `mistral:latest`, el único con 100% inglés). El builder usa `get_llm(settings.image_prompt_model)` — la fábrica ya existente de PHASE-2 — sin duplicar ninguna lógica.

```python
# config/__init__.py — añadido en sección Image generation
image_prompt_model: str = "mistral:latest"

# image_prompt_builder.py — antes
from app.engine.llm import llm
_generation_chain = llm | StrOutputParser()

# image_prompt_builder.py — después
from app.engine.llm import get_llm
_generation_chain = get_llm(settings.image_prompt_model) | StrOutputParser()
```

**Impacto:** El modelo de generación de contenido (`ollama_model`) y el de extracción visual (`image_prompt_model`) son configurables independientemente. Sin cambio de API pública.

---

## Mejora 2 — Corrección de datos en opciones de tipo para item

### Problema
`_COMBINED_TYPE_OPTIONS[EntityType.item]` no incluía `orb` ni `sphere`. El harness esperaba esos valores en tc-11 pero el prompt los excluía implícitamente al listar solo las opciones válidas.

### Solución
```python
# antes
EntityType.item: "sword, bow, wand, shield, armor, relic, artifact, jewelry, amulet, potion",

# después
EntityType.item: "sword, bow, wand, shield, armor, relic, artifact, orb, sphere, jewelry, amulet, potion",
```

---

## Mejora 3 — Refuerzo de instrucción de tipo en categoría backstory

### Problema
En backstory, el modelo a veces producía un descriptor visual como primer token en lugar del tipo de entidad. La instrucción `"start with the specific type"` no era suficientemente explícita cuando el texto tenía fuerte carga narrativa.

### Solución
`build_combined_prompt()` añade una línea de refuerzo condicional solo cuando `category == ContentCategory.backstory`:

```
IMPORTANT: The very first item MUST be a type from the list above, even in historical or backstory text.
```

---

## Impacto acumulado en fases anteriores

| Fase | Impacto |
|---|---|
| **PHASE-1** (RAG content generation) | Ninguno. Archivos completamente separados. |
| **PHASE-2** (per-query model selection) | Ninguno. Se reutiliza `get_llm()` sin modificarla. El `chain` global del RAG no cambia. |
