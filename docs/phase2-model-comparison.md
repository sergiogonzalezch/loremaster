# Phase 2 — Comparativa de Modelos (llama3.2 vs llama3.1 vs qwen2.5 vs mistral)

**Generado:** 2026-05-14 10:06  
**Juez:** `gemma2:9b`  
**Baseline:** `llama3.2 (t=0.7)`  
**Umbral de switch:** ≥ 0.5 puntos de diferencia en D3 por categoría

---

## Ranking global

| Modelo | Rechazos | D1 | D2 | D3 | D4 | Promedio |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **`mistral (t=0.7)`** | 0/10 | 2.90 | 2.00 | 3.00 | 2.10 | **2.50** |
| `llama3.2 (t=0.7)` | 0/10 | 2.50 | 2.00 | 2.80 | 2.00 | 2.33 |
| `qwen2.5 (t=0.7)` | 7/10 | 1.90 | 1.50 | 2.00 | 1.50 | 1.73 |
| `llama3.1 (t=0.7)` | 0/10 | 1.20 | 1.10 | 1.20 | 1.10 | 1.15 |

---

## D3 — Cumplimiento de categoría por modelo

| Categoría | `llama3.2 (t=0.7)` | `llama3.1 (t=0.7)` | `qwen2.5 (t=0.7)` | `mistral (t=0.7)` | Mejor |
|---|:---:|:---:|:---:|:---:|:---|
| `backstory` | 2.67 | 1.00 | 1.00 | 3.00 | `mistral (t=0.7)` |
| `chapter` | 3.00 | 1.00 | 3.00 | 3.00 | `llama3.2 (t=0.7)` |
| `extended_description` | 3.00 | 1.67 | 3.00 | 3.00 | `llama3.2 (t=0.7)` |
| `scene` | 2.50 | 1.00 | 1.00 | 3.00 | `mistral (t=0.7)` ⚡ |

---

## Tiempos de respuesta

| Modelo | Promedio (s) | Mínimo (s) | Máximo (s) |
|---|:---:|:---:|:---:|
| `llama3.2 (t=0.7)` | 7.7 | 5.3 | 12.2 |
| `llama3.1 (t=0.7)` | 4.7 | 2.7 | 14.8 |
| `qwen2.5 (t=0.7)` | 7.2 | 2.5 | 16.0 |
| `mistral (t=0.7)` | 9.5 | 5.7 | 16.4 |

---

## Scores por caso (D1 / D2 / D3 / D4)

| TC | Categoría | Ctx | `llama3.2 (t=0.7)` | `llama3.1 (t=0.7)` | `qwen2.5 (t=0.7)` | `mistral (t=0.7)` |
|---|---|---|---|---|---|---|
| TC-01 | backstor | rich | 3/2/3/2 | 1/1/1/1 | 1/1/1/1⚠ | 3/2/3/2 |
| TC-02 | extended | rich | 3/2/3/2 | 3/2/3/2 | 3/2/3/2 | 3/2/3/2 |
| TC-03 | chapter | rich | 3/2/3/2 | 1/1/1/1 | 3/2/3/2⚠ | 3/2/3/2 |
| TC-04 | scene | sparse | 2/2/3/2 | 1/1/1/1 | 1/1/1/1⚠ | 3/2/3/2 |
| TC-05 | backstor | irreleva | 2/2/3/2 | 1/1/1/1 | 1/1/1/1⚠ | 3/2/3/3 |
| TC-06 | backstor | rich | 2/2/2/2 | 1/1/1/1 | 1/1/1/1⚠ | 3/2/3/2 |
| TC-07 | extended | rich | 3/2/3/2 | 1/1/1/1 | 2/2/3/2 | 3/2/3/2 |
| TC-08 | chapter | rich | 3/2/3/2 | 1/1/1/1 | 3/2/3/2⚠ | 3/2/3/2 |
| TC-09 | extended | sparse | 2/2/3/2 | 1/1/1/1 | 3/2/3/2 | 3/2/3/2 |
| TC-10 | scene | rich | 2/2/2/2 | 1/1/1/1 | 1/1/1/1⚠ | 2/2/3/2 |

---

## Decisión de switch por categoría

Umbral: el mejor modelo alternativo debe superar al baseline en **≥ 0.5** puntos de D3.

| Categoría | Baseline D3 | Mejor alternativo | Delta D3 | ¿Switch? |
|---|:---:|---|:---:|:---:|
| `backstory` | 2.67 | `mistral (t=0.7)` (3.00) | +0.33 | ❌ No |
| `chapter` | 3.00 | `qwen2.5 (t=0.7)` (3.00) | +0.00 | ❌ No |
| `extended_description` | 3.00 | `qwen2.5 (t=0.7)` (3.00) | +0.00 | ❌ No |
| `scene` | 2.50 | `mistral (t=0.7)` (3.00) | +0.50 | ✅ Sí |

---

## Resumen y próximos pasos

**Modelo ganador overall:** `mistral (t=0.7)`

**Categorías con switch recomendado (delta ≥ 0.5):**

- `scene` → usar `mistral (t=0.7)`

**Próximo paso:** implementar `ollama_model_overrides` en Settings y `get_llm()` factory
en `llm.py` para activar el switch por categoría (ver diseño en `docs/PHASE-2.md`).

---

*Reporte generado automáticamente por `reporter.py` — harness LoreMaster*