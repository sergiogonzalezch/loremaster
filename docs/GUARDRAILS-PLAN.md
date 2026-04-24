# Plan: Guardrails de contenido en Lore Master

## Contexto

El sistema actualmente tiene cero validación de contenido. Los únicos controles son: tipo MIME (PDF/TXT), tamaño de archivo (50 MB) y longitud mínima de query (5 chars). No hay sistema prompt de seguridad, ni límite máximo en inputs, ni validación de output del LLM.

El modelo local (`llama3.2:latest` vía Ollama) tiene safety training básico pero inferior al de modelos cloud. La protección debe implementarse en capas, sin depender de APIs externas para mantener la arquitectura local-first.

---

## Arquitectura de 3 capas

```
ENTRADA ──► [Capa 1: Input validation] ──► LLM ──► [Capa 3: Output validation] ──► DB
                     │
              [Capa 2: Prompt guardrails]
                  (system prompt)
```

---

## Capa 1 — Validación de entrada (rápida, sin LLM)

### 1a. Límites de longitud en todos los campos de texto libre

Evita ataques de prompt injection por inputs masivos y reduce superficie de ataque.

| Campo | Modelo | Cambio |
|---|---|---|
| `query` (RAG query) | `models/rag_query.py` | `max_length=2000` |
| `query` (generate content) | `models/entity_content.py` | `max_length=2000` |
| `name` (entity) | `models/entities.py` | `max_length=200` |
| `description` (entity) | `models/entities.py` | `max_length=2000` |

### 1b. Módulo `domain/content_guard.py` — Keyword blocklist

Nuevo módulo puro (sin I/O, sin DB). Responsabilidad única: detectar contenido prohibido con regex compiladas.

```python
# app/domain/content_guard.py

def check_user_input(text: str) -> None:
    """Raises ValueError if text contains blocked content."""

def check_document_content(text: str) -> None:
    """Raises ValueError if extracted document text contains blocked content."""
```

La blocklist incluye patrones en español e inglés para las categorías:

- Contenido sexual explícito / NSFW
- Incitación al odio por raza, género, religión, orientación sexual
- Instrucciones para actividades ilegales (síntesis de drogas, armas, etc.)
- Contenido denigrante o de abuso

**Dónde se llama:**

- `services/generation_service.py` → `check_user_input(query)` antes de invocar el LLM
- `services/rag_query_service.py` → `check_user_input(query)` antes de invocar el LLM
- `services/documents_service.py` → `check_document_content(content)` después de `extract_text()`, antes de ingestar en Qdrant

**Respuestas de error:**

- Input del usuario bloqueado → `HTTPException(422, "Contenido no permitido.")`
- Documento bloqueado → `HTTPException(422, "El documento contiene contenido no permitido.")`

---

## Capa 2 — Prompt guardrails (instrucciones de seguridad al LLM)

Esta es la capa de mayor impacto. Se añaden instrucciones de seguridad directamente en los prompts que recibe el modelo.

### 2a. Instrucción de seguridad compartida

Nuevo bloque constante en `domain/prompt_templates.py`:

```python
_SAFETY_INSTRUCTION = (
    "RESTRICCIONES ABSOLUTAS: Bajo ninguna circunstancia generes contenido que incluya "
    "material sexual explícito, instrucciones para actividades ilegales o dañinas, "
    "discurso de odio, acoso o contenido denigrante hacia personas o grupos. "
    "Si la solicitud o el contexto contienen ese tipo de material, responde únicamente: "
    "'No puedo procesar esta solicitud.' y no generes ningún contenido adicional. "
)
```

### 2b. Integración en templates de entidades

El bloque `_SAFETY_INSTRUCTION` se inserta al inicio de cada template en `_TEMPLATES`, antes del preamble narrativo:

```python
ContentCategory.backstory: (
    _SAFETY_INSTRUCTION
    + _PREAMBLE
    + "Genera una historia de fondo para '{entity_name}'..."
    + _SECTIONS
),
```

Se aplica a los 4 templates: `backstory`, `extended_description`, `scene`, `chapter`.

### 2c. Integración en el pipeline RAG genérico

En `engine/llm.py`, el `_PROMPT` (PromptTemplate para el endpoint `/query`) también recibe la instrucción de seguridad al inicio del template string.

> **Nota de evaluación**: llama3.2 respeta instrucciones de sistema en el prompt si están al inicio y son explícitas. La posición al comienzo del template garantiza que se carguen en el contexto antes que cualquier input del usuario. No se necesita cambiar a `ChatOllama` — el enfoque de inyección directa en el template string es suficiente y no requiere refactorizar la cadena LangChain existente.

---

## Capa 3 — Validación de output

Después de que el LLM genera una respuesta, antes de persistirla en DB, se valida que el contenido generado no contenga material prohibido.

### 3a. Función `check_generated_output` en `domain/content_guard.py`

```python
def check_generated_output(text: str) -> None:
    """Raises RuntimeError if LLM output contains blocked content."""
```

Usa los mismos patrones que la blocklist de entrada. Si el output es bloqueado, se lanza `RuntimeError` que el route convierte a `503`, indicando que la generación falló igual que cualquier fallo del LLM.

**Dónde se llama:**

- `services/generation_service.py` → después de `invoke_generation_pipeline()`, antes de crear `GeneratedText` y `EntityContent`
- `services/rag_query_service.py` → después de `invoke_rag_pipeline()`, antes de retornar la respuesta

**Respuesta de error al cliente:** `HTTPException(503, "No fue posible generar el contenido solicitado.")` — mensaje genérico que no revela qué patrón se detectó.

---

## Archivos modificados

| Archivo | Tipo de cambio |
|---|---|
| `app/domain/content_guard.py` | **Nuevo** — módulo puro con blocklist + funciones de check |
| `app/domain/prompt_templates.py` | Añadir `_SAFETY_INSTRUCTION` a todos los templates |
| `app/engine/llm.py` | Añadir `_SAFETY_INSTRUCTION` al `_PROMPT` genérico |
| `app/models/rag_query.py` | `max_length=2000` en `query` |
| `app/models/entity_content.py` | `max_length=2000` en `GenerateContentRequest.query` |
| `app/models/entities.py` | `max_length=200` en `name`, `max_length=2000` en `description` |
| `app/services/generation_service.py` | Llamar a `check_user_input` y `check_generated_output` |
| `app/services/rag_query_service.py` | Llamar a `check_user_input` y `check_generated_output` |
| `app/services/documents_service.py` | Llamar a `check_document_content` tras `extract_text()` |

---

## Evaluación del sistema prompt

| Técnica | Efectividad | Coste | Notas |
|---|---|---|---|
| `_SAFETY_INSTRUCTION` al inicio del prompt | Media-Alta | Cero (tokens extra ~60) | llama3.2 respeta instrucciones explícitas; no infalible |
| Keyword blocklist en input | Alta para ataques directos | Cero (regex CPU) | Fácil de bypassear con paráfrasis |
| Keyword blocklist en output | Media | Cero (regex CPU) | Red de seguridad si el LLM escapa |
| Max length en inputs | Alta contra prompt injection | Cero | Necesario siempre |

**Limitación conocida**: Un usuario determinado puede parafrasear contenido prohibido y esquivar la blocklist. Para un sistema local de worldbuilding colaborativo (no público), este nivel de protección es proporcionado. Si el sistema se expusiera públicamente, la recomendación es añadir un modelo de clasificación dedicado (`llama-guard` vía Ollama) como capa adicional.

---

## Fuera de alcance (fase posterior)

- **API externa de moderación** (OpenAI Moderation, Azure Content Safety) — rompe arquitectura local-first
- **Modelo de clasificación dedicado** (`llama-guard`) — overhead de memoria significativo para uso mono/pequeño equipo
- **Filtrado semántico por embeddings** — complejidad innecesaria para la escala actual
- **Logging de intentos bloqueados** — útil pero pertenece a la fase de observabilidad
