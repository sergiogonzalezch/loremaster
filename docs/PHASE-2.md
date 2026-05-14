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

## Feature futuro: per-category model switch

### Contexto del backend

Actualmente hay un único modelo global:

```
Settings.ollama_model = "llama3.2:latest"
    ↓
llm.py → OllamaLLM(model=settings.ollama_model)
    ↓
rag_pipeline.py → generation_chain = llm | StrOutputParser()
    ↓
generation_service.py → invoke_generation_pipeline(...)
```

### Diseño propuesto

El cambio es mínimo y backward-compatible. Tres puntos de toque:

**1. `Settings` — añadir overrides opcionales por categoría**

```python
# app/core/config/__init__.py
ollama_model: str = "llama3.2:latest"                    # modelo por defecto (sin cambios)
ollama_model_overrides: dict[str, str] = {}               # overrides por categoría
# Ejemplo en .env:
# OLLAMA_MODEL_OVERRIDES='{"chapter": "llama3.1:8b", "backstory": "gemma2:9b"}'
```

**2. `llm.py` — factory con caché por model string**

```python
# app/engine/llm.py
import functools

@functools.lru_cache(maxsize=8)
def get_llm(model: str) -> OllamaLLM:
    return OllamaLLM(
        model=model,
        base_url=settings.ollama_base_url,
        temperature=settings.temperature,
        num_predict=settings.max_tokens,
    )

# Instancia por defecto para compatibilidad hacia atrás
llm = get_llm(settings.ollama_model)
```

**3. `rag_pipeline.py` — resolver modelo por categoría en invoke**

```python
# app/engine/rag_pipeline.py
def invoke_generation_pipeline(
    ...,
    category: ContentCategory,
) -> tuple[str, int]:
    model = settings.ollama_model_overrides.get(category.value, settings.ollama_model)
    llm_instance = get_llm(model)
    generation_chain = llm_instance | StrOutputParser()
    ...
```

### Por qué este diseño

- **Cero breaking changes**: `ollama_model_overrides` defecto vacío → comportamiento idéntico al actual.
- **Sin rediseño**: no hay repositorio de LLMs ni inyección de dependencias nueva — solo un dict y una función cacheada.
- **Configurable vía .env**: los overrides se pueden cambiar sin tocar código.
- **Lazy init**: los modelos alternativos solo se cargan si hay un override configurado.

> Este feature **no se implementa** hasta que los datos de Phase 2 confirmen que algún modelo supera al baseline por ≥ 0.5 puntos en una categoría. Sin datos no hay justificación.

---

## Orden de trabajo

| Paso | Actividad | Prerequisito |
|---|---|---|
| 1 | `ollama pull llama3.1` + `ollama pull qwen2.5` + `ollama pull mistral` | Ollama activo |
| 2 | Ejecutar runner.py para cada modelo nuevo (3 runs) | Paso 1 |
| 3 | Ejecutar judge.py con gemma2 en cada run nuevo (3 evals) | Paso 2 |
| 4 | Implementar `reporter.py` | — |
| 5 | Generar reporte con los 4 modelos (baseline + 3 nuevos) | Pasos 3 y 4 |
| 6 | Decidir qué categorías justifican switch (umbral 0.5) | Paso 5 |
| 7 | Implementar per-category switch en backend **si aplica** | Paso 6 |
| 8 | Actualizar smoke tests si se toca el backend | Paso 7 |
| 9 | Merge `feature/model-harness` → `dev` | Pasos 5-8 |

---

## Entregables

| Entregable | Descripción |
|---|---|
| 3 runs de generación | llama3.1:8b, gemma2:9b, qwen2.5:7b contra los 10 TCs |
| 3 evals con gemma2 | Scores D1-D4 para cada run nuevo |
| `reporter.py` | Script que genera reporte markdown multi-modelo |
| `docs/phase2-model-comparison.md` | Reporte final con ranking y recomendaciones |
| Backend switch (condicional) | Solo si datos justifican; diseño ya documentado arriba |

---

## Lo que este plan NO incluye

- **Evaluación de embeddings o recuperación Qdrant:** el problema puede estar en la recuperación, no en la generación. Eso es una fase separada.
- **Temperatura como variable:** phase 2 usa 0.7 fija. Una fase futura podría explorar 0.5 vs 0.7 vs 0.9 en chapter y scene.
- **Integración en CI/CD:** el harness sigue siendo un herramienta offline manual.
- **Modelos mayores de 14B:** fuera del rango realista para ejecución local sin GPU dedicada de alta memoria.
- **API externa (Claude, GPT):** requeriría gestión de costes y claves; queda como opción futura documentada en PHASE-1-RESULTADOS.md.
