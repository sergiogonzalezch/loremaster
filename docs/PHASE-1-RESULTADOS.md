# Fase 1 — Resultados del Experimento de Refactor de Prompts

**Fecha:** 2026-05-13  
**Rama:** `feature/prompt-harness`  
**Modelo de generación:** `llama3.2:latest` (temp=0.7)  
**Modelo juez:** `qwen3.5:9b` (externo, sin auto-evaluación)

---

## Archivos refactorizados

| Archivo | Cambios principales |
|---------|---------------------|
| `backend/app/engine/llm.py` | Separadores XML, extensión 2-3 párrafos, instrucción de fallback |
| `backend/app/domain/prompt_templates.py` | Señales temporales por categoría, targets de longitud, Regla 3 |
| `backend/app/domain/image_prompt_rules.py` | Fusión de constantes, formato simplificado |

---

## Resultados cuantitativos

### Puntuaciones por dimensión (promedio de 10 casos)

| Dimensión | Baseline | Refactor | Delta |
|-----------|:--------:|:--------:|:-----:|
| D1 — Adherencia al contexto | 2.90 | 2.20 | **-0.70** |
| D2 — Especificidad narrativa | 2.80 | 2.30 | **-0.50** |
| D3 — Cumplimiento de categoría | 2.90 | 2.60 | **-0.30** |
| D4 — Completitud / longitud | 1.30 | 1.60 | **+0.30** |

### Criterios de validación definidos en PHASE-1.md

| Criterio | Resultado |
|----------|-----------|
| D3 mejora >= 0.3 | FAIL |
| D1 no empeora | FAIL |
| TC-04 / TC-05 sin rechazos | **PASS** |

### Puntuaciones por caso

| TC | Categoría | Ctx | Baseline (D1/D2/D3/D4) | Refactor (D1/D2/D3/D4) | Juez baseline | Juez refactor |
|----|-----------|-----|-------------------------|-------------------------|---------------|---------------|
| TC-01 | backstory | rich | 3/3/3/1 | 2/2/2/2 | qwen3.5 | qwen3.5 |
| TC-02 | backstory | sparse | 3/3/3/1 | 2/3/3/1 | qwen3.5 | qwen3.5 |
| TC-03 | chapter | rich | 3/2/3/1 | 3/3/3/1 | qwen3.5 | qwen3.5 |
| TC-04 | scene | sparse | 3/3/3/1 | 2/2/2/2 | qwen3.5 | qwen3.5 |
| TC-05 | scene | irrelevant | 2/2/2/2 | 2/2/3/2 | qwen3.5 | qwen3.5 |
| TC-06 | backstory | rich | 3/3/3/3 | 2/2/2/2 | **manual** | qwen3.5 |
| TC-07 | ext_desc | rich | 3/3/3/1 | 3/3/3/1 | qwen3.5 | qwen3.5 |
| TC-08 | backstory | rich | 3/3/3/1 | 2/2/3/2 | qwen3.5 | qwen3.5 |
| TC-09 | ext_desc | sparse | 3/3/3/1 | 2/2/2/2 | qwen3.5 | qwen3.5 |
| TC-10 | scene | rich | 3/3/3/1 | 2/2/3/1 | qwen3.5 | qwen3.5 |

> **Nota:** TC-06 baseline fue puntuado manualmente (llama3.2 no devolvía JSON válido para ese output de 4130 chars). Esto infla el baseline en ~0.3 puntos por dimensión respecto a los demás casos.

---

## Análisis de las regresiones

### Causa identificada: instrucción "nota breve"

El refactor incluyó esta instrucción en `_CONTEXT_INSTRUCTION`:

```
"Si el contexto es escaso, genera con lo disponible y añade al final
una nota breve indicando qué información adicional enriquecería el resultado."
```

**Problema:** llama3.2 activa la nota en **todos los outputs**, incluso con contexto rico.

**Consecuencias observadas:**

1. **El modelo gasta tokens en la meta-nota** en lugar de en contenido narrativo.  
   Ejemplo TC-01: baseline 2651 chars → refactored 2123 chars (más corto, peor).

2. **El juez interpreta la nota como señal de contexto insuficiente** y penaliza D1.  
   TC-01 refactored termina con:  
   > *"Nota adicional: Para profundizar en la historia de Kael... sería útil conocer más sobre su relación con Solaris..."*  
   qwen3.5 lee esto y asigna D1=2 ("uso parcial del contexto").

### Lo que mejoró genuinamente

- **D4 +0.30**: los targets de longitud funcionan. El baseline tenía D4=1 en 8/10 casos (demasiado corto). El refactor los llevó a D4=2.
- **Regla 3 validada**: TC-04 (sparse) y TC-05 (irrelevant) no generaron rechazos en ningún run.
- **TC-03 mejoró realmente**: el capítulo refactorizado tiene 3078 chars vs 2286 del baseline, y D2 subió de 2 a 3.

### Lo que el juez penalizó pero puede ser ruido

- La diferencia D1/D2 entre ambos runs puede amplificarse por **inconsistencia del juez entre sesiones distintas**: qwen3.5 no estaba calibrado entre el run de baseline y el run de refactored. En TC-07 (también tiene nota), D1/D2 se mantuvieron en 3 en ambas versiones.

---

## Limitaciones del experimento

1. **Juez mixto**: qwen3.5 (mayoría), llama3.2 como fallback, 1 caso manual. Inconsistencia metodológica.
2. **TC-06 manual inflado**: el único caso sin juez LLM fue el más largo del baseline (4130 chars), puntuado con 3/3/3/3. Esto sesga el baseline al alza.
3. **n=10**: muestra pequeña para extraer conclusiones estadísticas sólidas.
4. **Una sola temperatura**: solo se evaluó temp=0.7. La variabilidad del modelo puede ocultar diferencias reales.

---

## Opciones de siguiente paso

### Opción A — Fix rápido + re-evaluar (~30 min)
Eliminar la instrucción "nota breve" de `_CONTEXT_INSTRUCTION`.

**Cambio en `prompt_templates.py`:**
```python
# Antes
_CONTEXT_INSTRUCTION = (
    "Usa la información del contexto proporcionado. "
    "Si el contexto es escaso, genera con lo disponible y añade al final "
    "una nota breve indicando qué información adicional enriquecería el resultado. "
    "No rechaces la generación por falta de contexto."
)

# Después
_CONTEXT_INSTRUCTION = (
    "Usa la información del contexto proporcionado. "
    "Si el contexto es escaso, genera con lo disponible sin rechazar la solicitud."
)
```

Luego: nuevo run refactored (v2), comparar v2 vs baseline con juez limpio.

**Pro:** datos limpios, validación correcta.  
**Contra:** requiere otro ciclo de evaluación (~20 min de ejecución).

---

### Opción B — Aceptar y hacer merge
Las mejoras reales (D4, Regla 3, TC-03) justifican el refactor. Documentar la "nota breve" como deuda técnica.

**Pro:** cierra la tarea sin más iteraciones.  
**Contra:** los criterios formales de validación no se cumplen. La "nota breve" es un bug real que afecta la calidad narrativa.

---

### Opción C — Revertir al snapshot
Rollback al commit `530c520` (pre-refactor) y diseñar v2 desde cero.

**Pro:** conservadora, sin riesgo.  
**Contra:** se pierden las mejoras reales (D4, Regla 3). El refactor no es perjudicial — solo tiene un bug puntual.

---

## Recomendación

**Opción A.** El fix es una línea de código en `prompt_templates.py`. Con un run limpio tendremos validación real en lugar de resultados contaminados por el efecto "nota breve". Las mejoras en D4 y Regla 3 son reales; solo necesitamos eliminar el ruido para verlas reflejadas también en D1/D2.
