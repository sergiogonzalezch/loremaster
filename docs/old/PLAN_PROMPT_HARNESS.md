# Plan de Mejora: Prompts y Harness de Evaluación Multi-Modelo

## Contexto del proyecto

LoreMaster es una aplicación RAG para worldbuilding narrativo. El LLM genera contenido narrativo (backstory, escenas, capítulos) para entidades ficticias usando documentos del usuario como contexto. El stack es FastAPI + Ollama (llama3.2:latest y qwen3 4.9B Q4_K_M) + Qdrant + LangChain.

---

## Fase 1: Auditoría y refactor de prompt templates

### 1.1 Problemas identificados a resolver

**`backend/app/engine/llm.py`**

- La `_SAFETY_INSTRUCTION` está duplicada aquí y en `prompt_templates.py`. En el pipeline de generación de entidades ambas se ejecutan, consumiendo tokens innecesariamente y sesgando el tono hacia lo restrictivo.
- El separador entre contexto y pregunta usa coma inline (`CONTEXTO: {context}, PREGUNTA: {query}`) en lugar de separadores estructurales claros. Los modelos instrucción-tuned responden mejor a saltos de línea o etiquetas XML.
- No hay instrucción de formato ni longitud esperada en la respuesta. El modelo no sabe si debe responder en un párrafo o en varios.

**`backend/app/domain/prompt_templates.py`**

- `backstory` y `extended_description` son demasiado similares. El modelo no tiene señales claras para diferenciar el output: uno debería enfocarse en origen/historia y el otro en atributos/características presentes.
- `scene` y `chapter` no especifican estructura esperada. `chapter` debería indicar explícitamente inicio-desarrollo-cierre. `scene` debería indicar inmediatez y acción.
- `_ONLY_CONTEXT` en su forma actual hace que el modelo rechace generar cuando el contexto RAG es pobre, en lugar de generar con lo disponible e indicar las limitaciones.
- Ningún template especifica longitud objetivo, lo que resulta en outputs inconsistentes entre categorías.
- La instrucción de seguridad ocupa entre 80-100 tokens en cada llamada. Para el caso de uso narrativo de fantasía, la mayoría de ese bloque nunca se activa.

**`backend/app/engine/image_prompt_rules.py`**

- Los prompts de extracción superan las 200 palabras en varios casos. Modelos pequeños cuantizados tienden a ignorar instrucciones al final del prompt.
- Hay inconsistencia de idioma: instrucciones en inglés mezcladas con estructura en español. Esto puede causar cambios de idioma no deseados en el output.
- Las instrucciones de tipo `_NO_SKIP` y `_FORMAT_ATTRS` son redundantes entre sí y añaden ruido.

---

### 1.2 Reglas de negocio para el refactor de prompts

**Regla 1 — Separación de responsabilidades de seguridad**

La instrucción de seguridad debe existir en un único lugar del pipeline. Para el pipeline de generación de entidades, aplicarla solo en `prompt_templates.py`. En `llm.py` (usado para RAG libre) mantener una versión reducida. No duplicar.

**Regla 2 — Diferenciación clara por categoría**

Cada categoría debe producir un tipo de texto reconociblemente distinto:

- `backstory`: tiempo pasado, enfoque en origen, motivaciones y eventos formativos. Sin descripción física detallada.
- `extended_description`: tiempo presente, enfoque en atributos actuales, apariencia y comportamiento. Sin narrativa de eventos.
- `scene`: tiempo presente o pasado inmediato, enfoque en acción y diálogo, un momento concreto. Longitud media.
- `chapter`: estructura narrativa completa con inicio identificable, desarrollo y cierre. Longitud larga. El modelo debe saber que se espera un texto sustancial.

**Regla 3 — Manejo de contexto insuficiente**

Cuando el contexto RAG es pobre (pocos chunks, scores bajos), el modelo no debe rechazar la generación. Debe generar con lo disponible y añadir al final una nota indicando qué información adicional mejoraría el resultado. Esto es preferible a un rechazo que frustra al usuario.

**Regla 4 — Longitud objetivo explícita**

Cada template debe comunicar al modelo una longitud aproximada esperada:

- `backstory`: 2-3 párrafos
- `extended_description`: 2-3 párrafos
- `scene`: 3-5 párrafos
- `chapter`: 6-10 párrafos con estructura clara

Esto no es un límite duro sino una señal para el modelo. El parámetro `max_tokens` del servidor sigue siendo el límite real.

**Regla 5 — Consistencia de idioma**

Todos los prompts deben estar en español cuando el output esperado es en español. Los prompts de extracción de imagen pueden permanecer en inglés ya que el output es un prompt visual en inglés, pero deben ser completamente en inglés sin mezcla.

**Regla 6 — Prompts de imagen: brevedad**

Los prompts de extracción visual para `image_prompt_builder` deben reducirse a las instrucciones esenciales. La regla es: si el modelo puede seguir el prompt sin una instrucción específica, eliminarla. Priorizar las primeras 100 palabras ya que los modelos pequeños cuantizados las ponderan más.

---

### 1.3 Entregables de Fase 1

- `llm.py` refactorizado con separadores estructurales claros y sin duplicación de seguridad
- `prompt_templates.py` refactorizado con diferenciación clara por categoría, longitud objetivo y manejo de contexto insuficiente
- `image_prompt_rules.py` con prompts reducidos y en idioma consistente
- Documento de cambios con el antes/después de cada template y la justificación del cambio

---

## Fase 2: Harness de evaluación

### 2.1 Arquitectura del harness

El harness es un sistema de evaluación offline que corre fuera de la aplicación principal. No modifica el código de producción. Usa directamente los servicios del pipeline (Ollama, los prompt templates) pero con contexto RAG simulado en lugar de Qdrant real.

**Por qué contexto simulado y no Qdrant real**

Qdrant puede devolver chunks distintos en distintas corridas dependiendo de pequeñas variaciones en los embeddings. Para comparar modelos y versiones de prompts de forma justa, el contexto debe ser idéntico en cada corrida. El contexto simulado garantiza eso.

**Estructura de directorios del harness**

```
harness/
├── test_cases/          # Definición de casos de prueba en YAML o JSON
├── results/             # Resultados de cada corrida, organizados por fecha
├── runner/              # Lógica de ejecución contra cada modelo
├── evaluator/           # Lógica de evaluación (manual + LLM-as-judge)
└── reports/             # Comparativas entre corridas
```

---

### 2.2 Estructura de un test case

Cada caso de prueba es un archivo que define:

**Campos obligatorios:**

| Campo | Descripción |
|-------|-------------|
| `id` | Identificador único del caso |
| `name` | Nombre descriptivo |
| `category` | Categoría objetivo: `backstory`, `extended_description`, `scene`, `chapter` |
| `entity_type` | Tipo de entidad: `character`, `creature`, `location`, `faction`, `item` |
| `entity_name` | Nombre de la entidad ficticia |
| `entity_description` | Descripción base de la entidad |
| `simulated_context` | Lista de 2-4 fragmentos de texto que simulan lo que Qdrant devolvería |
| `query` | La pregunta o instrucción del usuario |
| `context_quality` | Indicador de calidad del contexto: `rich`, `sparse`, `irrelevant` |

**Campos opcionales:**

| Campo | Descripción |
|-------|-------------|
| `notes` | Observaciones sobre qué aspecto específico se está probando |
| `expected_failure_mode` | Qué tipo de fallo se anticipa con modelos pequeños |

---

### 2.3 Conjunto inicial de test cases — 10 casos

Los casos deben cubrir estas situaciones problemáticas identificadas en el feedback:

**Casos de contexto rico (3 casos)**

- **TC-01:** Personaje con mucha información en el contexto, categoría `backstory`. Verifica si el modelo usa la información disponible o inventa.
- **TC-02:** Lugar con descripción detallada, categoría `extended_description`. Verifica diferenciación con backstory.
- **TC-03:** Facción con historia compleja, categoría `chapter`. Verifica si el modelo produce estructura narrativa completa.

**Casos de contexto pobre (2 casos)**

- **TC-04:** Criatura con solo 1 fragmento de contexto relevante, categoría `scene`. Verifica el comportamiento con información insuficiente: ¿rechaza o genera?
- **TC-05:** Objeto con contexto de baja similitud (fragmentos sobre otro tema), categoría `backstory`. Verifica el peor caso de recuperación RAG.

**Casos de query compleja (2 casos)**

- **TC-06:** Query que requiere cruzar información de múltiples fragmentos del contexto. Verifica capacidad de síntesis.
- **TC-07:** Query sobre un crossover o relación entre dos entidades. Directamente relacionado con el feedback del usuario. Verifica si el modelo puede manejar consultas relacionales.

**Casos de categoría exigente (2 casos)**

- **TC-08:** Personaje, categoría `chapter`. El caso más exigente en longitud y estructura. Con llama3.2 es donde más probable es que el output sea corto o incompleto.
- **TC-09:** Criatura, categoría `extended_description`. Verifica si la descripción es específica o genérica.

**Caso de instrucción edge case (1 caso)**

- **TC-10:** Query que contiene elementos que podrían activar la instrucción de seguridad en un contexto narrativo legítimo (por ejemplo, una batalla o un veneno ficticio). Verifica si el modelo rechaza incorrectamente contenido narrativo válido.

---

### 2.4 Dimensiones de evaluación

Cada respuesta se evalúa en 4 dimensiones con escala 1-3:

**D1 — Adherencia al contexto**

| Score | Criterio |
|-------|----------|
| 1 | Ignora el contexto provisto, genera libremente sin referenciarlo |
| 2 | Usa parte del contexto pero mezcla con información inventada sin señalarlo |
| 3 | Usa el contexto de forma clara y coherente; lo que inventa es consistente con él |

**D2 — Especificidad narrativa**

| Score | Criterio |
|-------|----------|
| 1 | Output genérico que podría aplicar a cualquier entidad de ese tipo |
| 2 | Tiene algunos detalles específicos pero predomina lo genérico |
| 3 | Output rico en detalles específicos del mundo y la entidad |

**D3 — Cumplimiento de categoría**

| Score | Criterio |
|-------|----------|
| 1 | El output no corresponde a la categoría pedida (un backstory que suena a escena) |
| 2 | Corresponde parcialmente a la categoría pero le falta estructura característica |
| 3 | El output es reconociblemente de la categoría correcta con la estructura esperada |

**D4 — Completitud**

| Score | Criterio |
|-------|----------|
| 1 | Output cortado, incompleto o demasiado corto para la categoría |
| 2 | Completo pero con longitud insuficiente para lo que se pedía |
| 3 | Completo y con la extensión apropiada para la categoría |

> **Métrica agregada:** promedio simple de las 4 dimensiones. No ponderar porque en esta fase se quiere visibilidad por dimensión, no un número único.

---

### 2.5 Flujo de una corrida de evaluación

**Paso 1 — Preparación**

Seleccionar la configuración a evaluar: modelo (llama3.2 o qwen3), versión de prompt (actual o refactorizado) y temperatura. Registrar en el header del resultado.

**Paso 2 — Ejecución por test case**

Para cada test case:
- Construir el prompt final usando el template de la categoría correspondiente con el contexto simulado inyectado directamente
- Enviar a Ollama con la configuración seleccionada
- Registrar: texto del output, tiempo de respuesta en segundos, si el modelo rechazó generar

**Paso 3 — Evaluación manual (primera ronda)**

Revisar cada output contra las 4 dimensiones. Anotar justificación breve para cada score. Esto es crítico para calibrar el criterio antes de automatizar.

**Paso 4 — Evaluación LLM-as-judge (rondas posteriores)**

Una vez calibrado el criterio manual, construir un prompt de evaluación que presente al juez:
- El contexto simulado
- La query original
- La categoría esperada
- Las definiciones de las 4 dimensiones
- El output a evaluar
- Instrucción de devolver scores y justificación en formato estructurado

> **Importante:** el juez debe evaluar un output a la vez, no comparar dos outputs simultáneamente. La comparación se hace después agregando los resultados. Esto evita el sesgo de posición del LLM-as-judge.

**Paso 5 — Registro de resultados**

Cada corrida genera un archivo de resultados con:
- Metadata: fecha, modelo, versión de prompt, temperatura
- Por cada test case: output completo, tiempo, scores por dimensión, justificaciones
- Resumen: scores promedio por dimensión, por categoría y global

---

### 2.6 Comparativas entre configuraciones

**Comparativa de modelos** (mismo prompt, distinto modelo)

1. Correr todos los test cases con llama3.2 en configuración actual
2. Correr todos los test cases con qwen3 Q4_K_M en configuración actual
3. Comparar scores por dimensión y por categoría
4. Identificar en qué categorías cada modelo es superior

**Comparativa de prompts** (mismo modelo, distinto prompt)

1. Correr todos los test cases con prompts actuales en el modelo que resultó mejor
2. Correr todos los test cases con prompts refactorizados en el mismo modelo
3. Comparar para medir el impacto real del refactor de prompts

**Comparativa de temperatura**

Probar temperatura `0.7` (actual) vs `0.5` vs `0.9` en los test cases de categoría `chapter` y `scene`, que son los más sensibles a creatividad vs coherencia.

---

### 2.7 Criterios de decisión post-evaluación

**Selección de modelo por categoría**

Si un modelo supera al otro por 0.5 puntos o más en el promedio de una categoría específica, usar ese modelo para esa categoría. Esto implica hacer `OLLAMA_MODEL` configurable por categoría en lugar de global, lo cual es un cambio menor en `Settings` y en `generation_service`.

**Validación del refactor de prompts**

El refactor se considera exitoso si:
- D3 (cumplimiento de categoría) mejora en promedio 0.3 puntos o más
- D1 (adherencia al contexto) no empeora
- TC-04 y TC-05 (contexto pobre) ya no producen rechazos innecesarios

**Umbral para LLM-as-judge**

El juez automático se considera confiable cuando sus scores difieren de la evaluación manual en no más de 0.5 puntos en promedio sobre los primeros 10 casos evaluados manualmente. Si la diferencia es mayor, revisar el prompt del juez antes de usarlo para más evaluaciones.

---

## Dependencias entre fases

```
Fase 1 (auditoría prompts)
    └─→ Informar diseño de TC-10 (edge case seguridad)
    └─→ Informar qué dimensiones priorizar en evaluación

Fase 2 (harness)
    ├─→ Primera corrida con prompts actuales (baseline)
    └─→ Segunda corrida con prompts refactorizados (validación)
         └─→ Decisión: modelo por categoría o modelo único
```

> La Fase 1 debe completarse antes de la segunda corrida del harness, pero la construcción de los test cases y la primera corrida baseline pueden hacerse en paralelo con la auditoría de prompts.

---

## Orden de trabajo sugerido

| Día | Actividad |
|-----|-----------|
| 1 | Inspección de `llm.py` y `prompt_templates.py`. Documentar problemas concretos y proponer versiones alternativas. |
| 2 | Inspección de `image_prompt_rules.py`. Construir los 10 test cases con contexto simulado. |
| 3 | Primera corrida baseline con prompts actuales contra ambos modelos. Evaluación manual de resultados. |
| 4 | Aplicar refactor de prompts. Segunda corrida. Comparativa baseline vs refactorizado. Decisión sobre modelo por categoría. |

---

## Lo que este plan NO incluye

- **Integración del harness en CI/CD:** no es necesario en esta etapa
- **Base de datos de resultados:** archivos planos son suficientes por ahora
- **UI para el harness:** la revisión es manual o por script simple
- **Evaluación de embeddings o del pipeline Qdrant:** es una fase separada si los resultados del harness sugieren que el problema está en la recuperación y no en la generación
- **Generación en batch por entidad:** cambio gradual a futuro, no parte de esta iteración
