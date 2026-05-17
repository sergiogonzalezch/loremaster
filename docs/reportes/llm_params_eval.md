# Evaluación de Parámetros LLM — Temperatura y num_predict
**Generado:** 2026-05-16 16:40  
**Juez:** gemma2:9b  
**Runs:** 16

---
## Resumen ejecutivo

- **llama3.2:latest**: mejor config = `temp_only` → avg=2.27/3.0 (Δ+0.04 vs baseline) ⚪
- **llama3.1:latest**: mejor config = `tokens_only` → avg=2.3/3.0 (Δ-0.03 vs baseline) ⚪
- **qwen2.5:latest**: mejor config = `tokens_only` → avg=2.02/3.0 (Δ+0.12 vs baseline) ✅
- **mistral:latest**: mejor config = `tokens_only` → avg=2.3/3.0 (Δ-0.05 vs baseline) ⚪

---
## 1. Ranking global

| # | Configuración | Modelo | Errores | D1 | D2 | D3 | D4 | Promedio |
|---|---|---|---|---|---|---|---|---|
| 1 | `Baseline` | mistral:latest | 0 | 2.0 | 2.5 | 2.6 | 2.3 | **2.35** |
| 2 | `Baseline` | llama3.1:latest | 0 | 1.8 | 2.4 | 2.8 | 2.3 | **2.33** |
| 3 | `Solo tokens` | llama3.1:latest | 0 | 1.8 | 2.5 | 2.5 | 2.4 | **2.3** |
| 4 | `Solo tokens` | mistral:latest | 0 | 1.9 | 2.6 | 2.6 | 2.1 | **2.3** |
| 5 | `Temp + tokens` | mistral:latest | 0 | 1.8 | 2.5 | 2.5 | 2.4 | **2.3** |
| 6 | `Solo temp` | llama3.2:latest | 0 | 1.6 | 2.5 | 2.6 | 2.4 | **2.27** |
| 7 | `Solo temp` | llama3.1:latest | 0 | 1.8 | 2.5 | 2.5 | 2.3 | **2.27** |
| 8 | `Solo temp` | mistral:latest | 0 | 1.7 | 2.4 | 2.3 | 2.7 | **2.27** |
| 9 | `Temp + tokens` | llama3.1:latest | 0 | 1.8 | 2.5 | 2.4 | 2.3 | **2.25** |
| 10 | `Baseline` | llama3.2:latest | 0 | 1.6 | 2.5 | 2.3 | 2.5 | **2.23** |
| 11 | `Solo tokens` | llama3.2:latest | 0 | 1.7 | 2.2 | 2.6 | 2.4 | **2.23** |
| 12 | `Temp + tokens` | llama3.2:latest | 0 | 1.5 | 2.3 | 2.3 | 2.5 | **2.15** |
| 13 | `Solo tokens` | qwen2.5:latest | 0 | 1.6 | 2.3 | 1.9 | 2.3 | **2.02** |
| 14 | `Temp + tokens` | qwen2.5:latest | 0 | 1.5 | 2.3 | 2.0 | 2.0 | **1.95** |
| 15 | `Baseline` | qwen2.5:latest | 0 | 1.4 | 2.4 | 1.8 | 2.0 | **1.9** |
| 16 | `Solo temp` | qwen2.5:latest | 0 | 1.3 | 2.1 | 2.0 | 2.0 | **1.85** |

---
## 2. Comparativa de configuraciones vs baseline

> ✓ = mejora ≥ 0.20 | ✗ = regresión ≥ 0.20

### llama3.2:latest

| Dimensión | Baseline | Solo temp | Δ | Solo tokens | Δ | Temp + tokens | Δ |
|---|---|--- | --- | --- | --- | --- | ---|
| D1 — Adherencia ctx | 1.6 | 1.6 | = | 1.7 | +0.1 | 1.5 | -0.1 |
| D2 — Especificidad | 2.5 | 2.5 | = | 2.2 | -0.3 ✗ | 2.3 | -0.2 ✗ |
| D3 — Categoría | 2.3 | 2.6 | +0.3 ✓ | 2.6 | +0.3 ✓ | 2.3 | = |
| D4 — Completitud | 2.5 | 2.4 | -0.1 | 2.4 | -0.1 | 2.5 | = |
| **Promedio** | 2.23 | 2.27 | +0.04 | 2.23 | = | 2.15 | -0.08 |

### llama3.1:latest

| Dimensión | Baseline | Solo temp | Δ | Solo tokens | Δ | Temp + tokens | Δ |
|---|---|--- | --- | --- | --- | --- | ---|
| D1 — Adherencia ctx | 1.8 | 1.8 | = | 1.8 | = | 1.8 | = |
| D2 — Especificidad | 2.4 | 2.5 | +0.1 | 2.5 | +0.1 | 2.5 | +0.1 |
| D3 — Categoría | 2.8 | 2.5 | -0.3 ✗ | 2.5 | -0.3 ✗ | 2.4 | -0.4 ✗ |
| D4 — Completitud | 2.3 | 2.3 | = | 2.4 | +0.1 | 2.3 | = |
| **Promedio** | 2.33 | 2.27 | -0.06 | 2.3 | -0.03 | 2.25 | -0.08 |

### qwen2.5:latest

| Dimensión | Baseline | Solo temp | Δ | Solo tokens | Δ | Temp + tokens | Δ |
|---|---|--- | --- | --- | --- | --- | ---|
| D1 — Adherencia ctx | 1.4 | 1.3 | -0.1 | 1.6 | +0.2 ✓ | 1.5 | +0.1 |
| D2 — Especificidad | 2.4 | 2.1 | -0.3 ✗ | 2.3 | -0.1 | 2.3 | -0.1 |
| D3 — Categoría | 1.8 | 2.0 | +0.2 ✓ | 1.9 | +0.1 | 2.0 | +0.2 ✓ |
| D4 — Completitud | 2.0 | 2.0 | = | 2.3 | +0.3 ✓ | 2.0 | = |
| **Promedio** | 1.9 | 1.85 | -0.05 | 2.02 | +0.12 | 1.95 | +0.05 |

### mistral:latest

| Dimensión | Baseline | Solo temp | Δ | Solo tokens | Δ | Temp + tokens | Δ |
|---|---|--- | --- | --- | --- | --- | ---|
| D1 — Adherencia ctx | 2.0 | 1.7 | -0.3 ✗ | 1.9 | -0.1 | 1.8 | -0.2 ✗ |
| D2 — Especificidad | 2.5 | 2.4 | -0.1 | 2.6 | +0.1 | 2.5 | = |
| D3 — Categoría | 2.6 | 2.3 | -0.3 ✗ | 2.6 | = | 2.5 | -0.1 |
| D4 — Completitud | 2.3 | 2.7 | +0.4 ✓ | 2.1 | -0.2 ✗ | 2.4 | +0.1 |
| **Promedio** | 2.35 | 2.27 | -0.08 | 2.3 | -0.05 | 2.3 | -0.05 |

---
## 3. Análisis por categoría

> Permite ver si temperatura beneficia más a `scene` que a `backstory`, etc.

### backstory

| Configuración | Modelo | D1 | D2 | D3 | D4 | Promedio |
|---|---|---|---|---|---|---|
| `Baseline` | llama3.1:latest | 2.25 | 2.75 | 2.75 | 2.5 | **2.56** |
| `Solo temp` | mistral:latest | 2.25 | 2.75 | 2.25 | 2.75 | **2.5** |
| `Temp + tokens` | qwen2.5:latest | 2.25 | 2.75 | 2.25 | 2.75 | **2.5** |
| `Temp + tokens` | llama3.1:latest | 2.25 | 2.75 | 2.75 | 2.0 | **2.44** |
| `Baseline` | llama3.2:latest | 2.0 | 3.0 | 2.0 | 2.75 | **2.44** |
| `Solo temp` | llama3.2:latest | 2.0 | 2.75 | 2.5 | 2.5 | **2.44** |
| `Temp + tokens` | llama3.2:latest | 2.0 | 2.75 | 2.25 | 2.5 | **2.38** |
| `Baseline` | mistral:latest | 2.25 | 2.5 | 2.5 | 2.25 | **2.38** |
| `Solo tokens` | mistral:latest | 2.25 | 2.5 | 2.5 | 2.25 | **2.38** |
| `Temp + tokens` | mistral:latest | 2.25 | 2.5 | 2.5 | 2.25 | **2.38** |
| `Solo tokens` | llama3.1:latest | 1.75 | 2.5 | 2.25 | 2.75 | **2.31** |
| `Solo tokens` | llama3.2:latest | 2.0 | 2.25 | 2.5 | 2.5 | **2.31** |
| `Solo temp` | llama3.1:latest | 2.0 | 2.25 | 2.25 | 2.5 | **2.25** |
| `Solo tokens` | qwen2.5:latest | 1.75 | 2.0 | 1.5 | 2.25 | **1.88** |
| `Baseline` | qwen2.5:latest | 1.5 | 2.25 | 1.5 | 2.0 | **1.81** |
| `Solo temp` | qwen2.5:latest | 1.5 | 2.0 | 2.0 | 1.5 | **1.75** |

### extended_description

| Configuración | Modelo | D1 | D2 | D3 | D4 | Promedio |
|---|---|---|---|---|---|---|
| `Solo tokens` | qwen2.5:latest | 1.67 | 3.0 | 3.0 | 2.67 | **2.58** |
| `Baseline` | mistral:latest | 1.67 | 2.67 | 2.67 | 2.67 | **2.42** |
| `Solo tokens` | mistral:latest | 1.67 | 3.0 | 3.0 | 2.0 | **2.42** |
| `Solo tokens` | llama3.1:latest | 1.67 | 2.67 | 3.0 | 2.0 | **2.33** |
| `Baseline` | qwen2.5:latest | 1.33 | 3.0 | 2.67 | 2.33 | **2.33** |
| `Temp + tokens` | qwen2.5:latest | 1.33 | 3.0 | 3.0 | 2.0 | **2.33** |
| `Solo temp` | llama3.1:latest | 1.33 | 2.67 | 3.0 | 2.0 | **2.25** |
| `Temp + tokens` | mistral:latest | 1.33 | 2.67 | 2.67 | 2.33 | **2.25** |
| `Baseline` | llama3.1:latest | 1.33 | 2.0 | 3.0 | 2.33 | **2.17** |
| `Solo tokens` | llama3.2:latest | 1.33 | 2.33 | 2.67 | 2.33 | **2.17** |
| `Solo temp` | qwen2.5:latest | 1.0 | 2.33 | 2.67 | 2.67 | **2.17** |
| `Solo temp` | llama3.2:latest | 1.0 | 2.0 | 3.0 | 2.33 | **2.08** |
| `Temp + tokens` | llama3.2:latest | 1.0 | 2.0 | 2.67 | 2.67 | **2.08** |
| `Baseline` | llama3.2:latest | 1.0 | 2.0 | 2.67 | 2.33 | **2.0** |
| `Solo temp` | mistral:latest | 1.0 | 1.67 | 2.67 | 2.33 | **1.92** |
| `Temp + tokens` | llama3.1:latest | 1.0 | 1.67 | 2.33 | 2.33 | **1.83** |

### scene

| Configuración | Modelo | D1 | D2 | D3 | D4 | Promedio |
|---|---|---|---|---|---|---|
| `Temp + tokens` | llama3.1:latest | 2.0 | 3.0 | 2.0 | 2.67 | **2.42** |
| `Solo temp` | llama3.1:latest | 2.0 | 2.67 | 2.33 | 2.33 | **2.33** |
| `Solo temp` | mistral:latest | 1.67 | 2.67 | 2.0 | 3.0 | **2.33** |
| `Solo tokens` | llama3.1:latest | 2.0 | 2.33 | 2.33 | 2.33 | **2.25** |
| `Solo temp` | llama3.2:latest | 1.67 | 2.67 | 2.33 | 2.33 | **2.25** |
| `Baseline` | mistral:latest | 2.0 | 2.33 | 2.67 | 2.0 | **2.25** |
| `Temp + tokens` | mistral:latest | 1.67 | 2.33 | 2.33 | 2.67 | **2.25** |
| `Baseline` | llama3.1:latest | 1.67 | 2.33 | 2.67 | 2.0 | **2.17** |
| `Baseline` | llama3.2:latest | 1.67 | 2.33 | 2.33 | 2.33 | **2.17** |
| `Solo tokens` | llama3.2:latest | 1.67 | 2.0 | 2.67 | 2.33 | **2.17** |
| `Solo tokens` | mistral:latest | 1.67 | 2.33 | 2.33 | 2.0 | **2.08** |
| `Temp + tokens` | llama3.2:latest | 1.33 | 2.0 | 2.0 | 2.33 | **1.92** |
| `Solo temp` | qwen2.5:latest | 1.33 | 2.0 | 1.33 | 2.0 | **1.67** |
| `Solo tokens` | qwen2.5:latest | 1.33 | 2.0 | 1.33 | 2.0 | **1.67** |
| `Baseline` | qwen2.5:latest | 1.33 | 2.0 | 1.33 | 1.67 | **1.58** |
| `Temp + tokens` | qwen2.5:latest | 0.67 | 1.0 | 0.67 | 1.0 | **0.83** |

---
## 4. Análisis por modelo

> ¿La mejora es consistente entre modelos o solo beneficia a alguno?

### llama3.2:latest

| Configuración | D1 | D2 | D3 | D4 | Promedio | vs baseline |
|---|---|---|---|---|---|---|
| `Baseline` | 1.6 | 2.5 | 2.3 | 2.5 | **2.23** | — |
| `Solo temp` | 1.6 | 2.5 | 2.6 | 2.4 | **2.27** | +0.04 |
| `Solo tokens` | 1.7 | 2.2 | 2.6 | 2.4 | **2.23** | = |
| `Temp + tokens` | 1.5 | 2.3 | 2.3 | 2.5 | **2.15** | -0.08 |

### llama3.1:latest

| Configuración | D1 | D2 | D3 | D4 | Promedio | vs baseline |
|---|---|---|---|---|---|---|
| `Baseline` | 1.8 | 2.4 | 2.8 | 2.3 | **2.33** | — |
| `Solo temp` | 1.8 | 2.5 | 2.5 | 2.3 | **2.27** | -0.06 |
| `Solo tokens` | 1.8 | 2.5 | 2.5 | 2.4 | **2.3** | -0.03 |
| `Temp + tokens` | 1.8 | 2.5 | 2.4 | 2.3 | **2.25** | -0.08 |

### qwen2.5:latest

| Configuración | D1 | D2 | D3 | D4 | Promedio | vs baseline |
|---|---|---|---|---|---|---|
| `Baseline` | 1.4 | 2.4 | 1.8 | 2.0 | **1.9** | — |
| `Solo temp` | 1.3 | 2.1 | 2.0 | 2.0 | **1.85** | -0.05 |
| `Solo tokens` | 1.6 | 2.3 | 1.9 | 2.3 | **2.02** | +0.12 |
| `Temp + tokens` | 1.5 | 2.3 | 2.0 | 2.0 | **1.95** | +0.05 |

### mistral:latest

| Configuración | D1 | D2 | D3 | D4 | Promedio | vs baseline |
|---|---|---|---|---|---|---|
| `Baseline` | 2.0 | 2.5 | 2.6 | 2.3 | **2.35** | — |
| `Solo temp` | 1.7 | 2.4 | 2.3 | 2.7 | **2.27** | -0.08 |
| `Solo tokens` | 1.9 | 2.6 | 2.6 | 2.1 | **2.3** | -0.05 |
| `Temp + tokens` | 1.8 | 2.5 | 2.5 | 2.4 | **2.3** | -0.05 |

---
## 5. Tiempos de respuesta

> `tokens_only` y `both` aumentan num_predict en `scene` (2000→2500); se espera latencia ligeramente mayor.

| Configuración | Modelo | Promedio (s) | Mínimo (s) | Máximo (s) |
|---|---|---|---|---|
| `Baseline` | llama3.1:latest | 23.1 | 16.8 | 32.9 |
| `Baseline` | llama3.2:latest | 13.6 | 9.9 | 27.8 |
| `Baseline` | mistral:latest | 18.1 | 15.3 | 22.5 |
| `Baseline` | qwen2.5:latest | 16.2 | 9.1 | 19.4 |
| `Temp + tokens` | llama3.1:latest | 19.7 | 14.3 | 28.1 |
| `Temp + tokens` | llama3.2:latest | 14.2 | 11.2 | 29.1 |
| `Temp + tokens` | mistral:latest | 24.7 | 15.3 | 46.5 |
| `Temp + tokens` | qwen2.5:latest | 15.6 | 8.6 | 19.0 |
| `Solo temp` | llama3.1:latest | 17.9 | 13.6 | 22.2 |
| `Solo temp` | llama3.2:latest | 13.9 | 10.3 | 27.3 |
| `Solo temp` | mistral:latest | 17.6 | 13.3 | 22.2 |
| `Solo temp` | qwen2.5:latest | 15.9 | 9.0 | 21.6 |
| `Solo tokens` | llama3.1:latest | 19.4 | 14.9 | 26.5 |
| `Solo tokens` | llama3.2:latest | 12.9 | 11.0 | 15.9 |
| `Solo tokens` | mistral:latest | 17.6 | 14.1 | 21.2 |
| `Solo tokens` | qwen2.5:latest | 16.2 | 8.8 | 20.9 |

---
## 6. Scores detallados por caso

#### TC-01 — character / backstory  *(contexto: rich)*

| Configuración | Modelo | D1 | D2 | D3 | D4 | Avg |
|---|---|---|---|---|---|---|
| `Baseline` | llama3.1:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Baseline` | llama3.2:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Baseline` | mistral:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Baseline` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 |
| `Solo temp` | llama3.1:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Solo temp` | llama3.2:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Solo temp` | mistral:latest | 2 | 3 | 2 | 2 | 2.25 |
| `Solo temp` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 |
| `Solo tokens` | llama3.1:latest | 1 | 2 | 2 | 3 | 2.0 |
| `Solo tokens` | llama3.2:latest | 2 | 2 | 3 | 2 | 2.25 |
| `Solo tokens` | mistral:latest | 2 | 3 | 2 | 2 | 2.25 |
| `Solo tokens` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 |
| `Temp + tokens` | llama3.1:latest | 2 | 3 | 2 | 2 | 2.25 |
| `Temp + tokens` | llama3.2:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Temp + tokens` | mistral:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Temp + tokens` | qwen2.5:latest | 2 | 3 | 2 | 3 | 2.5 |

#### TC-02 — character / extended_description  *(contexto: rich)*

| Configuración | Modelo | D1 | D2 | D3 | D4 | Avg |
|---|---|---|---|---|---|---|
| `Baseline` | llama3.1:latest | 1 | 2 | 3 | 2 | 2.0 |
| `Baseline` | llama3.2:latest | 1 | 2 | 3 | 2 | 2.0 |
| `Baseline` | mistral:latest | 1 | 2 | 3 | 3 | 2.25 |
| `Baseline` | qwen2.5:latest | 1 | 3 | 3 | 2 | 2.25 |
| `Solo temp` | llama3.1:latest | 1 | 3 | 3 | 2 | 2.25 |
| `Solo temp` | llama3.2:latest | 1 | 2 | 3 | 3 | 2.25 |
| `Solo temp` | mistral:latest | 1 | 2 | 3 | 2 | 2.0 |
| `Solo temp` | qwen2.5:latest | 1 | 2 | 3 | 2 | 2.0 |
| `Solo tokens` | llama3.1:latest | 1 | 2 | 3 | 2 | 2.0 |
| `Solo tokens` | llama3.2:latest | 1 | 2 | 3 | 2 | 2.0 |
| `Solo tokens` | mistral:latest | 1 | 3 | 3 | 2 | 2.25 |
| `Solo tokens` | qwen2.5:latest | 1 | 3 | 3 | 3 | 2.5 |
| `Temp + tokens` | llama3.1:latest | 1 | 2 | 2 | 3 | 2.0 |
| `Temp + tokens` | llama3.2:latest | 1 | 2 | 3 | 3 | 2.25 |
| `Temp + tokens` | mistral:latest | 1 | 3 | 3 | 2 | 2.25 |
| `Temp + tokens` | qwen2.5:latest | 1 | 3 | 3 | 2 | 2.25 |

#### TC-03 — character / scene  *(contexto: rich)*

| Configuración | Modelo | D1 | D2 | D3 | D4 | Avg |
|---|---|---|---|---|---|---|
| `Baseline` | llama3.1:latest | 2 | 3 | 2 | 2 | 2.25 |
| `Baseline` | llama3.2:latest | 2 | 2 | 3 | 2 | 2.25 |
| `Baseline` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 |
| `Baseline` | qwen2.5:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Solo temp` | llama3.1:latest | 2 | 2 | 3 | 2 | 2.25 |
| `Solo temp` | llama3.2:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Solo temp` | mistral:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Solo temp` | qwen2.5:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Solo tokens` | llama3.1:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Solo tokens` | llama3.2:latest | 2 | 2 | 3 | 2 | 2.25 |
| `Solo tokens` | mistral:latest | 2 | 3 | 2 | 2 | 2.25 |
| `Solo tokens` | qwen2.5:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Temp + tokens` | llama3.1:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Temp + tokens` | llama3.2:latest | 1 | 2 | 2 | 2 | 1.75 |
| `Temp + tokens` | mistral:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Temp + tokens` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 |

#### TC-04 — creature / backstory  *(contexto: medium)*

| Configuración | Modelo | D1 | D2 | D3 | D4 | Avg |
|---|---|---|---|---|---|---|
| `Baseline` | llama3.1:latest | 2 | 3 | 3 | 2 | 2.5 |
| `Baseline` | llama3.2:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Baseline` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 |
| `Baseline` | qwen2.5:latest | 2 | 3 | 2 | 2 | 2.25 |
| `Solo temp` | llama3.1:latest | 2 | 1 | 2 | 2 | 1.75 |
| `Solo temp` | llama3.2:latest | 2 | 3 | 3 | 2 | 2.5 |
| `Solo temp` | mistral:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Solo temp` | qwen2.5:latest | 2 | 2 | 3 | 2 | 2.25 |
| `Solo tokens` | llama3.1:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Solo tokens` | llama3.2:latest | 2 | 2 | 3 | 2 | 2.25 |
| `Solo tokens` | mistral:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Solo tokens` | qwen2.5:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Temp + tokens` | llama3.1:latest | 2 | 2 | 3 | 2 | 2.25 |
| `Temp + tokens` | llama3.2:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Temp + tokens` | mistral:latest | 2 | 3 | 2 | 2 | 2.25 |
| `Temp + tokens` | qwen2.5:latest | 2 | 3 | 2 | 3 | 2.5 |

#### TC-05 — creature / extended_description  *(contexto: medium)*

| Configuración | Modelo | D1 | D2 | D3 | D4 | Avg |
|---|---|---|---|---|---|---|
| `Baseline` | llama3.1:latest | 1 | 2 | 3 | 2 | 2.0 |
| `Baseline` | llama3.2:latest | 1 | 2 | 3 | 2 | 2.0 |
| `Baseline` | mistral:latest | 2 | 3 | 3 | 2 | 2.5 |
| `Baseline` | qwen2.5:latest | 1 | 3 | 3 | 2 | 2.25 |
| `Solo temp` | llama3.1:latest | 1 | 2 | 3 | 2 | 2.0 |
| `Solo temp` | llama3.2:latest | 1 | 2 | 3 | 2 | 2.0 |
| `Solo temp` | mistral:latest | 1 | 1 | 2 | 2 | 1.5 |
| `Solo temp` | qwen2.5:latest | 0 | 2 | 3 | 3 | 2.0 |
| `Solo tokens` | llama3.1:latest | 2 | 3 | 3 | 2 | 2.5 |
| `Solo tokens` | llama3.2:latest | 1 | 2 | 3 | 2 | 2.0 |
| `Solo tokens` | mistral:latest | 2 | 3 | 3 | 2 | 2.5 |
| `Solo tokens` | qwen2.5:latest | 2 | 3 | 3 | 2 | 2.5 |
| `Temp + tokens` | llama3.1:latest | 1 | 1 | 2 | 2 | 1.5 |
| `Temp + tokens` | llama3.2:latest | 1 | 2 | 3 | 2 | 2.0 |
| `Temp + tokens` | mistral:latest | 2 | 3 | 3 | 2 | 2.5 |
| `Temp + tokens` | qwen2.5:latest | 1 | 3 | 3 | 2 | 2.25 |

#### TC-06 — creature / scene  *(contexto: medium)*

| Configuración | Modelo | D1 | D2 | D3 | D4 | Avg |
|---|---|---|---|---|---|---|
| `Baseline` | llama3.1:latest | 1 | 2 | 3 | 2 | 2.0 |
| `Baseline` | llama3.2:latest | 1 | 2 | 2 | 3 | 2.0 |
| `Baseline` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 |
| `Baseline` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 |
| `Solo temp` | llama3.1:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Solo temp` | llama3.2:latest | 1 | 2 | 3 | 2 | 2.0 |
| `Solo temp` | mistral:latest | 1 | 2 | 2 | 3 | 2.0 |
| `Solo temp` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 |
| `Solo tokens` | llama3.1:latest | 2 | 2 | 2 | 2 | 2.0 |
| `Solo tokens` | llama3.2:latest | 1 | 2 | 3 | 2 | 2.0 |
| `Solo tokens` | mistral:latest | 1 | 2 | 3 | 2 | 2.0 |
| `Solo tokens` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 |
| `Temp + tokens` | llama3.1:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Temp + tokens` | llama3.2:latest | 1 | 2 | 2 | 2 | 1.75 |
| `Temp + tokens` | mistral:latest | 1 | 2 | 2 | 3 | 2.0 |
| `Temp + tokens` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 |

#### TC-07 — location / extended_description  *(contexto: rich)*

| Configuración | Modelo | D1 | D2 | D3 | D4 | Avg |
|---|---|---|---|---|---|---|
| `Baseline` | llama3.1:latest | 2 | 2 | 3 | 3 | 2.5 |
| `Baseline` | llama3.2:latest | 1 | 2 | 2 | 3 | 2.0 |
| `Baseline` | mistral:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Baseline` | qwen2.5:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Solo temp` | llama3.1:latest | 2 | 3 | 3 | 2 | 2.5 |
| `Solo temp` | llama3.2:latest | 1 | 2 | 3 | 2 | 2.0 |
| `Solo temp` | mistral:latest | 1 | 2 | 3 | 3 | 2.25 |
| `Solo temp` | qwen2.5:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Solo tokens` | llama3.1:latest | 2 | 3 | 3 | 2 | 2.5 |
| `Solo tokens` | llama3.2:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Solo tokens` | mistral:latest | 2 | 3 | 3 | 2 | 2.5 |
| `Solo tokens` | qwen2.5:latest | 2 | 3 | 3 | 3 | 2.75 |
| `Temp + tokens` | llama3.1:latest | 1 | 2 | 3 | 2 | 2.0 |
| `Temp + tokens` | llama3.2:latest | 1 | 2 | 2 | 3 | 2.0 |
| `Temp + tokens` | mistral:latest | 1 | 2 | 2 | 3 | 2.0 |
| `Temp + tokens` | qwen2.5:latest | 2 | 3 | 3 | 2 | 2.5 |

#### TC-08 — location / scene  *(contexto: medium)*

| Configuración | Modelo | D1 | D2 | D3 | D4 | Avg |
|---|---|---|---|---|---|---|
| `Baseline` | llama3.1:latest | 2 | 2 | 3 | 2 | 2.25 |
| `Baseline` | llama3.2:latest | 2 | 3 | 2 | 2 | 2.25 |
| `Baseline` | mistral:latest | 2 | 3 | 2 | 2 | 2.25 |
| `Baseline` | qwen2.5:latest | 2 | 3 | 2 | 2 | 2.25 |
| `Solo temp` | llama3.1:latest | 2 | 3 | 2 | 2 | 2.25 |
| `Solo temp` | llama3.2:latest | 2 | 3 | 2 | 2 | 2.25 |
| `Solo temp` | mistral:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Solo temp` | qwen2.5:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Solo tokens` | llama3.1:latest | 2 | 2 | 3 | 2 | 2.25 |
| `Solo tokens` | llama3.2:latest | 2 | 2 | 2 | 3 | 2.25 |
| `Solo tokens` | mistral:latest | 2 | 2 | 2 | 2 | 2.0 |
| `Solo tokens` | qwen2.5:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Temp + tokens` | llama3.1:latest | 2 | 3 | 2 | 2 | 2.25 |
| `Temp + tokens` | llama3.2:latest | 2 | 2 | 2 | 3 | 2.25 |
| `Temp + tokens` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 |
| `Temp + tokens` | qwen2.5:latest | 2 | 3 | 2 | 3 | 2.5 |

#### TC-09 — faction / backstory  *(contexto: sparse)*

| Configuración | Modelo | D1 | D2 | D3 | D4 | Avg |
|---|---|---|---|---|---|---|
| `Baseline` | llama3.1:latest | 2 | 2 | 3 | 2 | 2.25 |
| `Baseline` | llama3.2:latest | 2 | 3 | 2 | 2 | 2.25 |
| `Baseline` | mistral:latest | 2 | 3 | 2 | 2 | 2.25 |
| `Baseline` | qwen2.5:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Solo temp` | llama3.1:latest | 2 | 3 | 2 | 2 | 2.25 |
| `Solo temp` | llama3.2:latest | 2 | 2 | 3 | 2 | 2.25 |
| `Solo temp` | mistral:latest | 2 | 2 | 2 | 3 | 2.25 |
| `Solo temp` | qwen2.5:latest | 2 | 3 | 2 | 2 | 2.25 |
| `Solo tokens` | llama3.1:latest | 2 | 2 | 3 | 2 | 2.25 |
| `Solo tokens` | llama3.2:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Solo tokens` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 |
| `Solo tokens` | qwen2.5:latest | 2 | 2 | 2 | 3 | 2.25 |
| `Temp + tokens` | llama3.1:latest | 2 | 3 | 3 | 2 | 2.5 |
| `Temp + tokens` | llama3.2:latest | 2 | 3 | 2 | 2 | 2.25 |
| `Temp + tokens` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 |
| `Temp + tokens` | qwen2.5:latest | 2 | 2 | 2 | 3 | 2.25 |

#### TC-10 — item / backstory  *(contexto: sparse)*

| Configuración | Modelo | D1 | D2 | D3 | D4 | Avg |
|---|---|---|---|---|---|---|
| `Baseline` | llama3.1:latest | 3 | 3 | 3 | 3 | 3.0 |
| `Baseline` | llama3.2:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Baseline` | mistral:latest | 3 | 2 | 3 | 2 | 2.5 |
| `Baseline` | qwen2.5:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Solo temp` | llama3.1:latest | 2 | 2 | 3 | 3 | 2.5 |
| `Solo temp` | llama3.2:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Solo temp` | mistral:latest | 3 | 3 | 3 | 3 | 3.0 |
| `Solo temp` | qwen2.5:latest | 2 | 3 | 3 | 2 | 2.5 |
| `Solo tokens` | llama3.1:latest | 2 | 3 | 2 | 3 | 2.5 |
| `Solo tokens` | llama3.2:latest | 2 | 2 | 2 | 3 | 2.25 |
| `Solo tokens` | mistral:latest | 3 | 2 | 3 | 2 | 2.5 |
| `Solo tokens` | qwen2.5:latest | 3 | 3 | 2 | 3 | 2.75 |
| `Temp + tokens` | llama3.1:latest | 3 | 3 | 3 | 2 | 2.75 |
| `Temp + tokens` | llama3.2:latest | 2 | 2 | 3 | 2 | 2.25 |
| `Temp + tokens` | mistral:latest | 3 | 2 | 3 | 2 | 2.5 |
| `Temp + tokens` | qwen2.5:latest | 3 | 3 | 3 | 2 | 2.75 |

---
## 7. Decisión recomendada

| Umbral | Significado |
|---|---|
| Δ ≥ 0.30 | ✅ Implementar — mejora sustancial |
| 0.10 ≤ Δ < 0.30 | 🟡 Considerar — mejora marginal |
| \|Δ\| < 0.10 | ⚪ Neutral — sin diferencia significativa |
| Δ < −0.10 | ❌ Descartar — regresión |

### llama3.2:latest

- `Solo temp`: ⚪ **NEUTRAL** (Δ+0.04)
- `Solo tokens`: ⚪ **NEUTRAL** (Δ+0.00)
- `Temp + tokens`: ⚪ **NEUTRAL** (Δ-0.08)

### llama3.1:latest

- `Solo temp`: ⚪ **NEUTRAL** (Δ-0.06)
- `Solo tokens`: ⚪ **NEUTRAL** (Δ-0.03)
- `Temp + tokens`: ⚪ **NEUTRAL** (Δ-0.08)

### qwen2.5:latest

- `Solo temp`: ⚪ **NEUTRAL** (Δ-0.05)
- `Solo tokens`: 🟡 **CONSIDERAR** (Δ+0.12)
- `Temp + tokens`: ⚪ **NEUTRAL** (Δ+0.05)

### mistral:latest

- `Solo temp`: ⚪ **NEUTRAL** (Δ-0.08)
- `Solo tokens`: ⚪ **NEUTRAL** (Δ-0.05)
- `Temp + tokens`: ⚪ **NEUTRAL** (Δ-0.05)

---
*Reporte generado por `evaluations/llm_params_harness/reporter.py`*