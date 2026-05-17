# Evaluacion de Parametros RAG -- chunk_size, chunk_overlap y rag_score_threshold
**Generado:** 2026-05-16 19:53  
**Juez:** gemma2:9b  
**Runs:** 24

---
## Resumen ejecutivo

> La dimension clave es **D1 (Adherencia al contexto)**: mide si el RAG aporta informacion util.
> Un threshold mas alto (0.45) recupera menos chunks pero mas relevantes.
> Un chunk mas pequeno (400) preserva mejor el semantico ante el limite de 128 tokens del modelo de embeddings.

- **llama3.2:latest**: mejor config = `both` -> avg=2.35/3.0 (D+0.20 vs baseline) [OK]
- **llama3.1:latest**: mejor config = `chunks_only` -> avg=0.57/3.0 (D+0.07 vs baseline) [~]
- **qwen2.5:latest**: mejor config = `chunks_only` -> avg=1.27/3.0 (D+0.20 vs baseline) [OK]
- **mistral:latest**: mejor config = `chunks_only` -> avg=2.4/3.0 (D+0.23 vs baseline) [OK]

---
## 1. Ranking global

| # | Config | Modelo | D1 | D2 | D3 | D4 | Promedio | Chunks/q | MaxSim |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `Solo chunks` | mistral:latest | 1.9 | 2.7 | 2.9 | 2.1 | **2.4** | 2.1 | 0.313 |
| 2 | `Chunks + threshold` | llama3.2:latest | 1.9 | 2.6 | 2.8 | 2.1 | **2.35** | 0.3 | 0.142 |
| 3 | `Solo threshold` | mistral:latest | 1.9 | 2.4 | 2.9 | 2.1 | **2.33** | 0.2 | 0.048 |
| 4 | `Chunks + threshold` | mistral:latest | 1.8 | 2.6 | 2.7 | 2.2 | **2.33** | 0.3 | 0.142 |
| 5 | `threshold_035` | mistral:latest | 1.9 | 2.3 | 2.8 | 2.1 | **2.27** | 0.8 | 0.165 |
| 6 | `both_035` | mistral:latest | 1.9 | 2.3 | 2.8 | 2.1 | **2.27** | 1.5 | 0.218 |
| 7 | `Solo threshold` | llama3.2:latest | 1.7 | 2.4 | 2.7 | 1.9 | **2.17** | 0.2 | 0.048 |
| 8 | `Baseline` | mistral:latest | 1.8 | 2.2 | 2.5 | 2.2 | **2.17** | 1.9 | 0.261 |
| 9 | `Baseline` | llama3.2:latest | 1.5 | 2.3 | 2.5 | 2.3 | **2.15** | 1.9 | 0.261 |
| 10 | `both_035` | llama3.2:latest | 1.5 | 2.4 | 2.2 | 2.4 | **2.12** | 1.5 | 0.218 |
| 11 | `threshold_035` | llama3.2:latest | 1.5 | 2.4 | 2.5 | 2.0 | **2.1** | 0.8 | 0.165 |
| 12 | `Solo chunks` | llama3.2:latest | 1.4 | 2.3 | 2.5 | 2.0 | **2.05** | 2.1 | 0.313 |
| 13 | `Solo chunks` | qwen2.5:latest | 1.1 | 1.5 | 1.5 | 1.0 | **1.27** | 2.1 | 0.313 |
| 14 | `Baseline` | qwen2.5:latest | 0.9 | 1.1 | 1.4 | 0.9 | **1.07** | 1.9 | 0.261 |
| 15 | `Solo threshold` | qwen2.5:latest | 0.8 | 0.9 | 1.3 | 0.6 | **0.9** | 0.2 | 0.048 |
| 16 | `threshold_035` | qwen2.5:latest | 0.8 | 0.8 | 1.4 | 0.6 | **0.9** | 0.8 | 0.165 |
| 17 | `both_035` | qwen2.5:latest | 0.8 | 0.8 | 1.0 | 0.6 | **0.8** | 1.5 | 0.218 |
| 18 | `Solo chunks` | llama3.1:latest | 0.4 | 0.5 | 0.8 | 0.6 | **0.57** | 2.1 | 0.313 |
| 19 | `Chunks + threshold` | qwen2.5:latest | 0.6 | 0.6 | 0.6 | 0.5 | **0.57** | 0.3 | 0.142 |
| 20 | `Baseline` | llama3.1:latest | 0.5 | 0.2 | 0.9 | 0.4 | **0.5** | 1.9 | 0.261 |
| 21 | `threshold_035` | llama3.1:latest | 0.4 | 0.2 | 0.3 | 0.6 | **0.38** | 0.8 | 0.165 |
| 22 | `Solo threshold` | llama3.1:latest | 0.4 | 0.2 | 0.3 | 0.3 | **0.3** | 0.2 | 0.048 |
| 23 | `Chunks + threshold` | llama3.1:latest | 0.3 | 0.0 | 0.0 | 0.6 | **0.23** | 0.3 | 0.142 |
| 24 | `both_035` | llama3.1:latest | 0.2 | 0.0 | 0.0 | 0.5 | **0.17** | 1.5 | 0.218 |

---
## 2. Estadisticas de recuperacion RAG

> `threshold_only` y `both` deben recuperar menos chunks (filtro mas estricto).
> Si `chunks_only` mejora D1, confirma que chunks mas pequenos preservan mejor el semantico.

| Config | Modelo | Chunks indexados | Chunks/query (avg) | Min | Max | MaxSim avg |
|---|---|---|---|---|---|---|
| `Baseline` | llama3.1:latest | 10 | 1.9 | 0 | 4 | 0.261 |
| `Baseline` | llama3.2:latest | 10 | 1.9 | 0 | 4 | 0.261 |
| `Baseline` | mistral:latest | 10 | 1.9 | 0 | 4 | 0.261 |
| `Baseline` | qwen2.5:latest | 10 | 1.9 | 0 | 4 | 0.261 |
| `Solo chunks` | llama3.1:latest | 15 | 2.1 | 0 | 4 | 0.313 |
| `Solo chunks` | llama3.2:latest | 15 | 2.1 | 0 | 4 | 0.313 |
| `Solo chunks` | mistral:latest | 15 | 2.1 | 0 | 4 | 0.313 |
| `Solo chunks` | qwen2.5:latest | 15 | 2.1 | 0 | 4 | 0.313 |
| `Solo threshold` | llama3.1:latest | 10 | 0.2 | 0 | 2 | 0.048 |
| `Solo threshold` | llama3.2:latest | 10 | 0.2 | 0 | 2 | 0.048 |
| `Solo threshold` | mistral:latest | 10 | 0.2 | 0 | 2 | 0.048 |
| `Solo threshold` | qwen2.5:latest | 10 | 0.2 | 0 | 2 | 0.048 |
| `Chunks + threshold` | llama3.1:latest | 15 | 0.3 | 0 | 1 | 0.142 |
| `Chunks + threshold` | llama3.2:latest | 15 | 0.3 | 0 | 1 | 0.142 |
| `Chunks + threshold` | mistral:latest | 15 | 0.3 | 0 | 1 | 0.142 |
| `Chunks + threshold` | qwen2.5:latest | 15 | 0.3 | 0 | 1 | 0.142 |
| `threshold_035` | llama3.1:latest | 10 | 0.8 | 0 | 3 | 0.165 |
| `both_035` | llama3.1:latest | 15 | 1.5 | 0 | 4 | 0.218 |
| `threshold_035` | llama3.2:latest | 10 | 0.8 | 0 | 3 | 0.165 |
| `both_035` | llama3.2:latest | 15 | 1.5 | 0 | 4 | 0.218 |
| `threshold_035` | mistral:latest | 10 | 0.8 | 0 | 3 | 0.165 |
| `both_035` | mistral:latest | 15 | 1.5 | 0 | 4 | 0.218 |
| `threshold_035` | qwen2.5:latest | 10 | 0.8 | 0 | 3 | 0.165 |
| `both_035` | qwen2.5:latest | 15 | 1.5 | 0 | 4 | 0.218 |

---
## 3. Comparativa vs baseline por modelo (foco D1)

> [+] = mejora >= 0.20 | [-] = regresion >= 0.20

### llama3.2:latest

| Dimension | Baseline | Solo chunks | D | Solo threshold | D | Chunks + threshold | D |
|---|---|--- | --- | --- | --- | --- | ---|
| **D1 -- Adherencia ctx** | 1.5 | 1.4 | -0.1 | 1.7 | +0.2 [+] | 1.9 | +0.4 [+] |
| D2 -- Especificidad | 2.3 | 2.3 | = | 2.4 | +0.1 | 2.6 | +0.3 [+] |
| D3 -- Categoria | 2.5 | 2.5 | = | 2.7 | +0.2 [+] | 2.8 | +0.3 [+] |
| D4 -- Completitud | 2.3 | 2.0 | -0.3 [-] | 1.9 | -0.4 [-] | 2.1 | -0.2 [-] |
| **Promedio** | 2.15 | 2.05 | -0.1 | 2.17 | +0.02 | 2.35 | +0.2 [+] |

### llama3.1:latest

| Dimension | Baseline | Solo chunks | D | Solo threshold | D | Chunks + threshold | D |
|---|---|--- | --- | --- | --- | --- | ---|
| **D1 -- Adherencia ctx** | 0.5 | 0.4 | -0.1 | 0.4 | -0.1 | 0.3 | -0.2 [-] |
| D2 -- Especificidad | 0.2 | 0.5 | +0.3 [+] | 0.2 | = | 0.0 | -0.2 [-] |
| D3 -- Categoria | 0.9 | 0.8 | -0.1 | 0.3 | -0.6 [-] | 0.0 | -0.9 [-] |
| D4 -- Completitud | 0.4 | 0.6 | +0.2 [+] | 0.3 | -0.1 | 0.6 | +0.2 [+] |
| **Promedio** | 0.5 | 0.57 | +0.07 | 0.3 | -0.2 [-] | 0.23 | -0.27 [-] |

### qwen2.5:latest

| Dimension | Baseline | Solo chunks | D | Solo threshold | D | Chunks + threshold | D |
|---|---|--- | --- | --- | --- | --- | ---|
| **D1 -- Adherencia ctx** | 0.9 | 1.1 | +0.2 [+] | 0.8 | -0.1 | 0.6 | -0.3 [-] |
| D2 -- Especificidad | 1.1 | 1.5 | +0.4 [+] | 0.9 | -0.2 [-] | 0.6 | -0.5 [-] |
| D3 -- Categoria | 1.4 | 1.5 | +0.1 | 1.3 | -0.1 | 0.6 | -0.8 [-] |
| D4 -- Completitud | 0.9 | 1.0 | +0.1 | 0.6 | -0.3 [-] | 0.5 | -0.4 [-] |
| **Promedio** | 1.07 | 1.27 | +0.2 [+] | 0.9 | -0.17 | 0.57 | -0.5 [-] |

### mistral:latest

| Dimension | Baseline | Solo chunks | D | Solo threshold | D | Chunks + threshold | D |
|---|---|--- | --- | --- | --- | --- | ---|
| **D1 -- Adherencia ctx** | 1.8 | 1.9 | +0.1 | 1.9 | +0.1 | 1.8 | = |
| D2 -- Especificidad | 2.2 | 2.7 | +0.5 [+] | 2.4 | +0.2 [+] | 2.6 | +0.4 [+] |
| D3 -- Categoria | 2.5 | 2.9 | +0.4 [+] | 2.9 | +0.4 [+] | 2.7 | +0.2 [+] |
| D4 -- Completitud | 2.2 | 2.1 | -0.1 | 2.1 | -0.1 | 2.2 | = |
| **Promedio** | 2.17 | 2.4 | +0.23 [+] | 2.33 | +0.16 | 2.33 | +0.16 |

---
## 4. Analisis por categoria

### backstory

| Config | Modelo | D1 | D2 | D3 | D4 | Promedio |
|---|---|---|---|---|---|---|
| `Chunks + threshold` | llama3.2:latest | 2.0 | 2.75 | 3.0 | 2.25 | **2.5** |
| `Chunks + threshold` | mistral:latest | 2.0 | 3.0 | 2.5 | 2.5 | **2.5** |
| `Solo chunks` | mistral:latest | 2.0 | 2.75 | 3.0 | 2.0 | **2.44** |
| `Solo threshold` | llama3.2:latest | 2.0 | 2.5 | 3.0 | 2.0 | **2.38** |
| `Solo threshold` | mistral:latest | 2.0 | 2.5 | 3.0 | 2.0 | **2.38** |
| `Baseline` | llama3.2:latest | 1.75 | 2.5 | 2.5 | 2.5 | **2.31** |
| `Solo chunks` | llama3.2:latest | 1.5 | 2.5 | 3.0 | 2.25 | **2.31** |
| `Baseline` | mistral:latest | 1.75 | 2.25 | 2.5 | 2.5 | **2.25** |
| `threshold_035` | mistral:latest | 1.75 | 2.25 | 2.5 | 2.25 | **2.19** |
| `threshold_035` | llama3.2:latest | 1.5 | 2.5 | 2.5 | 2.0 | **2.12** |
| `both_035` | llama3.2:latest | 1.5 | 2.5 | 1.75 | 2.75 | **2.12** |
| `both_035` | mistral:latest | 1.75 | 2.0 | 2.75 | 2.0 | **2.12** |
| `Solo chunks` | qwen2.5:latest | 1.25 | 1.5 | 1.5 | 1.0 | **1.31** |
| `Baseline` | qwen2.5:latest | 0.75 | 0.5 | 1.5 | 0.75 | **0.88** |
| `threshold_035` | llama3.1:latest | 0.75 | 0.5 | 0.75 | 1.25 | **0.81** |
| `Baseline` | llama3.1:latest | 0.75 | 0.25 | 1.5 | 0.5 | **0.75** |
| `Solo chunks` | llama3.1:latest | 0.5 | 0.5 | 1.5 | 0.5 | **0.75** |
| `threshold_035` | qwen2.5:latest | 0.5 | 0.0 | 1.25 | 0.0 | **0.44** |
| `Solo threshold` | qwen2.5:latest | 0.5 | 0.0 | 1.0 | 0.0 | **0.38** |
| `Chunks + threshold` | llama3.1:latest | 0.25 | 0.0 | 0.0 | 1.0 | **0.31** |
| `both_035` | llama3.1:latest | 0.0 | 0.0 | 0.0 | 0.75 | **0.19** |
| `both_035` | qwen2.5:latest | 0.5 | 0.0 | 0.25 | 0.0 | **0.19** |
| `Solo threshold` | llama3.1:latest | 0.0 | 0.0 | 0.0 | 0.25 | **0.06** |
| `Chunks + threshold` | qwen2.5:latest | 0.25 | 0.0 | 0.0 | 0.0 | **0.06** |

### extended_description

| Config | Modelo | D1 | D2 | D3 | D4 | Promedio |
|---|---|---|---|---|---|---|
| `Solo chunks` | qwen2.5:latest | 2.0 | 3.0 | 3.0 | 2.0 | **2.5** |
| `Solo threshold` | qwen2.5:latest | 2.0 | 3.0 | 3.0 | 2.0 | **2.5** |
| `Chunks + threshold` | llama3.2:latest | 2.0 | 2.67 | 3.0 | 2.0 | **2.42** |
| `threshold_035` | mistral:latest | 2.0 | 2.67 | 3.0 | 2.0 | **2.42** |
| `both_035` | mistral:latest | 2.0 | 2.67 | 3.0 | 2.0 | **2.42** |
| `threshold_035` | qwen2.5:latest | 2.0 | 2.67 | 3.0 | 2.0 | **2.42** |
| `both_035` | qwen2.5:latest | 2.0 | 2.67 | 3.0 | 2.0 | **2.42** |
| `Chunks + threshold` | mistral:latest | 2.0 | 2.33 | 3.0 | 2.0 | **2.33** |
| `Baseline` | qwen2.5:latest | 1.67 | 3.0 | 2.67 | 2.0 | **2.33** |
| `both_035` | llama3.2:latest | 1.67 | 2.33 | 3.0 | 2.0 | **2.25** |
| `Solo chunks` | mistral:latest | 1.67 | 2.33 | 3.0 | 2.0 | **2.25** |
| `Solo threshold` | mistral:latest | 1.67 | 2.33 | 3.0 | 2.0 | **2.25** |
| `Solo threshold` | llama3.2:latest | 1.67 | 2.67 | 2.33 | 2.0 | **2.17** |
| `Baseline` | llama3.2:latest | 1.33 | 2.33 | 2.67 | 2.0 | **2.08** |
| `threshold_035` | llama3.2:latest | 1.33 | 2.33 | 2.67 | 2.0 | **2.08** |
| `Baseline` | mistral:latest | 1.67 | 2.33 | 2.33 | 2.0 | **2.08** |
| `Solo chunks` | llama3.2:latest | 1.33 | 2.0 | 2.0 | 2.0 | **1.83** |
| `Chunks + threshold` | qwen2.5:latest | 1.67 | 2.0 | 2.0 | 1.67 | **1.83** |
| `Solo threshold` | llama3.1:latest | 0.67 | 0.67 | 1.0 | 0.67 | **0.75** |
| `Baseline` | llama3.1:latest | 0.33 | 0.33 | 1.0 | 0.67 | **0.58** |
| `Chunks + threshold` | llama3.1:latest | 0.33 | 0.0 | 0.0 | 0.67 | **0.25** |
| `both_035` | llama3.1:latest | 0.33 | 0.0 | 0.0 | 0.67 | **0.25** |
| `Solo chunks` | llama3.1:latest | 0.0 | 0.0 | 0.0 | 0.67 | **0.17** |
| `threshold_035` | llama3.1:latest | 0.0 | 0.0 | 0.0 | 0.33 | **0.08** |

### scene

| Config | Modelo | D1 | D2 | D3 | D4 | Promedio |
|---|---|---|---|---|---|---|
| `Solo chunks` | mistral:latest | 2.0 | 3.0 | 2.67 | 2.33 | **2.5** |
| `Solo threshold` | mistral:latest | 2.0 | 2.33 | 2.67 | 2.33 | **2.33** |
| `both_035` | mistral:latest | 2.0 | 2.33 | 2.67 | 2.33 | **2.33** |
| `threshold_035` | mistral:latest | 2.0 | 2.0 | 3.0 | 2.0 | **2.25** |
| `Baseline` | mistral:latest | 2.0 | 2.0 | 2.67 | 2.0 | **2.17** |
| `Chunks + threshold` | llama3.2:latest | 1.67 | 2.33 | 2.33 | 2.0 | **2.08** |
| `threshold_035` | llama3.2:latest | 1.67 | 2.33 | 2.33 | 2.0 | **2.08** |
| `Chunks + threshold` | mistral:latest | 1.33 | 2.33 | 2.67 | 2.0 | **2.08** |
| `Baseline` | llama3.2:latest | 1.33 | 2.0 | 2.33 | 2.33 | **2.0** |
| `both_035` | llama3.2:latest | 1.33 | 2.33 | 2.0 | 2.33 | **2.0** |
| `Solo chunks` | llama3.2:latest | 1.33 | 2.33 | 2.33 | 1.67 | **1.92** |
| `Solo threshold` | llama3.2:latest | 1.33 | 2.0 | 2.67 | 1.67 | **1.92** |
| `Solo chunks` | llama3.1:latest | 0.67 | 1.0 | 0.67 | 0.67 | **0.75** |
| `Solo threshold` | llama3.1:latest | 0.67 | 0.0 | 0.0 | 0.0 | **0.17** |
| `Baseline` | llama3.1:latest | 0.33 | 0.0 | 0.0 | 0.0 | **0.08** |
| `Chunks + threshold` | llama3.1:latest | 0.33 | 0.0 | 0.0 | 0.0 | **0.08** |
| `threshold_035` | llama3.1:latest | 0.33 | 0.0 | 0.0 | 0.0 | **0.08** |
| `both_035` | llama3.1:latest | 0.33 | 0.0 | 0.0 | 0.0 | **0.08** |
| `Baseline` | qwen2.5:latest | 0.33 | 0.0 | 0.0 | 0.0 | **0.08** |
| `Solo chunks` | qwen2.5:latest | 0.0 | 0.0 | 0.0 | 0.0 | **0.0** |
| `Solo threshold` | qwen2.5:latest | 0.0 | 0.0 | 0.0 | 0.0 | **0.0** |
| `Chunks + threshold` | qwen2.5:latest | 0.0 | 0.0 | 0.0 | 0.0 | **0.0** |
| `threshold_035` | qwen2.5:latest | 0.0 | 0.0 | 0.0 | 0.0 | **0.0** |
| `both_035` | qwen2.5:latest | 0.0 | 0.0 | 0.0 | 0.0 | **0.0** |

---
## 5. Analisis por modelo

### llama3.2:latest

| Config | D1 | D2 | D3 | D4 | Promedio | vs baseline | Chunks/q |
|---|---|---|---|---|---|---|---|
| `Baseline` | 1.5 | 2.3 | 2.5 | 2.3 | **2.15** | -- | 1.9 |
| `Solo chunks` | 1.4 | 2.3 | 2.5 | 2.0 | **2.05** | -0.1 | 2.1 |
| `Solo threshold` | 1.7 | 2.4 | 2.7 | 1.9 | **2.17** | +0.02 | 0.2 |
| `Chunks + threshold` | 1.9 | 2.6 | 2.8 | 2.1 | **2.35** | +0.2 [+] | 0.3 |
| `threshold_035` | 1.5 | 2.4 | 2.5 | 2.0 | **2.1** | -0.05 | 0.8 |
| `both_035` | 1.5 | 2.4 | 2.2 | 2.4 | **2.12** | -0.03 | 1.5 |

### llama3.1:latest

| Config | D1 | D2 | D3 | D4 | Promedio | vs baseline | Chunks/q |
|---|---|---|---|---|---|---|---|
| `Baseline` | 0.5 | 0.2 | 0.9 | 0.4 | **0.5** | -- | 1.9 |
| `Solo chunks` | 0.4 | 0.5 | 0.8 | 0.6 | **0.57** | +0.07 | 2.1 |
| `Solo threshold` | 0.4 | 0.2 | 0.3 | 0.3 | **0.3** | -0.2 [-] | 0.2 |
| `Chunks + threshold` | 0.3 | 0.0 | 0.0 | 0.6 | **0.23** | -0.27 [-] | 0.3 |
| `threshold_035` | 0.4 | 0.2 | 0.3 | 0.6 | **0.38** | -0.12 | 0.8 |
| `both_035` | 0.2 | 0.0 | 0.0 | 0.5 | **0.17** | -0.33 [-] | 1.5 |

### qwen2.5:latest

| Config | D1 | D2 | D3 | D4 | Promedio | vs baseline | Chunks/q |
|---|---|---|---|---|---|---|---|
| `Baseline` | 0.9 | 1.1 | 1.4 | 0.9 | **1.07** | -- | 1.9 |
| `Solo chunks` | 1.1 | 1.5 | 1.5 | 1.0 | **1.27** | +0.2 [+] | 2.1 |
| `Solo threshold` | 0.8 | 0.9 | 1.3 | 0.6 | **0.9** | -0.17 | 0.2 |
| `Chunks + threshold` | 0.6 | 0.6 | 0.6 | 0.5 | **0.57** | -0.5 [-] | 0.3 |
| `threshold_035` | 0.8 | 0.8 | 1.4 | 0.6 | **0.9** | -0.17 | 0.8 |
| `both_035` | 0.8 | 0.8 | 1.0 | 0.6 | **0.8** | -0.27 [-] | 1.5 |

### mistral:latest

| Config | D1 | D2 | D3 | D4 | Promedio | vs baseline | Chunks/q |
|---|---|---|---|---|---|---|---|
| `Baseline` | 1.8 | 2.2 | 2.5 | 2.2 | **2.17** | -- | 1.9 |
| `Solo chunks` | 1.9 | 2.7 | 2.9 | 2.1 | **2.4** | +0.23 [+] | 2.1 |
| `Solo threshold` | 1.9 | 2.4 | 2.9 | 2.1 | **2.33** | +0.16 | 0.2 |
| `Chunks + threshold` | 1.8 | 2.6 | 2.7 | 2.2 | **2.33** | +0.16 | 0.3 |
| `threshold_035` | 1.9 | 2.3 | 2.8 | 2.1 | **2.27** | +0.1 | 0.8 |
| `both_035` | 1.9 | 2.3 | 2.8 | 2.1 | **2.27** | +0.1 | 1.5 |

---
## 6. Scores detallados por caso

#### TC-01 -- character / backstory  *(contexto: rich)*

| Config | Modelo | D1 | D2 | D3 | D4 | Avg | Chunks | MaxSim |
|---|---|---|---|---|---|---|---|---|
| `Baseline` | llama3.1:latest | 1 | 0 | 0 | 1 | 0.5 | 1 | 0.302 |
| `Baseline` | llama3.2:latest | 2 | 2 | 3 | 2 | 2.25 | 1 | 0.302 |
| `Baseline` | mistral:latest | 2 | 3 | 3 | 2 | 2.5 | 1 | 0.302 |
| `Baseline` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 1 | 0.302 |
| `Solo chunks` | llama3.1:latest | 0 | 0 | 0 | 1 | 0.25 | 3 | 0.396 |
| `Solo chunks` | llama3.2:latest | 2 | 3 | 3 | 2 | 2.5 | 3 | 0.396 |
| `Solo chunks` | mistral:latest | 2 | 3 | 3 | 2 | 2.5 | 3 | 0.396 |
| `Solo chunks` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 3 | 0.396 |
| `Solo threshold` | llama3.1:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `Solo threshold` | llama3.2:latest | 2 | 2 | 3 | 2 | 2.25 | 0 | 0.0 |
| `Solo threshold` | mistral:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `Solo threshold` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `Chunks + threshold` | llama3.1:latest | 1 | 0 | 0 | 1 | 0.5 | 0 | 0.0 |
| `Chunks + threshold` | llama3.2:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `Chunks + threshold` | mistral:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `Chunks + threshold` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `threshold_035` | llama3.1:latest | 1 | 0 | 0 | 1 | 0.5 | 0 | 0.0 |
| `both_035` | llama3.1:latest | 0 | 0 | 0 | 1 | 0.25 | 2 | 0.396 |
| `threshold_035` | llama3.2:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `both_035` | llama3.2:latest | 2 | 3 | 2 | 3 | 2.5 | 2 | 0.396 |
| `threshold_035` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 | 0 | 0.0 |
| `both_035` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 | 2 | 0.396 |
| `threshold_035` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `both_035` | qwen2.5:latest | 1 | 0 | 0 | 0 | 0.25 | 2 | 0.396 |

#### TC-02 -- location / extended_description  *(contexto: rich)*

| Config | Modelo | D1 | D2 | D3 | D4 | Avg | Chunks | MaxSim |
|---|---|---|---|---|---|---|---|---|
| `Baseline` | llama3.1:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `Baseline` | llama3.2:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `Baseline` | mistral:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `Baseline` | qwen2.5:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `Solo chunks` | llama3.1:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `Solo chunks` | llama3.2:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `Solo chunks` | mistral:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `Solo chunks` | qwen2.5:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `Solo threshold` | llama3.1:latest | 2 | 2 | 3 | 2 | 2.25 | 0 | 0.0 |
| `Solo threshold` | llama3.2:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `Solo threshold` | mistral:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `Solo threshold` | qwen2.5:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `Chunks + threshold` | llama3.1:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `Chunks + threshold` | llama3.2:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `Chunks + threshold` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 | 0 | 0.0 |
| `Chunks + threshold` | qwen2.5:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `threshold_035` | llama3.1:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `both_035` | llama3.1:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `threshold_035` | llama3.2:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `both_035` | llama3.2:latest | 1 | 2 | 3 | 2 | 2.0 | 0 | 0.0 |
| `threshold_035` | mistral:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `both_035` | mistral:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `threshold_035` | qwen2.5:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `both_035` | qwen2.5:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |

#### TC-03 -- faction / backstory  *(contexto: rich)*

| Config | Modelo | D1 | D2 | D3 | D4 | Avg | Chunks | MaxSim |
|---|---|---|---|---|---|---|---|---|
| `Baseline` | llama3.1:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `Baseline` | llama3.2:latest | 2 | 3 | 2 | 3 | 2.5 | 0 | 0.0 |
| `Baseline` | mistral:latest | 2 | 3 | 2 | 3 | 2.5 | 0 | 0.0 |
| `Baseline` | qwen2.5:latest | 1 | 0 | 1 | 0 | 0.5 | 0 | 0.0 |
| `Solo chunks` | llama3.1:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `Solo chunks` | llama3.2:latest | 1 | 2 | 3 | 2 | 2.0 | 0 | 0.0 |
| `Solo chunks` | mistral:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `Solo chunks` | qwen2.5:latest | 1 | 0 | 0 | 0 | 0.25 | 0 | 0.0 |
| `Solo threshold` | llama3.1:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `Solo threshold` | llama3.2:latest | 2 | 2 | 3 | 2 | 2.25 | 0 | 0.0 |
| `Solo threshold` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 | 0 | 0.0 |
| `Solo threshold` | qwen2.5:latest | 1 | 0 | 1 | 0 | 0.5 | 0 | 0.0 |
| `Chunks + threshold` | llama3.1:latest | 0 | 0 | 0 | 1 | 0.25 | 0 | 0.0 |
| `Chunks + threshold` | llama3.2:latest | 2 | 2 | 3 | 2 | 2.25 | 0 | 0.0 |
| `Chunks + threshold` | mistral:latest | 2 | 3 | 2 | 3 | 2.5 | 0 | 0.0 |
| `Chunks + threshold` | qwen2.5:latest | 1 | 0 | 0 | 0 | 0.25 | 0 | 0.0 |
| `threshold_035` | llama3.1:latest | 1 | 0 | 0 | 1 | 0.5 | 0 | 0.0 |
| `both_035` | llama3.1:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `threshold_035` | llama3.2:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `both_035` | llama3.2:latest | 1 | 2 | 2 | 3 | 2.0 | 0 | 0.0 |
| `threshold_035` | mistral:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `both_035` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 | 0 | 0.0 |
| `threshold_035` | qwen2.5:latest | 1 | 0 | 1 | 0 | 0.5 | 0 | 0.0 |
| `both_035` | qwen2.5:latest | 1 | 0 | 1 | 0 | 0.5 | 0 | 0.0 |

#### TC-04 -- creature / scene  *(contexto: sparse)*

| Config | Modelo | D1 | D2 | D3 | D4 | Avg | Chunks | MaxSim |
|---|---|---|---|---|---|---|---|---|
| `Baseline` | llama3.1:latest | 0 | 0 | 0 | 0 | 0.0 | 3 | 0.349 |
| `Baseline` | llama3.2:latest | 1 | 2 | 2 | 3 | 2.0 | 3 | 0.349 |
| `Baseline` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 | 3 | 0.349 |
| `Baseline` | qwen2.5:latest | 1 | 0 | 0 | 0 | 0.25 | 3 | 0.349 |
| `Solo chunks` | llama3.1:latest | 0 | 0 | 0 | 0 | 0.0 | 2 | 0.347 |
| `Solo chunks` | llama3.2:latest | 1 | 3 | 2 | 2 | 2.0 | 2 | 0.347 |
| `Solo chunks` | mistral:latest | 2 | 3 | 2 | 3 | 2.5 | 2 | 0.347 |
| `Solo chunks` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 2 | 0.347 |
| `Solo threshold` | llama3.1:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `Solo threshold` | llama3.2:latest | 1 | 2 | 2 | 1 | 1.5 | 0 | 0.0 |
| `Solo threshold` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 | 0 | 0.0 |
| `Solo threshold` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `Chunks + threshold` | llama3.1:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `Chunks + threshold` | llama3.2:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `Chunks + threshold` | mistral:latest | 1 | 2 | 3 | 2 | 2.0 | 0 | 0.0 |
| `Chunks + threshold` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `threshold_035` | llama3.1:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `both_035` | llama3.1:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `threshold_035` | llama3.2:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `both_035` | llama3.2:latest | 1 | 2 | 2 | 1 | 1.5 | 0 | 0.0 |
| `threshold_035` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 | 0 | 0.0 |
| `both_035` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 | 0 | 0.0 |
| `threshold_035` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `both_035` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |

#### TC-05 -- item / backstory  *(contexto: irrelevant)*

| Config | Modelo | D1 | D2 | D3 | D4 | Avg | Chunks | MaxSim |
|---|---|---|---|---|---|---|---|---|
| `Baseline` | llama3.1:latest | 1 | 1 | 3 | 0 | 1.25 | 4 | 0.481 |
| `Baseline` | llama3.2:latest | 1 | 2 | 2 | 3 | 2.0 | 4 | 0.481 |
| `Baseline` | mistral:latest | 2 | 1 | 3 | 2 | 2.0 | 4 | 0.481 |
| `Baseline` | qwen2.5:latest | 1 | 0 | 3 | 0 | 1.0 | 4 | 0.481 |
| `Solo chunks` | llama3.1:latest | 1 | 1 | 3 | 0 | 1.25 | 4 | 0.473 |
| `Solo chunks` | llama3.2:latest | 1 | 2 | 3 | 2 | 2.0 | 4 | 0.473 |
| `Solo chunks` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 | 4 | 0.473 |
| `Solo chunks` | qwen2.5:latest | 2 | 3 | 3 | 2 | 2.5 | 4 | 0.473 |
| `Solo threshold` | llama3.1:latest | 0 | 0 | 0 | 1 | 0.25 | 2 | 0.481 |
| `Solo threshold` | llama3.2:latest | 2 | 3 | 3 | 2 | 2.5 | 2 | 0.481 |
| `Solo threshold` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 | 2 | 0.481 |
| `Solo threshold` | qwen2.5:latest | 1 | 0 | 3 | 0 | 1.0 | 2 | 0.481 |
| `Chunks + threshold` | llama3.1:latest | 0 | 0 | 0 | 1 | 0.25 | 1 | 0.473 |
| `Chunks + threshold` | llama3.2:latest | 2 | 3 | 3 | 3 | 2.75 | 1 | 0.473 |
| `Chunks + threshold` | mistral:latest | 2 | 3 | 2 | 3 | 2.5 | 1 | 0.473 |
| `Chunks + threshold` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 1 | 0.473 |
| `threshold_035` | llama3.1:latest | 0 | 0 | 1 | 1 | 0.5 | 3 | 0.481 |
| `both_035` | llama3.1:latest | 0 | 0 | 0 | 1 | 0.25 | 4 | 0.473 |
| `threshold_035` | llama3.2:latest | 1 | 2 | 3 | 2 | 2.0 | 3 | 0.481 |
| `both_035` | llama3.2:latest | 2 | 3 | 2 | 3 | 2.5 | 4 | 0.473 |
| `threshold_035` | mistral:latest | 1 | 1 | 2 | 2 | 1.5 | 3 | 0.481 |
| `both_035` | mistral:latest | 1 | 1 | 2 | 2 | 1.5 | 4 | 0.473 |
| `threshold_035` | qwen2.5:latest | 1 | 0 | 3 | 0 | 1.0 | 3 | 0.481 |
| `both_035` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 4 | 0.473 |

#### TC-06 -- character / backstory  *(contexto: rich)*

| Config | Modelo | D1 | D2 | D3 | D4 | Avg | Chunks | MaxSim |
|---|---|---|---|---|---|---|---|---|
| `Baseline` | llama3.1:latest | 1 | 0 | 3 | 1 | 1.25 | 4 | 0.359 |
| `Baseline` | llama3.2:latest | 2 | 3 | 3 | 2 | 2.5 | 4 | 0.359 |
| `Baseline` | mistral:latest | 1 | 2 | 2 | 3 | 2.0 | 4 | 0.359 |
| `Baseline` | qwen2.5:latest | 1 | 2 | 2 | 3 | 2.0 | 4 | 0.359 |
| `Solo chunks` | llama3.1:latest | 1 | 1 | 3 | 1 | 1.5 | 4 | 0.49 |
| `Solo chunks` | llama3.2:latest | 2 | 3 | 3 | 3 | 2.75 | 4 | 0.49 |
| `Solo chunks` | mistral:latest | 2 | 3 | 3 | 2 | 2.5 | 4 | 0.49 |
| `Solo chunks` | qwen2.5:latest | 2 | 3 | 3 | 2 | 2.5 | 4 | 0.49 |
| `Solo threshold` | llama3.1:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `Solo threshold` | llama3.2:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `Solo threshold` | mistral:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `Solo threshold` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `Chunks + threshold` | llama3.1:latest | 0 | 0 | 0 | 1 | 0.25 | 1 | 0.49 |
| `Chunks + threshold` | llama3.2:latest | 2 | 3 | 3 | 2 | 2.5 | 1 | 0.49 |
| `Chunks + threshold` | mistral:latest | 2 | 3 | 3 | 2 | 2.5 | 1 | 0.49 |
| `Chunks + threshold` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 1 | 0.49 |
| `threshold_035` | llama3.1:latest | 1 | 2 | 2 | 2 | 1.75 | 2 | 0.359 |
| `both_035` | llama3.1:latest | 0 | 0 | 0 | 1 | 0.25 | 4 | 0.49 |
| `threshold_035` | llama3.2:latest | 1 | 2 | 1 | 2 | 1.5 | 2 | 0.359 |
| `both_035` | llama3.2:latest | 1 | 2 | 1 | 2 | 1.5 | 4 | 0.49 |
| `threshold_035` | mistral:latest | 2 | 3 | 2 | 3 | 2.5 | 2 | 0.359 |
| `both_035` | mistral:latest | 2 | 3 | 3 | 2 | 2.5 | 4 | 0.49 |
| `threshold_035` | qwen2.5:latest | 0 | 0 | 1 | 0 | 0.25 | 2 | 0.359 |
| `both_035` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 4 | 0.49 |

#### TC-07 -- character / extended_description  *(contexto: rich)*

| Config | Modelo | D1 | D2 | D3 | D4 | Avg | Chunks | MaxSim |
|---|---|---|---|---|---|---|---|---|
| `Baseline` | llama3.1:latest | 0 | 0 | 0 | 1 | 0.25 | 1 | 0.308 |
| `Baseline` | llama3.2:latest | 1 | 1 | 2 | 2 | 1.5 | 1 | 0.308 |
| `Baseline` | mistral:latest | 1 | 2 | 1 | 2 | 1.5 | 1 | 0.308 |
| `Baseline` | qwen2.5:latest | 2 | 3 | 2 | 2 | 2.25 | 1 | 0.308 |
| `Solo chunks` | llama3.1:latest | 0 | 0 | 0 | 1 | 0.25 | 1 | 0.305 |
| `Solo chunks` | llama3.2:latest | 1 | 1 | 0 | 2 | 1.0 | 1 | 0.305 |
| `Solo chunks` | mistral:latest | 1 | 2 | 3 | 2 | 2.0 | 1 | 0.305 |
| `Solo chunks` | qwen2.5:latest | 2 | 3 | 3 | 2 | 2.5 | 1 | 0.305 |
| `Solo threshold` | llama3.1:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `Solo threshold` | llama3.2:latest | 1 | 2 | 1 | 2 | 1.5 | 0 | 0.0 |
| `Solo threshold` | mistral:latest | 1 | 2 | 3 | 2 | 2.0 | 0 | 0.0 |
| `Solo threshold` | qwen2.5:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `Chunks + threshold` | llama3.1:latest | 1 | 0 | 0 | 1 | 0.5 | 0 | 0.0 |
| `Chunks + threshold` | llama3.2:latest | 2 | 2 | 3 | 2 | 2.25 | 0 | 0.0 |
| `Chunks + threshold` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 | 0 | 0.0 |
| `Chunks + threshold` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `threshold_035` | llama3.1:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `both_035` | llama3.1:latest | 1 | 0 | 0 | 1 | 0.5 | 0 | 0.0 |
| `threshold_035` | llama3.2:latest | 1 | 1 | 2 | 2 | 1.5 | 0 | 0.0 |
| `both_035` | llama3.2:latest | 2 | 2 | 3 | 2 | 2.25 | 0 | 0.0 |
| `threshold_035` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 | 0 | 0.0 |
| `both_035` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 | 0 | 0.0 |
| `threshold_035` | qwen2.5:latest | 2 | 2 | 3 | 2 | 2.25 | 0 | 0.0 |
| `both_035` | qwen2.5:latest | 2 | 2 | 3 | 2 | 2.25 | 0 | 0.0 |

#### TC-08 -- character / scene  *(contexto: rich)*

| Config | Modelo | D1 | D2 | D3 | D4 | Avg | Chunks | MaxSim |
|---|---|---|---|---|---|---|---|---|
| `Baseline` | llama3.1:latest | 1 | 0 | 0 | 0 | 0.25 | 0 | 0.0 |
| `Baseline` | llama3.2:latest | 2 | 2 | 2 | 2 | 2.0 | 0 | 0.0 |
| `Baseline` | mistral:latest | 2 | 2 | 2 | 2 | 2.0 | 0 | 0.0 |
| `Baseline` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `Solo chunks` | llama3.1:latest | 2 | 3 | 2 | 2 | 2.25 | 1 | 0.302 |
| `Solo chunks` | llama3.2:latest | 2 | 2 | 2 | 1 | 1.75 | 1 | 0.302 |
| `Solo chunks` | mistral:latest | 2 | 3 | 3 | 2 | 2.5 | 1 | 0.302 |
| `Solo chunks` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 1 | 0.302 |
| `Solo threshold` | llama3.1:latest | 1 | 0 | 0 | 0 | 0.25 | 0 | 0.0 |
| `Solo threshold` | llama3.2:latest | 2 | 2 | 3 | 2 | 2.25 | 0 | 0.0 |
| `Solo threshold` | mistral:latest | 2 | 3 | 2 | 3 | 2.5 | 0 | 0.0 |
| `Solo threshold` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `Chunks + threshold` | llama3.1:latest | 1 | 0 | 0 | 0 | 0.25 | 0 | 0.0 |
| `Chunks + threshold` | llama3.2:latest | 2 | 2 | 3 | 2 | 2.25 | 0 | 0.0 |
| `Chunks + threshold` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 | 0 | 0.0 |
| `Chunks + threshold` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `threshold_035` | llama3.1:latest | 1 | 0 | 0 | 0 | 0.25 | 0 | 0.0 |
| `both_035` | llama3.1:latest | 1 | 0 | 0 | 0 | 0.25 | 0 | 0.0 |
| `threshold_035` | llama3.2:latest | 2 | 2 | 2 | 1 | 1.75 | 0 | 0.0 |
| `both_035` | llama3.2:latest | 2 | 3 | 2 | 3 | 2.5 | 0 | 0.0 |
| `threshold_035` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 | 0 | 0.0 |
| `both_035` | mistral:latest | 2 | 3 | 2 | 3 | 2.5 | 0 | 0.0 |
| `threshold_035` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `both_035` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |

#### TC-09 -- creature / extended_description  *(contexto: sparse)*

| Config | Modelo | D1 | D2 | D3 | D4 | Avg | Chunks | MaxSim |
|---|---|---|---|---|---|---|---|---|
| `Baseline` | llama3.1:latest | 1 | 1 | 3 | 1 | 1.5 | 2 | 0.385 |
| `Baseline` | llama3.2:latest | 1 | 3 | 3 | 2 | 2.25 | 2 | 0.385 |
| `Baseline` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 | 2 | 0.385 |
| `Baseline` | qwen2.5:latest | 1 | 3 | 3 | 2 | 2.25 | 2 | 0.385 |
| `Solo chunks` | llama3.1:latest | 0 | 0 | 0 | 1 | 0.25 | 2 | 0.368 |
| `Solo chunks` | llama3.2:latest | 1 | 2 | 3 | 2 | 2.0 | 2 | 0.368 |
| `Solo chunks` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 | 2 | 0.368 |
| `Solo chunks` | qwen2.5:latest | 2 | 3 | 3 | 2 | 2.5 | 2 | 0.368 |
| `Solo threshold` | llama3.1:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `Solo threshold` | llama3.2:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `Solo threshold` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 | 0 | 0.0 |
| `Solo threshold` | qwen2.5:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `Chunks + threshold` | llama3.1:latest | 0 | 0 | 0 | 1 | 0.25 | 0 | 0.0 |
| `Chunks + threshold` | llama3.2:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `Chunks + threshold` | mistral:latest | 2 | 3 | 3 | 2 | 2.5 | 0 | 0.0 |
| `Chunks + threshold` | qwen2.5:latest | 3 | 3 | 3 | 3 | 3.0 | 0 | 0.0 |
| `threshold_035` | llama3.1:latest | 0 | 0 | 0 | 1 | 0.25 | 1 | 0.385 |
| `both_035` | llama3.1:latest | 0 | 0 | 0 | 1 | 0.25 | 1 | 0.368 |
| `threshold_035` | llama3.2:latest | 1 | 3 | 3 | 2 | 2.25 | 1 | 0.385 |
| `both_035` | llama3.2:latest | 2 | 3 | 3 | 2 | 2.5 | 1 | 0.368 |
| `threshold_035` | mistral:latest | 2 | 3 | 3 | 2 | 2.5 | 1 | 0.385 |
| `both_035` | mistral:latest | 2 | 3 | 3 | 2 | 2.5 | 1 | 0.368 |
| `threshold_035` | qwen2.5:latest | 2 | 3 | 3 | 2 | 2.5 | 1 | 0.385 |
| `both_035` | qwen2.5:latest | 2 | 3 | 3 | 2 | 2.5 | 1 | 0.368 |

#### TC-10 -- character / scene  *(contexto: rich)*

| Config | Modelo | D1 | D2 | D3 | D4 | Avg | Chunks | MaxSim |
|---|---|---|---|---|---|---|---|---|
| `Baseline` | llama3.1:latest | 0 | 0 | 0 | 0 | 0.0 | 4 | 0.428 |
| `Baseline` | llama3.2:latest | 1 | 2 | 3 | 2 | 2.0 | 4 | 0.428 |
| `Baseline` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 | 4 | 0.428 |
| `Baseline` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 4 | 0.428 |
| `Solo chunks` | llama3.1:latest | 0 | 0 | 0 | 0 | 0.0 | 4 | 0.452 |
| `Solo chunks` | llama3.2:latest | 1 | 2 | 3 | 2 | 2.0 | 4 | 0.452 |
| `Solo chunks` | mistral:latest | 2 | 3 | 3 | 2 | 2.5 | 4 | 0.452 |
| `Solo chunks` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 4 | 0.452 |
| `Solo threshold` | llama3.1:latest | 1 | 0 | 0 | 0 | 0.25 | 0 | 0.0 |
| `Solo threshold` | llama3.2:latest | 1 | 2 | 3 | 2 | 2.0 | 0 | 0.0 |
| `Solo threshold` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 | 0 | 0.0 |
| `Solo threshold` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |
| `Chunks + threshold` | llama3.1:latest | 0 | 0 | 0 | 0 | 0.0 | 1 | 0.452 |
| `Chunks + threshold` | llama3.2:latest | 1 | 2 | 1 | 2 | 1.5 | 1 | 0.452 |
| `Chunks + threshold` | mistral:latest | 1 | 3 | 2 | 2 | 2.0 | 1 | 0.452 |
| `Chunks + threshold` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 1 | 0.452 |
| `threshold_035` | llama3.1:latest | 0 | 0 | 0 | 0 | 0.0 | 2 | 0.428 |
| `both_035` | llama3.1:latest | 0 | 0 | 0 | 0 | 0.0 | 4 | 0.452 |
| `threshold_035` | llama3.2:latest | 1 | 2 | 2 | 3 | 2.0 | 2 | 0.428 |
| `both_035` | llama3.2:latest | 1 | 2 | 2 | 3 | 2.0 | 4 | 0.452 |
| `threshold_035` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 | 2 | 0.428 |
| `both_035` | mistral:latest | 2 | 2 | 3 | 2 | 2.25 | 4 | 0.452 |
| `threshold_035` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 2 | 0.428 |
| `both_035` | qwen2.5:latest | 0 | 0 | 0 | 0 | 0.0 | 4 | 0.452 |

---
## 7. Decision recomendada

| Umbral | Significado |
|---|---|
| D1 mejora >= 0.20 | Implementar el cambio |
| |D1| < 0.20 | Neutral -- no justifica complejidad |
| D1 empeora >= 0.20 | Descartar |

### llama3.2:latest

- `Solo chunks`: [~] NEUTRAL (D1 -0.10, avg -0.10)
- `Solo threshold`: [OK] IMPLEMENTAR (D1 +0.20, avg +0.02)
- `Chunks + threshold`: [OK] IMPLEMENTAR (D1 +0.40, avg +0.20)

### llama3.1:latest

- `Solo chunks`: [~] NEUTRAL (D1 -0.10, avg +0.07)
- `Solo threshold`: [~] NEUTRAL (D1 -0.10, avg -0.20)
- `Chunks + threshold`: [X] DESCARTAR (D1 -0.20, avg -0.27)

### qwen2.5:latest

- `Solo chunks`: [OK] IMPLEMENTAR (D1 +0.20, avg +0.20)
- `Solo threshold`: [~] NEUTRAL (D1 -0.10, avg -0.17)
- `Chunks + threshold`: [X] DESCARTAR (D1 -0.30, avg -0.50)

### mistral:latest

- `Solo chunks`: [~] NEUTRAL (D1 +0.10, avg +0.23)
- `Solo threshold`: [~] NEUTRAL (D1 +0.10, avg +0.16)
- `Chunks + threshold`: [~] NEUTRAL (D1 +0.00, avg +0.16)

---
*Reporte generado por `evaluations/rag_params_harness/reporter.py`*