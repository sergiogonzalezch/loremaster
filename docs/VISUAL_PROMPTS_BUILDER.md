# Visual Prompts Builder - Documentación Técnica

Sistema para construir prompts visuales para generación de imágenes a partir de contenido confirmado de entidades.

## Arquitectura General

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FLUJO COMPLETO                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  EntityContent (confirmado)                                        │
│         │                                                          │
│         ▼                                                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              image_pipeline.py                               │   │
│  │                    invoke_prompt_extraction()                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│         │                                                          │
│    ┌────┴────┐                                                     │
│    │ 2 LLM   │                                                     │
│    │ calls   │                                                     │
│    └────┬────┘                                                     │
│         │                                                          │
│    ┌────┴──────────────────────┐                                  │
│    ▼                             ▼                                  │
│ ┌──────────────┐      ┌──────────────────────┐                   │
│ │ 1st call:    │      │ 2nd call:            │                   │
│ │ Extract type │      │ Extract visual       │                   │
│ │ (robot, etc) │      │ attributes           │                   │
│ └──────────────┘      └──────────────────────┘                   │
│         │                         │                                 │
│         └────────┬────────────────┘                                 │
│                  ▼                                                │
│         (tipo_especifico, atributos)                             │
│                  │                                                │
│                  ▼                                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              prompt_builder.py                              │   │
│  │                 build_visual_prompt()                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                  │                                                │
│                  ▼                                                │
│    "robot, metal plateado, cuerpo..., high quality..."            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Archivos del Sistema

| Archivo | Propósito | Líneas |
|---------|-----------|--------|
| `engine/image_pipeline.py` | Pipeline principal - 2 llamadas LLM | ~120 |
| `domain/image_prompt_rules.py` | Instrucciones LLM por entity+category | ~180 |
| `domain/prompt_builder.py` | Ensambla el prompt final | ~120 |
| `services/image_generation_service.py` | Orquestación del servicio | ~420 |

## Archivos Eliminados/Obsoletos

| Archivo | Razón |
|---------|-------|
| `domain/prompt_extraction_rules.py` | Renombrado a `image_prompt_rules.py` |
| Funciones en `rag_pipeline.py` (`invoke_prompt_extraction_pipeline`) | Movidas a `image_pipeline.py` |

---

## 1. image_pipeline.py

### Función Principal

```python
def invoke_prompt_extraction(
    content_text: str,
    entity_type: EntityType,
    category: ContentCategory,
    target_tokens: int = 150,
) -> tuple[str, str]:
    """Retorna (tipo_especifico, atributos_visuales)"""
```

### Flujo

1. **Primera llamada LLM**: Extrae el tipo específico de la entidad
   - Prompt: `_TYPE_EXTRACT_PROMPT[entity_type]`
   - Ejemplo: "Del siguiente texto, identifica el tipo específico de ser..."
   - Output: "robot", "dragón", "espada", etc.

2. **Segunda llamada LLM**: Extrae atributos visuales
   - Prompt: `_llm_instruction_by_entity_category[(entity_type, category)]`
   - Ejemplo: "extrae TODOS los atributos visuales..."
   - Output: "metal plateado, cuerpo cilíndrico, pantalla LCD..."

3. Retorna tupla `(tipo_especifico, atributos)`

### Funciones Auxiliares

- `_get_generation_chain()`: Lazy initialization del LLM chain
- `_estimate_tokens(text)`: ~4 chars por token
- `_truncate_to_tokens(text, max_tokens)`: Trunca preservando palabras completas

---

## 2. image_prompt_rules.py

### Estructura de Datos

```python
_llm_instruction_by_entity_category = {
    (EntityType.character, ContentCategory.extended_description): "...",
    (EntityType.character, ContentCategory.backstory): "...",
    # ... 20 combinaciones
}
```

### Constantes Principales

| Constante | Descripción |
|-----------|-------------|
| `_BASE_EXTRACT` | "extrae TODOS los atributos visuales..." |
| `_NO_SKIP` | "NO resumas, NO omitas. Cada detalle visual..." |
| `_FORMAT_ATTRS` | "SOLO atributos sueltos, NO frases completas." |
| `_IGNORA_BY_CATEGORY` | Categorías de lo que se ignora por tipo de contenido |
| `_TYPE_EXTRACT_PROMPT` | Instrucciones para extraer tipo específico |
| `_ATRIBUTOS_BY_ENTITY_CATEGORY` | Atributos específicos por combinación |

### Builder Function

```python
def _build_instruction(entity_type: EntityType, category: ContentCategory) -> str:
    """Construye la instrucción LLM dinámicamente"""
```

### Tabla de Combinaciones (20)

| Entity Type | extended_description | backstory | scene | chapter |
|-------------|---------------------|-----------|-------|---------|
| character | ✅ | ✅ | ✅ | ✅ |
| creature | ✅ | ✅ | ✅ | ✅ |
| location | ✅ | ✅ | ✅ | ✅ |
| faction | ✅ | ✅ | ✅ | ✅ |
| item | ✅ | ✅ | ✅ | ✅ |

### Tipo Específico por Entity Type

| Entity Type | Tipos Posibles |
|-------------|----------------|
| character | robot, androide, cyborg, humano, alien, demonio, ángel, bestia... |
| creature | dragón, bestia, espíritu, demonio, ángel, ser mitológico, monstruo... |
| location | ciudad, fortaleza, templo, bosque, montaña, ruina, nave, planeta... |
| faction | reino, clan, hermandad, orden, guild, corporation, religión, movimiento... |
| item | espada, arco, varita, escudo, armadura, relicto, artefacto, joyería... |

---

## 3. prompt_builder.py

### Función Principal

```python
def build_visual_prompt(
    entity_type: EntityType,
    entity_name: str,
    entity_description: str,
    confirmed_content: str,
    category: ContentCategory,
    max_tokens: int = 150,
) -> dict[str, str | int | bool]:
```

### Return Value

```python
{
    "prompt": "robot, metal plateado, cuerpo cilíndrico, ..., high quality...",
    "token_count": 45,
    "truncated": False,
    "source": "llm_extraction",
    "strategy": "llm_extraction",
    "category": "extended_description",
}
```

### Flujo

1. Llama `invoke_prompt_extraction()` → obtiene `(tipo, atributos)`
2. Calcula espacio disponible para atributos (reservando para tipo + suffix)
3. Trunca atributos si es necesario
4. Ensambla: `prefix + attributes + QUALITY_SUFFIX`
5. Retorna diccionario con metadata

### Constantes

```python
_ENTITY_TYPE_VISUAL = {
    EntityType.character: "personaje",
    EntityType.creature: "criatura",
    EntityType.location: "lugar",
    EntityType.faction: "facción",
    EntityType.item: "objeto",
}

QUALITY_SUFFIX = "high quality, masterpiece, sharp focus, professional digital art"
```

---

## 4. image_generation_service.py

### Funciones Principales

| Función | Descripción |
|---------|-------------|
| `build_prompt_service()` | Construye prompt efímero (sin guardar) |
| `generate_images_service()` | Genera imágenes + persiste en DB |
| `get_generation_service()` | Obtiene una generación existente |
| `list_generations_service()` | Lista todas las generaciones de una entidad |
| `delete_image_service()` | Elimina imagen individual (soft delete) |

### build_prompt_service()

```python
def build_prompt_service(
    session: Session,
    entity: Entity,
    content_id: str,
) -> BuildPromptResponse:
    # 1. Valida content_id pertenece al entity y está confirmado
    # 2. Valida categoría soportada (extended_description, backstory, scene, chapter)
    # 3. Llama build_visual_prompt()
    # 4. Retorna respuesta efímera
```

### generate_images_service()

```python
def generate_images_service(
    session: Session,
    entity: Entity,
    content_id: str,
    final_prompt: str,
    batch_size: int,
) -> GenerateImagesResponse:
    # 1. Valida content_id confirmado
    # 2. Genera auto_prompt via build_visual_prompt()
    # 3. Crea ImageGeneration + ImageRecords
    # 4. Si backend == "mock": placeholders
    # 5. Persiste en DB
```

---

## Decisiones de Diseño

### 1. Doble Llamada LLM

**Antes**: Una llamada LLM que a veces incluía el tipo, a veces no (~50%)

**Ahora**: Dos llamadas LLM garantizadas:
- 1ra: Solo tipo específico
- 2da: Solo atributos visuales

**Resultado**: 100% de inclusión del tipo

### 2. Sin Fallback/Template

**Antes**: Código de fallback determinista si LLM fallaba

**Ahora**: Si LLM falla → eleva `RuntimeError`

**Razón**: El usuario prefirió consistencia sobre resiliencia

### 3. Separación de Pipelines

| Pipeline | Archivo | Propósito |
|----------|---------|-----------|
| RAG (texto) | `engine/rag_pipeline.py` | Query + generación de contenido |
| Image | `engine/image_pipeline.py` | Extracción de atributos visuales |

### 4. Prompt Sin Nombre de Entidad

El prompt **NO** incluye el nombre de la entidad (ej: "Aragorn"). Solo incluye:
- Tipo específico (robot, dragón, etc.)
- Atributos visuales del contenido
- Quality suffix

---

## Configuración (config.py)

| Variable | Default | Propósito |
|----------|---------|-----------|
| `image_prompt_tokens` | 150 | Límite de tokens para el prompt |
| `image_backend` | "mock" | Backend de generación (mock/real) |
| `image_width` | 1024 | Ancho de imagen |
| `image_height` | 1024 | Alto de imagen |
| `image_seed_base` | 42 | Semilla base para imágenes |

---

## Errores y Manejo

| Error | Causa | Respuesta |
|-------|-------|-----------|
| `RuntimeError: LLM service unavailable` | Ollama no responde | HTTP 503 |
| `NoContextAvailableError` | Contenido no existe/no confirmado | HTTP 404 |
| `ValueError: Categoría no soportada` | Categoría no es imagen | HTTP 400 |

---

## Historial de Cambios

| Fecha | Cambio |
|-------|--------|
| 2026-05-03 | Separación de image_pipeline de rag_pipeline |
| 2026-05-03 | Eliminación de fallback/template |
| 2026-05-03 | Implementación de doble llamada LLM para tipo |
| 2026-05-03 | Refactor de image_prompt_rules con builder functions |
| 2026-05-03 | Traducción de prompts a inglés para compatibilidad con Flux/Klein |
| 2026-05-03 | Agregada constante ENGLISH_RESPONSE_INSTRUCTION para forzar respuesta en inglés |