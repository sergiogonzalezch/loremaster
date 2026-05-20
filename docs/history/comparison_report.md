# Image Prompt Harness — Comparativa por modelo

Métricas evaluadas sobre el output de `build_combined_prompt()`:

| Criterio | Descripción |
| --- | --- |
| **Tipo correcto** | El primer token del output coincide con el tipo de entidad esperado |
| **En inglés** | El output no contiene palabras función ni colores en español |

## Resultados

| Modelo | Temp | Tipo correcto | En inglés |
| --- | --- | --- | --- |
| llama3.2:latest | 0.7 | 10/12 (83.3%) | 11/12 (91.7%) |
| mistral:latest | 0.7 | 10/12 (83.3%) | 12/12 (100.0%) |
| llama3.1:latest | 0.7 | 8/12 (66.7%) | 11/12 (91.7%) |
| qwen2.5:latest | 0.7 | 10/12 (83.3%) | 11/12 (91.7%) |
| gemma2:9b | 0.7 | 10/12 (83.3%) | 11/12 (91.7%) |
| qwen3.5:9b | 0.7 | 0/12 (0.0%) | 0/12 (0.0%) |

## Detalle por caso

### llama3.2:latest (temp=0.7)

| Caso | Tipo | Inglés | Error |
| --- | --- | --- | --- |
| tc-01 | OK | OK | — |
| tc-02 | FAIL | OK | — |
| tc-03 | OK | OK | — |
| tc-04 | OK | OK | — |
| tc-05 | FAIL | OK | — |
| tc-06 | OK | OK | — |
| tc-07 | OK | OK | — |
| tc-08 | OK | OK | — |
| tc-09 | OK | OK | — |
| tc-10 | OK | OK | — |
| tc-11 | OK | OK | — |
| tc-12 | OK | FAIL | — |

### mistral:latest (temp=0.7)

| Caso | Tipo | Inglés | Error |
| --- | --- | --- | --- |
| tc-01 | OK | OK | — |
| tc-02 | OK | OK | — |
| tc-03 | OK | OK | — |
| tc-04 | OK | OK | — |
| tc-05 | FAIL | OK | — |
| tc-06 | OK | OK | — |
| tc-07 | OK | OK | — |
| tc-08 | OK | OK | — |
| tc-09 | OK | OK | — |
| tc-10 | OK | OK | — |
| tc-11 | FAIL | OK | — |
| tc-12 | OK | OK | — |

### llama3.1:latest (temp=0.7)

| Caso | Tipo | Inglés | Error |
| --- | --- | --- | --- |
| tc-01 | OK | OK | — |
| tc-02 | OK | OK | — |
| tc-03 | OK | OK | — |
| tc-04 | FAIL | FAIL | — |
| tc-05 | FAIL | OK | — |
| tc-06 | OK | OK | — |
| tc-07 | FAIL | OK | — |
| tc-08 | OK | OK | — |
| tc-09 | OK | OK | — |
| tc-10 | OK | OK | — |
| tc-11 | FAIL | OK | — |
| tc-12 | OK | OK | — |

### qwen2.5:latest (temp=0.7)

| Caso | Tipo | Inglés | Error |
| --- | --- | --- | --- |
| tc-01 | OK | OK | — |
| tc-02 | OK | OK | — |
| tc-03 | OK | OK | — |
| tc-04 | FAIL | OK | — |
| tc-05 | FAIL | OK | — |
| tc-06 | OK | OK | — |
| tc-07 | OK | OK | — |
| tc-08 | OK | FAIL | — |
| tc-09 | OK | OK | — |
| tc-10 | OK | OK | — |
| tc-11 | OK | OK | — |
| tc-12 | OK | OK | — |

### gemma2:9b (temp=0.7)

| Caso | Tipo | Inglés | Error |
| --- | --- | --- | --- |
| tc-01 | FAIL | FAIL | HTTPConnectionPool(host='localhost', port=11434): Read timed out. (read timeout=120) |
| tc-02 | OK | OK | — |
| tc-03 | OK | OK | — |
| tc-04 | OK | OK | — |
| tc-05 | OK | OK | — |
| tc-06 | OK | OK | — |
| tc-07 | OK | OK | — |
| tc-08 | OK | OK | — |
| tc-09 | OK | OK | — |
| tc-10 | OK | OK | — |
| tc-11 | FAIL | OK | — |
| tc-12 | OK | OK | — |

### qwen3.5:9b (temp=0.7)

| Caso | Tipo | Inglés | Error |
| --- | --- | --- | --- |
| tc-01 | FAIL | FAIL | — |
| tc-02 | FAIL | FAIL | HTTPConnectionPool(host='localhost', port=11434): Read timed out. (read timeout=120) |
| tc-03 | FAIL | FAIL | HTTPConnectionPool(host='localhost', port=11434): Read timed out. (read timeout=120) |
| tc-04 | FAIL | FAIL | HTTPConnectionPool(host='localhost', port=11434): Read timed out. (read timeout=120) |
| tc-05 | FAIL | FAIL | HTTPConnectionPool(host='localhost', port=11434): Read timed out. (read timeout=120) |
| tc-06 | FAIL | FAIL | HTTPConnectionPool(host='localhost', port=11434): Read timed out. (read timeout=120) |
| tc-07 | FAIL | FAIL | — |
| tc-08 | FAIL | FAIL | — |
| tc-09 | FAIL | FAIL | — |
| tc-10 | FAIL | FAIL | — |
| tc-11 | FAIL | FAIL | — |
| tc-12 | FAIL | FAIL | — |
