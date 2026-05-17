$ claude -p "Analiza este pipeline RAG de un worldbuilding tool. Evalúa: calidad del chunking para textos de lore (personajes,
  localizaciones), si la búsqueda por similitud tiene parámetros sensatos, posibles cuellos de botella en latencia, y si los prompts al LLM están bien estructurados para generar contenido de ficción."
Aquí tienes el análisis completo del pipeline RAG:

---

## Análisis del Pipeline RAG — Loremaster

### 1. Chunking

**Configuración actual:** `chunk_size=512` chars, `chunk_overlap=50` chars, `RecursiveCharacterTextSplitter`.

**Problema crítico — truncación silenciosa en el embedding:**
`paraphrase-multilingual-MiniLM-L12-v2` tiene un límite de **128 tokens**. Un chunk de 512 caracteres de lore en español genera ~100-160 tokens fácilmente. `sentence-transformers` trunca sin avisar: el final del chunk desaparece del embedding. Una descripción de personaje que dice "...y fue traicionado por su hermano en la batalla de X" puede perder ese detalle clave.

**Fix inmediato:** Reducir `chunk_size` a **~400 chars** (~80-90 tokens), que deja margen para el tokenizer. Alternativamente, cambiar el modelo de embedding por uno con ventana más larga (`all-MiniLM-L6-v2` tiene el mismo límite; `all-mpnet-base-v2` llega a 384 tokens).

**Overlap insuficiente para narrativa:**
`overlap=50` chars es ~10% del chunk. Una oración de transición entre dos párrafos de lore mide 80-120 chars. Con 50 de overlap, una idea que cruza el límite queda partida sin contexto en ambos chunks. Para texto narrativo, **150-200 chars** de overlap es más sensato.

**Lo que sí está bien:**
Los separadores `["\n\n", "\n", ". ", " ", ""]` son correctos para prosa: primero rompe por párrafos, luego por oraciones. Esto evita partir en mitad de una frase.

---

### 2. Búsqueda por Similitud

**Configuración actual:** `top_k=4`, `score_threshold=0.3`, distancia coseno.

**score_threshold=0.3 es demasiado permisivo:**
Para `MiniLM-L12-v2`, una similitud coseno de 0.3 es "vagamente relacionado". En worldbuilding, si el usuario pregunta por "la motivación de Kira", chunks con similitud 0.3 pueden ser sobre otro personaje de la misma colección que comparte vocabulario temático. Ese contexto contamina la generación. **0.45-0.5** es un umbral más defensivo para lore específico.

**top_k=4 puede ser escaso para consultas abiertas:**
Una pregunta como "¿qué eventos marcaron la historia del reino?" puede necesitar chunks de varios documentos distintos. Con 4 chunks × ~400 chars = ~1600 chars de contexto, cabe bien en el prompt, pero para queries amplias **6-8 chunks** daría más cobertura sin saturar el LLM.

**No hay metadata en el contexto recuperado:**
Los chunks se inyectan como texto plano. El LLM no sabe de qué documento viene cada fragmento ni su posición en el original. Añadir una cabecera mínima (`[Doc: "Crónica del Norte", párr. 3]`) ayudaría al LLM a ponderar fuentes contradictorias entre documentos.

---

### 3. Cuellos de Botella en Latencia

**El más grave: LLM síncrono con semáforo=1 en FastAPI async.**

```python
# rag_pipeline.py
with _llm_semaphore:           # threading.Semaphore(1)
    answer = chain.invoke(...)  # bloquea el hilo
```

`chain.invoke()` es síncrono y bloquea el thread de uvicorn durante toda la inferencia. Con `llama3.2:latest` generando hasta 2000 tokens en CPU/GPU de consumidor, eso son **20-60 segundos por llamada**. El segundo usuario en llegar espera bloqueado en el semáforo. La solución es mover las llamadas LLM a un executor:

```python
# Patrón correcto para FastAPI
loop = asyncio.get_event_loop()
answer = await loop.run_in_executor(None, lambda: chain.invoke(...))
```

**Sin caché de embeddings de consulta:**
Cada query recalcula el embedding de la pregunta. MiniLM es rápido (~5ms en CPU), pero es trabajo evitable para consultas repetidas. Un `functools.lru_cache` sobre el hash de la query sería suficiente.

**Ingesta síncrona de embeddings:**
`_embedding_model.encode(chunks, batch_size=32)` en el background task es correcto (no bloquea la respuesta HTTP), pero si se sube un PDF de 100 páginas, el proceso de encoding puede tardar 10-30 segundos y acaparar CPU durante la inferencia LLM concurrente.

**Resumen de latencias estimadas (hardware local mid-range):**

| Paso | Tiempo estimado |
|---|---|
| Extracción de texto | <1s |
| Embedding de query | 5-20ms |
| Búsqueda Qdrant | <10ms |
| Inferencia LLM (2000 tokens) | 20-90s |
| **Total percibido por usuario** | **20-90s** |

El LLM domina absolutamente. El resto es ruido.

---

### 4. Prompts al LLM

**Prompt genérico (RAG query libre):**

```
Eres un asistente experto en narrativa y worldbuilding.
Usa la información del contexto para responder.
Si el contexto es insuficiente, genera con lo disponible.
Extensión: 2-3 párrafos.
<context>...</context>
<question>...</question>
```

**Problema:** "Si el contexto es insuficiente, genera con lo disponible" instruye explícitamente al LLM a alucinar. Para un query de tipo *"¿Qué dijo el rey en la batalla?"* con contexto insuficiente, el LLM inventará un discurso que puede contradecir el lore establecido. Esta instrucción tiene sentido para generación creativa, pero no para recuperación de hechos del mundo. Deberían ser dos rutas con prompts distintos, o al menos dos instrucciones condicionales según si el contexto es suficiente.

**Prompts de entidad (backstory, scene, chapter...):**

Esto está bien diseñado. Separar por categoría con restricciones específicas (tiempo verbal, scope, extensión) es exactamente lo correcto para worldbuilding. La inyección de `extra_context` con la descripción actual del personaje antes del RAG context es un toque inteligente para mantener coherencia.

**Problemas concretos:**

1. **`max_tokens=2000` es insuficiente para `chapter`** (6-10 párrafos narrativos). Un capítulo de ficción mínimo son 800-1500 palabras ≈ 1000-2000 tokens solo de output. El LLM puede quedarse a mitad de oración. Para la categoría `chapter` debería aumentarse a **3000-4000 tokens** como mínimo.

2. **`temperature=0.7` es fija para todas las categorías.** `backstory` y `extended_description` se beneficiarían de una temperatura más baja (0.5-0.6) para generar contenido más coherente con el lore recuperado. `scene` y `chapter` pueden subir a 0.8-0.9 para mayor creatividad. Una temperatura por categoría mejoraría la calidad percibida.

3. **Sin few-shot examples.** Los prompts definen el *qué* pero no el *cómo* estilísticamente. Un ejemplo de 3-4 líneas del tipo de prosa esperada en el system prompt anclaría el registro narrativo (épico, oscuro, humorístico) que probablemente varía por colección/campaña.

4. **`llama3.2:latest` recibe el prompt como texto plano**, no usando su chat template. La librería `langchain-ollama` con `OllamaLLM` hace raw completion, no chat completion. `llama3.2` fue entrenado con un formato de chat específico (`<|system|>`, `<|user|>`, `<|assistant|>`). Usar `ChatOllama` con mensajes separados en lugar de `OllamaLLM` con texto plano probablemente mejoraría la calidad de las respuestas.

---

### Priorización de Fixes

| Prioridad | Problema | Impacto | Esfuerzo | Estado |
|---|---|---|---|---|
| 🔴 Alta | LLM síncrono bloqueando uvicorn | Latencia/escalabilidad | Bajo (run_in_executor) | ⏳ Pendiente |
| 🔴 Alta | Truncación silenciosa en embedding (512 chars > 128 tokens) | Calidad RAG | Bajo (cambiar chunk_size) | ✅ Aplicado — chunk_size=400 (rag_params_harness 2026-05-16) |
| 🟡 Media | Usar `ChatOllama` en lugar de `OllamaLLM` | Calidad generación | Bajo | ❌ Descartado — genera finales conversacionales incompatibles con frontend no-chat |
| 🟡 Media | `max_tokens=2000` insuficiente para `chapter` | Calidad generación | Bajo | ❌ N/A — `chapter` eliminado como categoría (feature separado) |
| 🟡 Media | `score_threshold=0.3` demasiado permisivo | Relevancia contexto | Mínimo | ❌ Descartado — rag_params_harness 2026-05-16: threshold≥0.35 elimina 58-85% del retrieval en este corpus |
| 🟡 Media | `chunk_overlap=50` insuficiente para narrativa | Calidad RAG | Bajo | ✅ Aplicado — chunk_overlap=150 (rag_params_harness 2026-05-16) |
| 🟢 Baja | Temperature por categoría | Calidad generación | Bajo | ❌ Descartado — llm_params_harness (2026-05-16): Δ neutral en 4 modelos, no justifica complejidad |
| 🟢 Baja | Metadata de fuente en contexto recuperado | Coherencia | Medio | ❌ Descartado — metadata_harness (2026-05-16): Δ máximo +0.10, D5 queda en 1.0-1.1/3.0; modelos 3-7B ignoran las cabeceras |

---

### Decisiones tomadas — llm_params_harness (2026-05-16)

Evaluación de 4 configuraciones (baseline / solo temp / solo tokens / ambos) × 4 modelos (llama3.2, llama3.1, qwen2.5, mistral) con gemma2:9b como juez. 16 runs, 10 TC por run.

**Resultados:**

| Config | llama3.2 | llama3.1 | qwen2.5* | mistral |
|---|---|---|---|---|
| Baseline | 2.28 | 2.33 | 1.90 | 2.35 |
| Solo temp (factual=0.55, scene=0.85) | 2.27 | 2.27 | 1.85 | 2.27 |
| Solo tokens (factual=1200, scene=2500) | 2.23 | 2.30 | 2.02 | 2.30 |
| Temp + tokens | 2.15 | 2.25 | 1.95 | 2.30 |

*qwen2.5 con scores artificialmente bajos por fallos de parseo del juez en algunos TC.

**Conclusión:** ninguna variación supera el baseline de forma significativa (Δ máximo +0.04, todos dentro del rango de ruido). La temperatura y num_predict por categoría no justifican la complejidad adicional. Valores de referencia guardados en `evaluations/llm_params_harness/runner.py` (`_FACTUAL_TEMPERATURE=0.55`, `_CREATIVE_TEMPERATURE=0.85`).

**Decisión:** mantener `temperature=0.7` y `max_tokens=2000` uniformes para todas las categorías.

---

### Decisiones tomadas — rag_params_harness (2026-05-16)

Evaluación de 6 configuraciones × 4 modelos con gemma2:9b como juez. 24 runs, 10 TC por run. Métrica principal: D1 (adherencia al contexto) + chunks/query.

**Configuraciones evaluadas:**

| Config | chunk_size | chunk_overlap | threshold | Chunks/q | MaxSim avg |
|---|---|---|---|---|---|
| baseline | 512 | 50 | 0.30 | 1.9 | 0.261 |
| chunks_only | 400 | 150 | 0.30 | 2.1 | 0.313 |
| threshold_only | 512 | 50 | 0.45 | 0.2 | 0.048 |
| both (chunks+threshold) | 400 | 150 | 0.45 | 0.3 | 0.142 |
| threshold_035 | 512 | 50 | 0.35 | 0.8 | 0.165 |
| both_035 | 400 | 150 | 0.35 | 1.5 | 0.218 |

**Resultados (modelos fiables: llama3.2, mistral):**

| Config | llama3.2 | mistral | Chunks/q |
|---|---|---|---|
| baseline | 2.15 | 2.17 | 1.9 |
| **chunks_only** | 2.05 | **2.40** | **2.1** |
| threshold_035 | 2.10 | 2.27 | 0.8 |
| both_035 | 2.12 | 2.27 | 1.5 |
| threshold_only (0.45) | 2.17 | 2.33 | 0.2 |
| both (0.45) | 2.35 | 2.33 | 0.3 |

*Nota: los scores altos de `threshold_only` y `both` con threshold=0.45 son un artefacto del juez: con 0.2 chunks/query el LLM genera sin contexto RAG y el juez puntúa la generación libre, no la fidelidad al lore.*

**Conclusiones:**
- `chunk_size=400`: corrección técnica obligatoria — 512 chars genera 100-160 tokens en español, excediendo el límite de 128 tokens del modelo de embedding. MaxSim mejora +20% (0.261→0.313) con chunks más cortos.
- `chunk_overlap=150`: mejora cobertura narrativa en límites de chunk (una oración de transición mide 80-120 chars; con 50 de overlap quedaba partida).
- `threshold=0.30`: mantener — threshold≥0.35 elimina el 58% del retrieval, threshold≥0.45 elimina el 85%. Corpus con similitudes bajas (maxsim típico 0.30-0.49).
- `top_k=4`: mantener — con chunks de 400 chars, 4 chunks = ~1 600 chars de contexto, dentro del prompt.

**Decisión:** `chunk_size=400`, `chunk_overlap=150`, `threshold=0.30`, `top_k=4`. Aplicado en `config/__init__.py`, `.env.example`, `LIMITERS.md` y `CLAUDE.md`.

---

### Decisiones tomadas — metadata_harness (2026-05-16)

Evaluación de 3 configuraciones de formato de contexto × 2 modelos con gemma2:9b como juez. 6 runs, 10 TC por run. Corpus: 2 documentos (golden_seed.txt + golden_seed_2.txt, 34 chunks). 8/10 TCs recuperaron chunks de ambos archivos simultáneamente.

**Configuraciones evaluadas:**
- `baseline`: sin cabeceras de fuente (comportamiento actual de producción)
- `meta_name`: `[Fuente: "archivo.txt"]` por chunk
- `meta_full`: `[Fuente: "archivo.txt" · fragmento N · relevancia X.XX]` por chunk

**Resultados:**

| Config | llama3.2 | mistral | D5 avg | Δ global |
|---|---|---|---|---|
| baseline | 1.94 | 1.94 | 1.0 | — |
| meta_name | 2.04 | 1.98 | 1.0 | +0.07 |
| meta_full | 2.02 | 2.04 | 1.1 | +0.07 |

**Conclusiones:**
- Δ máximo entre configs: +0.10 (llama3.2 meta_name vs baseline). Umbral de adopción definido: Δ D1 ≥ +0.20 o Δ D5 ≥ +0.50. No se alcanza ninguno.
- D5 (uso de fuente) se mantiene en 1.0 con todas las configs y sube a 1.1 únicamente con `meta_full` — ambos modelos no aprovechan las cabeceras de fuente para atribuir información en la generación.
- La señal es consistente entre modelos: llama3.2 y mistral muestran el mismo patrón plano, descartando ruido de un único modelo.
- El límite no es el tamaño del corpus sino la capacidad del modelo: con 8/10 TCs multi-fuente el escenario ideal se dio, y la mejora fue marginal de todas formas. Modelos 3-7B no tienen suficiente capacidad de razonamiento sobre metadata de contexto.
- Re-evaluar si el proyecto migra a un modelo con mayor ventana de contexto y capacidad de atribución (≥13B o API externa).

**Decisión:** no implementar cabeceras de fuente en `search_context`. `retrieve_context` permanece sin cambios.