# Evaluacion de Metadata en Contexto RAG -- cabeceras de fuente

*Generado: 2026-05-16 21:21*

## Indice

1. [Corpus y configuraciones](#1-corpus-y-configuraciones)
2. [Score global por config y modelo](#2-score-global-por-config-y-modelo)
3. [D5 — uso de fuente por config](#3-d5--uso-de-fuente-por-config)
4. [Multi-source vs single-source TCs](#4-multi-source-vs-single-source-tcs)
5. [Dimensiones D1-D5 por config (todos los modelos)](#5-dimensiones-d1-d5-por-config)
6. [Detalle por modelo](#6-detalle-por-modelo)
7. [Decision](#7-decision)

## 1. Corpus y configuraciones

**Corpus multi-documento:**

- `golden_seed.txt` — 15 chunks
- `golden_seed_2.txt` — 19 chunks
- Total indexado: 34 chunks (chunk=400, overlap=150, threshold=0.30, top_k=4)

**Configuraciones evaluadas:**

| Config | Descripcion |
|---|---|
| `baseline` | Baseline (sin headers) |
| `meta_name` | meta_name [Fuente: archivo] |
| `meta_full` | meta_full [Fuente: archivo · frag · rel] |

**Modelos evaluados:** `llama3.2:latest`, `mistral:latest`

**Juez:** `gemma2:9b` (D1-D5, escala 0-3)

**Rubrica D5 (uso de fuente):** Evalua si el texto generado distingue o atribuye
informacion a distintos documentos cuando el contexto incluye cabeceras de fuente.
Para baseline (sin cabeceras), mide si el LLM muestra conciencia de multiples perspectivas.

## 2. Score global por config y modelo

| Config | llama3.2:latest | mistral:latest | Avg modelos |
|---|---|---|---|
| **Baseline (sin headers)** | 1.94 | 1.94 | **1.94** |
| **meta_name [Fuente: archivo]** | 2.04 | 1.98 | **2.01** |
| **meta_full [Fuente: archivo · frag · rel]** | 2.02 | 2.04 | **2.03** |

**Delta vs baseline:**

| Config | llama3.2:latest | mistral:latest ||
|---|---|---|---|
| **meta_name [Fuente: archivo]** | +0.1 | +0.04 ||
| **meta_full [Fuente: archivo · frag · rel]** | +0.08 | +0.1 ||

## 3. D5 — uso de fuente por config

D5 es la dimension clave del harness: mide si el LLM usa las cabeceras de fuente
para distinguir informacion de distintos documentos.

| Config | llama3.2:latest (D5) | mistral:latest (D5) | Avg D5 |
|---|---|---|---|
| **Baseline (sin headers)** | 1.0 | 1.0 | **1.0** |
| **meta_name [Fuente: archivo]** | 1.0 | 1.0 | **1.0** |
| **meta_full [Fuente: archivo · frag · rel]** | 1.1 | 1.1 | **1.1** |

## 4. Multi-source vs single-source TCs

Separacion de TCs segun si el retrieval recupero chunks de ambos archivos (multi)
o de un unico archivo. Los TCs multi-source son el escenario donde las cabeceras
aportan mas valor.

**Baseline (sin headers):**

| Modelo | Multi-source score | Single-source score | D5 (multi) | TCs multi |
|---|---|---|---|---|
| llama3.2:latest | 1.87 | 2.05 | 1.0 | 8/10 |
| mistral:latest | 1.87 | 2.05 | 1.0 | 8/10 |

**meta_name [Fuente: archivo]:**

| Modelo | Multi-source score | Single-source score | D5 (multi) | TCs multi |
|---|---|---|---|---|
| llama3.2:latest | 2.03 | 2.05 | 1.0 | 8/10 |
| mistral:latest | 1.97 | 2.0 | 1.0 | 8/10 |

**meta_full [Fuente: archivo · frag · rel]:**

| Modelo | Multi-source score | Single-source score | D5 (multi) | TCs multi |
|---|---|---|---|---|
| llama3.2:latest | 2.03 | 2.0 | 1.17 | 8/10 |
| mistral:latest | 2.03 | 2.05 | 1.17 | 8/10 |

## 5. Dimensiones D1-D5 por config

**Baseline (sin headers):**

| Modelo | D1 | D2 | D3 | D4 | D5 | Avg |
|---|---|---|---|---|---|---|
| llama3.2:latest | 1.9 | 2.1 | 2.7 | 2.0 | 1.0 | **1.94** |
| mistral:latest | 2.1 | 1.9 | 2.8 | 1.9 | 1.0 | **1.94** |

**meta_name [Fuente: archivo]:**

| Modelo | D1 | D2 | D3 | D4 | D5 | Avg |
|---|---|---|---|---|---|---|
| llama3.2:latest | 2.0 | 2.2 | 3.0 | 2.0 | 1.0 | **2.04** |
| mistral:latest | 2.0 | 1.9 | 3.0 | 2.0 | 1.0 | **1.98** |

**meta_full [Fuente: archivo · frag · rel]:**

| Modelo | D1 | D2 | D3 | D4 | D5 | Avg |
|---|---|---|---|---|---|---|
| llama3.2:latest | 2.0 | 2.2 | 2.7 | 2.1 | 1.1 | **2.02** |
| mistral:latest | 2.1 | 2.1 | 2.9 | 2.0 | 1.1 | **2.04** |

## 6. Detalle por modelo

### llama3.2:latest

| TC | source_signal | baseline (avg) | baseline (D5) | meta_name (avg) | meta_name (D5) | meta_full (avg) | meta_full (D5) | chunks | multi_src |
|---|---|---|---|---|---|---|---|---|---|
| TC-01 | multi | 2.0 | 1 | 2.0 | 1 | 2.0 | 1 | 4 | si |
| TC-02 | multi | 1.6 | 1 | 2.0 | 1 | 2.0 | 1 | 4 | si |
| TC-03 | multi | 2.0 | 1 | 2.0 | 1 | 2.2 | 2 | 4 | si |
| TC-04 | multi | 2.0 | 1 | 2.2 | 1 | 2.2 | 1 | 4 | si |
| TC-05 | multi | 1.6 | 1 | 2.0 | 1 | 1.8 | 1 | 4 | si |
| TC-06 | multi | 2.0 | 1 | 2.0 | 1 | 2.0 | 1 | 4 | si |
| TC-07 | seed1_heavy | 2.0 | 1 | 2.2 | 1 | 2.0 | 1 | 4 | si |
| TC-08 | seed1_heavy | 2.0 | 1 | 2.0 | 1 | 2.0 | 1 | 4 | si |
| TC-09 | seed2_heavy | 2.0 | 1 | 2.0 | 1 | 2.0 | 1 | 1 | no |
| TC-10 | seed2_heavy | 2.2 | 1 | 2.0 | 1 | 2.0 | 1 | 4 | no |

### mistral:latest

| TC | source_signal | baseline (avg) | baseline (D5) | meta_name (avg) | meta_name (D5) | meta_full (avg) | meta_full (D5) | chunks | multi_src |
|---|---|---|---|---|---|---|---|---|---|
| TC-01 | multi | 1.8 | 1 | 2.0 | 1 | 2.0 | 1 | 4 | si |
| TC-02 | multi | 1.8 | 1 | 1.8 | 1 | 2.0 | 1 | 4 | si |
| TC-03 | multi | 2.0 | 1 | 2.0 | 1 | 2.2 | 2 | 4 | si |
| TC-04 | multi | 2.0 | 1 | 2.0 | 1 | 2.0 | 1 | 4 | si |
| TC-05 | multi | 1.6 | 1 | 2.0 | 1 | 2.0 | 1 | 4 | si |
| TC-06 | multi | 2.0 | 1 | 2.0 | 1 | 2.0 | 1 | 4 | si |
| TC-07 | seed1_heavy | 2.2 | 1 | 2.0 | 1 | 2.2 | 1 | 4 | si |
| TC-08 | seed1_heavy | 2.0 | 1 | 2.0 | 1 | 2.0 | 1 | 4 | si |
| TC-09 | seed2_heavy | 2.0 | 1 | 2.0 | 1 | 2.0 | 1 | 1 | no |
| TC-10 | seed2_heavy | 2.0 | 1 | 2.0 | 1 | 2.0 | 1 | 4 | no |

## 7. Decision

> *Seccion a completar manualmente tras analizar los resultados.*

**Pregunta principal:** ¿Añadir cabeceras de fuente al contexto RAG mejora la calidad
de la generacion cuando el corpus es multi-documento?

**Opciones de implementacion (si la evaluacion es positiva):**

- **Opcion A — filename en payload Qdrant (ingest time):**
  Almacenar `filename` junto con `doc_id` al indexar chunks. Retrieve recupera el
  nombre directamente sin query adicional. Simple, sin overhead en query time.
  Tradeoff: si el documento se renombra despues de la ingesta, el payload queda desactualizado.

- **Opcion B — lookup DB en query time:**
  `search_context` recibe los `doc_id` UUID de los resultados Qdrant y hace un
  SELECT a la tabla `documents` para recuperar el `filename`. Siempre actualizado.
  Tradeoff: una query DB adicional por llamada RAG.

**Umbral de adopcion sugerido:** Δ D1 >= +0.2 O Δ D5 >= +0.5 respecto a baseline
en TCs multi-source, con al menos un modelo fiable (mistral o llama3.2).

| Metrica | Resultado | Umbral | Decision |
|---|---|---|---|
| Δ D1 (meta_name vs baseline, multi-source) | _pendiente_ | >= +0.2 | _pendiente_ |
| Δ D1 (meta_full vs baseline, multi-source) | _pendiente_ | >= +0.2 | _pendiente_ |
| Δ D5 (meta_name vs baseline) | _pendiente_ | >= +0.5 | _pendiente_ |
| Δ D5 (meta_full vs baseline) | _pendiente_ | >= +0.5 | _pendiente_ |
