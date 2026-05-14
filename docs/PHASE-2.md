# Fase 2 — Comparativa de Modelos

**Fecha:** 2026-05-14  
**Rama:** `feature/model-harness`  
**Objetivo:** Determinar qué modelo local produce la mejor narrativa por categoría, generar un reporte estructurado de resultados, y preparar el diseño del futuro switch per-categoría en el backend.

---

## Estado inicial heredado de Fase 1

El harness de evaluación está completamente operativo:

| Componente | Estado |
|---|---|
| `runner.py` | Acepta cualquier modelo y etiqueta de versión |
| `judge.py` | gemma2:9b como juez, fallback configurable |
| `compare.py` | Comparativa entre dos runs |
| 10 test cases YAML | Cubre backstory / ext_desc / scene / chapter en contextos rich / sparse / irrelevant |
| Baseline llama3.2 (refactored_v2) | Ya evaluado con gemma2 — D1=2.50 D2=2.00 D3=2.80 D4=2.00 |

Lo que falta: correr los mismos test cases contra otros modelos, agregar un script de reporte multi-modelo y diseñar el feature de switch.

---

## Estrategia de comparativa

### Principio

Mismos 10 test cases — mismo contexto simulado — mismos prompts (refactored_v2) — mismo juez (gemma2:9b) — temperatura 0.7.

La única variable que cambia entre corridas es el modelo generador. Esto garantiza que los deltas de score son atribuibles al modelo, no a ningún otro factor.

### Modelos candidatos

| Modelo | Tamaño | `ollama pull` | Instalado | Recomendación |
|---|---|---|---|---|
| `llama3.2:latest` | 3B | — | ✅ | Baseline (ya evaluado) |
| `llama3.1:8b` | 8B | `ollama pull llama3.1` | — | **Prioritario** — misma familia que el baseline pero 2.5× más parámetros; el candidato más directo para ganar en `chapter` donde llama3.2 trunca |
| `gemma2:9b` | 9B | — | ✅ | **Prioritario** — ya instalado; distinto linaje; fuerte instruction-following; resultados fiables como juez sugieren buena comprensión de las dimensiones evaluadas |
| `qwen2.5:7b` | 7B | `ollama pull qwen2.5` | — | **Secundario** — Qwen 2.5 (sin thinking mode, a diferencia de qwen3.5); excelente soporte multilingüe español; buen candidato para backstory y extended_description |
| `mistral:7b-instruct` | 7B | `ollama pull mistral` | — | **Secundario** — históricamente fuerte en instruction-following estructurado; punto de referencia clásico de la comunidad |

> **Por qué no qwen3.5**: su thinking mode genera bloques `<think>...</think>` en el output que contaminan el texto narrativo. Las corridas de Phase 1 como juez mostraron 40% de fallos de formato. Como generador el problema es distinto (tokens desperdiciados en metacognición en lugar de narrativa). No es candidato para esta fase.

### Corridas planificadas

| Run ID | Modelo | Prompt version | Temp | Casos |
|---|---|---|---|---|
| `baseline` | llama3.2 | refactored_v2 | 0.7 | ✅ ya existe |
| `run-llama31` | llama3.1:8b | refactored_v2 | 0.7 | pendiente |
| `run-gemma2` | gemma2:9b | refactored_v2 | 0.7 | pendiente |
| `run-qwen25` | qwen2.5:7b | refactored_v2 | 0.7 | pendiente |
| `run-mistral` | mistral:7b-instruct | refactored_v2 | 0.7 | pendiente |

**Tiempo estimado total:** ~60 min de generación (10 casos × ~30-60s × 4 modelos) + ~15 min de evaluación con gemma2 (40 casos × ~10s).

---

## Juez: mantener gemma2:9b

**Veredicto: no cambiar.**

| Criterio | gemma2:9b |
|---|---|
| Tasa de éxito JSON en Phase 1 | 10/10 (100%) |
| Evaluaciones realizadas | 20 (baseline + refactored_v2) |
| Riesgo de auto-evaluación | Bajo (distinto linaje que los modelos a evaluar) |
| Comparabilidad con Phase 1 | Total — mismo juez en ambas fases |

Cambiar el juez entre fases invalidaría la comparación con el baseline de Phase 1. gemma2 ya demostró fiabilidad y calibración consistente.

---

## Nuevo entregable: `reporter.py`

Script que toma N directorios de runs ya evaluados y genera un reporte markdown con la comparativa completa.

### Interfaz

```bash
# Desde backend/ con el venv activo
python evaluations/prompt_harness/reporter.py \
  --runs "2026-05-13_23-17_llama3.2_refactored_v2_0.7" \
          "FECHA_llama3.1_refactored_v2_0.7" \
          "FECHA_gemma2_refactored_v2_0.7" \
          "FECHA_qwen2.5_refactored_v2_0.7" \
  --output docs/phase2-model-comparison.md \
  --title "Phase 2 — Comparativa de Modelos"
```

### Estructura del reporte generado

```markdown
# Phase 2 — Comparativa de Modelos
**Fecha:** ...  **Juez:** gemma2:9b  **Temperatura:** 0.7  **Prompts:** refactored_v2

## Resumen ejecutivo
[Modelo ganador overall y recomendación por categoría en 3-5 líneas]

## Ranking global (promedio D1-D4)

| Modelo       | D1   | D2   | D3   | D4   | Promedio |
|---|---|---|---|---|---|
| llama3.1:8b  | X.XX | X.XX | X.XX | X.XX | **X.XX** |
| gemma2:9b    | X.XX | ...  |      |      |          |
| ...          |      |      |      |      |          |
| llama3.2:3b  |      |      |      |      |          |

## D3 por categoría (cumplimiento de categoría)

| Categoría            | llama3.2 | llama3.1 | gemma2 | qwen2.5 | mistral | Mejor modelo |
|---|---|---|---|---|---|---|
| backstory            | 2.33     | X.XX     | X.XX   | X.XX    | X.XX    | **?**        |
| chapter              | 3.00     | X.XX     | X.XX   | X.XX    | X.XX    | **?**        |
| extended_description | 3.00     | X.XX     | X.XX   | X.XX    | X.XX    | **?**        |
| scene                | 2.50     | X.XX     | X.XX   | X.XX    | X.XX    | **?**        |

## Tiempo de respuesta promedio (segundos)

| Modelo      | Promedio | Mín  | Máx  |
|---|---|---|---|
| llama3.2:3b | X.X      | X.X  | X.X  |
| ...         |          |      |      |

## Scores por caso (TC-01 … TC-10)
[Tabla por modelo mostrando D1/D2/D3/D4 por TC]

## Recomendación de modelo por categoría

| Categoría | Modelo recomendado | Delta vs baseline | Justificación |
|---|---|---|---|
| backstory | ? | +X.XX | ... |
| chapter   | ? | +X.XX | ... |
| ...       |   |       |     |

## Criterio de switch aplicado
Umbral: diferencia >= 0.5 puntos en promedio de categoría para justificar switch.
[Lista de categorías donde se aplica el switch]
```

### Criterio de decisión para switch por categoría

Si un modelo supera al baseline (llama3.2:3b) en **≥ 0.5 puntos** en el promedio de una categoría específica → esa categoría es candidata al switch. Si la diferencia es < 0.5 puntos → mantener el modelo actual no justifica la complejidad adicional.

---

## Feature: Per-Query Model Selection

### Contexto y decisión de diseño

Los datos de Phase 2 muestran que `mistral` supera al baseline solo en `scene` (+0.50, exactamente en el umbral). Un switch automático por categoría configurable via `.env` sería poco visible para el usuario y no le daría control real.

**Enfoque adoptado:** el usuario selecciona el modelo activamente antes de generar cada draft. Si el resultado no le convence, puede generar otro draft con un modelo distinto y confirmar el mejor. Esto encaja naturalmente con el sistema de drafts ya existente.

Sin recomendaciones hardcodeadas en el código: la lista viene de Ollama en tiempo real y el usuario decide basándose en sus propios criterios.

---

### Flujo de usuario

```
[Usuario abre panel de generación]
    ↓
Selector de modelo (carga desde GET /api/v1/models)
    ↓ elige "mistral"
[Genera draft]  ←  llama rag_pipeline con model="mistral"
    ↓
Draft creado — muestra badge "Generado con: mistral"
    ↓ (no le convence)
[Genera otro draft]  ←  elige "llama3.2"
    ↓
Dos drafts pendientes → confirma el mejor
```

---

### Plan de implementación

#### Paso B1 — Backend: endpoint de modelos disponibles

**Archivo nuevo:** `app/api/routes/models/models.py`

- `GET /api/v1/models` — consulta `{ollama_base_url}/api/tags` y retorna la lista de modelos instalados localmente
- Si Ollama no responde → 503 con mensaje en español
- Sin lógica de recomendaciones: devuelve nombre, tamaño, y si es el modelo por defecto

```python
class ModelInfo(BaseModel):
    name: str
    size: int           # bytes, para info del usuario
    is_default: bool    # True si coincide con settings.ollama_model
```

Registrar el router en `app/main.py` bajo `/api/v1/models`.

---

#### Paso B2 — Backend: factory LLM con caché

**Archivo:** `app/engine/llm.py`

```python
import functools

@functools.lru_cache(maxsize=8)
def get_llm(model: str) -> OllamaLLM:
    return OllamaLLM(
        model=model,
        base_url=settings.ollama_base_url,
        temperature=settings.temperature,
        num_predict=settings.max_tokens,
    )
```

`OllamaLLM` es stateless — el caché evita instanciar el mismo objeto N veces sin beneficio. El `llm` global existente se mantiene como fallback para el pipeline RAG libre.

---

#### Paso B3 — Backend: propagar `model` por la cadena de llamadas

Cambios en cascada, todos pequeños:

| Archivo | Cambio |
|---|---|
| `models/schemas/entity_content.py` | `GenerateContentRequest` → añadir `model: str \| None = None` |
| `engine/rag_pipeline.py` | `invoke_generation_pipeline` acepta `model: str \| None`; si hay modelo → crea chain con `get_llm(model)`, si no → usa `generation_chain` global |
| `services/entity/generation_service.py` | `generate()` acepta y propaga `model` |
| `api/routes/entities/content.py` | pasa `request.model` a `generation_service.generate()` |

---

#### Paso B4 — Backend: registrar modelo usado en DB

**Archivo:** `app/models/db/generated_text.py`

```python
model_used: str = Field(default=settings.ollama_model, max_length=100)
```

- `generation_service.generate()` escribe `model_used = model or settings.ollama_model` al crear el `GeneratedText`
- `EntityContentResponse` añade `model_used: str | None` para que el frontend lo muestre
- **Alembic migration** para la columna (nullable con valor por defecto para registros existentes)

---

#### Paso F1 — Frontend: API method

**Archivo nuevo:** `src/api/endpoints/models.ts`

```typescript
export async function getModels(): Promise<ModelInfo[]>
```

---

#### Paso F2 — Frontend: componente `ModelSelector`

**Archivo nuevo:** `src/components/ModelSelector.tsx`

- Dropdown que carga `/api/v1/models` al montarse
- Muestra nombre del modelo; marca el modelo por defecto
- Persiste la última selección en `localStorage` (key: `lm_selected_model`)
- Si la carga falla → oculta el selector sin bloquear la generación (usa el modelo por defecto)

---

#### Paso F3 — Frontend: integración en generación y cards

| Archivo | Cambio |
|---|---|
| `EntityContentsPanel.tsx` | Integra `ModelSelector`; pasa `model` seleccionado al llamar `generateContent()` |
| `ContentCard.tsx` | Muestra badge pequeño con `model_used` en drafts pendientes |

---

### Scope total

| Capa | Archivos nuevos | Archivos modificados |
|---|:---:|:---:|
| Backend | 2 (`models.py`, migración Alembic) | 5 |
| Frontend | 2 (`models.ts`, `ModelSelector.tsx`) | 2 |

**Sin cambios en:** pipeline RAG libre (`rag_query.py`), sistema de confirmación de drafts, estructura de colecciones.

---

## Orden de trabajo

### Comparativa de modelos (completado ✅)

| Paso | Actividad | Estado |
|---|---|---|
| 1 | `ollama pull llama3.1` + `ollama pull qwen2.5` + `ollama pull mistral` | ✅ |
| 2 | Ejecutar runner.py para cada modelo nuevo (3 runs) | ✅ |
| 3 | Ejecutar judge.py con gemma2 en cada run nuevo (3 evals) | ✅ |
| 4 | Implementar `reporter.py` | ✅ |
| 5 | Generar reporte con los 4 modelos → `docs/phase2-model-comparison.md` | ✅ |
| 6 | Decisión: solo `scene` supera umbral (+0.50, mistral) | ✅ |

### Feature per-query model selection (pendiente)

| Paso | Actividad | Prerequisito |
|---|---|---|
| B1 | `GET /api/v1/models` — endpoint lista modelos Ollama | — |
| B2 | `get_llm(model)` factory con `lru_cache` en `llm.py` | — |
| B3 | Propagar `model` por la cadena: schema → service → pipeline | B2 |
| B4 | Columna `model_used` en `GeneratedText` + migración Alembic | — |
| F1 | `getModels()` en `api/endpoints/models.ts` | B1 |
| F2 | Componente `ModelSelector` con localStorage | F1 |
| F3 | Integrar `ModelSelector` en panel + badge en `ContentCard` | F2, B3, B4 |
| T1 | Actualizar tests afectados por los cambios de backend | B1–B4 |
| M | Merge `feature/model-harness` → `dev` | Todo |

---

## Entregables

| Entregable | Descripción | Estado |
|---|---|---|
| 3 runs de generación | llama3.1:8b, qwen2.5:7b, mistral contra los 10 TCs | ✅ |
| 3 evals con gemma2 | Scores D1-D4 para cada run nuevo | ✅ |
| `reporter.py` | Script que genera reporte markdown multi-modelo | ✅ |
| `docs/phase2-model-comparison.md` | Reporte final con ranking y recomendaciones | ✅ |
| `GET /api/v1/models` | Endpoint que lista modelos Ollama instalados | pendiente |
| Per-query model selection | UI + backend para elegir modelo por generación | pendiente |
| `model_used` en drafts | Trazabilidad del modelo por draft generado | pendiente |

---

## Lo que este plan NO incluye

- **Evaluación de embeddings o recuperación Qdrant:** el problema puede estar en la recuperación, no en la generación. Eso es una fase separada.
- **Temperatura como variable:** phase 2 usa 0.7 fija. Una fase futura podría explorar 0.5 vs 0.7 vs 0.9 en chapter y scene.
- **Integración en CI/CD:** el harness sigue siendo un herramienta offline manual.
- **Modelos mayores de 14B:** fuera del rango realista para ejecución local sin GPU dedicada de alta memoria.
- **API externa (Claude, GPT):** requeriría gestión de costes y claves; queda como opción futura documentada en PHASE-1-RESULTADOS.md.
