# Visual Prompts Builder - Documentación Técnica

Sistema para construir prompts visuales para generación de imágenes a partir de contenido confirmado de entidades.

## Arquitectura General

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FLUJO COMPLETO                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Frontend: build-prompt endpoint                                    │
│         │                                                          │
│         ▼                                                          │
│  EntityContent (confirmado) ──────┐                                │
│                                    │                                │
│  ┌─────────────────────────────────▼──────────────────────────┐   │
│  │              image_prompt_builder.py                       │   │
│  │                   build_visual_prompt()                      │   │
│  └─────────────────────────────────┬──────────────────────────┘   │
│                                    │                                │
│    ┌──────────────┐      ┌────────┴────────┐      ┌─────────────┐ │
│    │ 1st LLM call │      │ 2nd LLM call    │      │ Assembling  │ │
│    │ Extract type │      │ Extract attrs  │      │ + Truncation│ │
│    └──────┬───────┘      └────────┬────────┘      └──────┬──────┘ │
│           │                        │                      │        │
│           └────────────────────────┼──────────────────────┘        │
│                                    ▼                               │
│                         "robot, silver metal, ...                  │
│                          high quality, masterpiece..."             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Evolución de Archivos

### Before (v1)
```
domain/
├── prompt_builder.py       ← Ensamblaba prompt + truncaba
├── image_prompt_rules.py  ← Instrucciones LLM

engine/
└── image_pipeline.py       ← 2 llamadas LLM (tipo + atributos)
```

### After (v2 - actual)
```
domain/
└── image_prompt_rules.py  ← Instrucciones LLM (sin cambios)

engine/
└── image_prompt_builder.py ← MERGED: pipeline LLM + ensamblado + truncado
```

## Archivos del Sistema (Estado Actual)

| Archivo | Propósito | Estado |
|---------|-----------|--------|
| `engine/image_prompt_builder.py` | Pipeline completo (fusionado) | ✅ Activo |
| `domain/image_prompt_rules.py` | Instrucciones LLM por entity+category | ✅ Activo |
| `services/image_generation_service.py` | Orquestación del servicio | ✅ Activo |

## Archivos Eliminados/Mergedos

| Archivo Original | Destino | Razón |
|-----------------|---------|-------|
| `engine/image_pipeline.py` | → `image_prompt_builder.py` | Fusionado |
| `domain/prompt_builder.py` | → `image_prompt_builder.py` | Fusionado |
| `domain/prompt_extraction_rules.py` | → `image_prompt_rules.py` | Renombrado |

---

## 1. image_prompt_builder.py

### Función Principal

```python
def build_visual_prompt(
    entity_type: EntityType,
    confirmed_content: str,
    category: ContentCategory,
    max_tokens: int = 512,
) -> dict[str, str | int]:
```

**Antes (v1)**:
```python
def build_visual_prompt(
    entity_type: EntityType,
    entity_name: str,              # ⬅️ ELIMINADO
    entity_description: str,       # ⬅️ ELIMINADO
    confirmed_content: str,
    category: ContentCategory,
    max_tokens: int = 150,         # ⬅️ CAMBIADO: 150 → 512
) -> dict[str, str | int | bool]:  # ⬅️ CAMBIADO: sin bool
```

### Return Value

**Antes (v1)**:
```python
{
    "prompt": "...",
    "token_count": 45,
    "truncated": False,      # ⬅️ ELIMINADO
    "source": "llm_extraction",  # ⬅️ ELIMINADO
    "strategy": "llm_extraction", # ⬅️ ELIMINADO
    "category": "extended_description",
}
```

**Después (v2)**:
```python
{
    "prompt": "robot, silver metal, high quality...",
    "token_count": 45,
    "category": "extended_description",
}
```

### Flujo Interno

1. **Primera llamada LLM**: Extrae tipo específico
   - Prompt: `_TYPE_EXTRACT_PROMPT[entity_type]`
   - Output: "robot", "dragon", "sword"

2. **Segunda llamada LLM**: Extrae atributos visuales
   - Prompt: `_llm_instruction_by_entity_category[(entity_type, category)]`
   - Output: "silver metal, cylindrical body, LCD screen"

3. **Ensamblado**: `prefix + attributes + QUALITY_SUFFIX`

4. **Truncado**: Si excede max_tokens, trunca preservando palabras completas

### Constantes Locales (ELIMINADAS)

| Constante | Razón |
|-----------|-------|
| `_ENTITY_TYPE_VISUAL` | No usada, información redundante |

---

## 2. image_prompt_rules.py

### Constantes Principales

| Constante | Descripción |
|-----------|-------------|
| `_BASE_EXTRACT` | "extract ALL visual attributes..." |
| `_NO_SKIP` | "DO NOT summarize, DO NOT skip..." |
| `_FORMAT_ATTRS` | "ONLY loose attributes in ENGLISH..." |
| `_TYPE_EXTRACT_PROMPT` | Instrucciones para extraer tipo específico |
| `_ATTRIBUTOS_BY_ENTITY_CATEGORY` | Atributos por combinación entity+category |
| `_ATTRIBUTE_EXTRACT_SUFFIX` | ⭐ Exportada a image_prompt_builder |

### Tabla de Combinaciones (20)

| Entity Type | extended_description | backstory | scene | chapter |
|-------------|---------------------|-----------|-------|---------|
| character | ✅ | ✅ | ✅ | ✅ |
| creature | ✅ | ✅ | ✅ | ✅ |
| location | ✅ | ✅ | ✅ | ✅ |
| faction | ✅ | ✅ | ✅ | ✅ |
| item | ✅ | ✅ | ✅ | ✅ |

---

## 3. image_generation_service.py

### Cambios en Funciones

#### build_prompt_service()
- **Sin cambios significativos** - llama a `build_visual_prompt()`

#### generate_images_service()
```python
# ANTES: generaba auto_prompt internamente en cada llamada
auto_prompt = build_visual_prompt(...)

# DESDÉS: recibe auto_prompt ya generado (del build-prompt endpoint)
# El backend NO regenera - usa el que le pasa el frontend
auto_prompt: str,  # ⬅️ Del request (pre-generado por backend en build-prompt)
final_prompt: str, # ⬅️ Del request
```

### Validaciones Añadidas
- `content_guard.check_user_input()` para auto_prompt y final_prompt

---

## Flujo de Auto-Prompt

**Antes (v1)**: Backend regeneraba auto_prompt en generate-images
```
Frontend                        Backend
   │                                │
   ├─► build-prompt               │
   │   (genera auto_prompt)        │
   │◄─────────────────────────────┤
   │                                │
   ├─► generate-images ───────────┤
   │   (sin auto_prompt)           │
   │        ┌──► build_visual_prompt() [RE-GENERA]
   │        └──► retorna imágenes
```

**Después (v2)**: Frontend pasa auto_prompt, backend no regenera
```
Frontend                        Backend
   │                                │
   ├─► build-prompt               │
   │   (genera auto_prompt via LLM)│
   │◄─────────────────────────────┤
   │                                │
   ├─► generate-images ───────────┤
   │   (con auto_prompt)           │
   │        └──► retorna imágenes  [NO regenera]
```

---

## Cambios en API

### build-prompt (POST)
```json
// Request (sin cambios)
{
  "content_id": "..."
}

// Response (sin cambios)
{
  "auto_prompt": "...",
  "token_count": 45
}
```

### generate-images (POST)
```json
// ANTES
{
  "content_id": "...",
  "final_prompt": "...",
  "batch_size": 4
}

// DESDÉS (añadido auto_prompt)
{
  "content_id": "...",
  "auto_prompt": "...",      // ⬅️ NUEVO: del frontend
  "final_prompt": "...",
  "batch_size": 4
}
```

---

## Configuración (config.py)

| Variable | Antes | Después | Propósito |
|----------|-------|---------|-----------|
| `image_prompt_tokens` | 150 | 512 | Límite tokens (text encoder limit) |
| `image_backend` | "mock" | "mock" | Backend de generación |
| `image_width` | 1024 | 1024 | Ancho de imagen |
| `image_height` | 1024 | 1024 | Alto de imagen |
| `image_seed_base` | 42 | 42 | Semilla base |

---

## Errores y Manejo

| Error | Causa | Respuesta |
|-------|-------|-----------|
| `RuntimeError: LLM service unavailable` | Ollama no responde | HTTP 503 |
| `NoContextAvailableError` | Contenido no existe/no confirmado | HTTP 404 |
| `ValueError: Categoría no soportada` | Categoría no válida para imágenes | HTTP 400 |
| `ValueError: Input bloqueado` | Prompt falla content_guard | HTTP 422 |

---

## Historial de Cambios

| Fecha | Cambio |
|-------|--------|
| 2026-05-04 | Merge: `image_pipeline.py` + `prompt_builder.py` → `image_prompt_builder.py` |
| 2026-05-04 | Eliminado: `truncated`, `prompt_source`, `entity_name`, `entity_description` |
| 2026-05-04 | Cambiado: max_tokens 150 → 512 |
| 2026-05-04 | Cambiado: auto_prompt se pasa como parámetro (no se regenera en generate-images) |
| 2026-05-04 | Añadido: content_guard para validar prompts |
| 2026-05-03 | Separación de image_pipeline de rag_pipeline |
| 2026-05-03 | Eliminación de fallback/template |
| 2026-05-03 | Implementación de doble llamada LLM para tipo |
| 2026-05-03 | Refactor de image_prompt_rules |