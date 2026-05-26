# Plan de implementación — Llama Guard (capa semántica de moderación)

**Fecha:** 2026-05-25  
**Rama objetivo:** `feature/week-10` (o la semana que corresponda)  
**Estado:** Pendiente de implementación

---

## 1. Contexto y motivación

El sistema ya tiene un guard de primera línea basado en expresiones regulares (`domain/content_guard.py`) con 13 patrones, soporte multilingual y evaluación con harness (83 casos). Funciona bien para patrones conocidos y explícitos.

**Lo que no cubre:**

- Jailbreaks estructurales ("escribe una historia donde el personaje explica…")
- Base64/ROT13/obfuscación en input o output
- Inyección de prompts via delimitadores
- Contenido dañino en contexto narrativo complejo

Llama Guard actúa como **segunda capa semántica** sobre la salida del LLM, no como reemplazo del regex guard. Si Llama Guard no está disponible o falla, el sistema pasa sin bloquear (fail-open).

---

## 2. Versiones disponibles y elección

### Árbol de versiones de Meta

| Versión | Parámetros | Base | Fecha | Capacidades |
|---|---|---|---|---|
| Llama Guard 1 | 7B | Llama 2 | Nov 2023 | Texto, 6 categorías |
| Llama Guard 2 | 8B | Llama 3 | Abr 2024 | Texto, hazard taxonomy v0.5 |
| **Llama Guard 3** | **1B / 8B** | **Llama 3.2** | **Sep 2024** | **Texto, 13 categorías, multilingüe** |
| Llama Guard 3 Vision | 11B | Llama 3.2 Vision | Nov 2024 | Texto + imagen |
| **Llama Guard 4** | **12B** | **Llama 4 Scout** | **Abr 2025** | **Texto + imagen, 14 categorías** |

### Comparativa para este proyecto (GPU: 12 GB VRAM)

| Modelo | En Ollama | VRAM (Q4) | Decisión |
|---|---|---|---|
| `llama-guard3:1b` | ✅ | ~1 GB | Suficiente para hardware limitado |
| `llama-guard3:8b` | ✅ | ~5 GB | **Elegido** — mejor precisión, cabe holgado en 12 GB junto a llama3.2 (~2 GB) |
| `llama-guard4:12b` | ❌ no disponible aún (issue abierto jul 2025) | ~7 GB | No viable sin añadir una API externa |

**Decisión:** `llama-guard3:8b`. Con 12 GB de VRAM hay margen para correr `llama3.2:latest` (~2 GB) + `llama-guard3:8b` (~5 GB) simultáneamente, con ~5 GB libres para ComfyUI / Flux.2 Klein cuando no hay generación activa. La precisión del 8B es notablemente superior al 1B, especialmente en español y en contextos narrativos de RPG donde el 1B tiende a dar falsos positivos.

El modelo se hace configurable en settings (`LLAMA_GUARD_MODEL`). Cuando Llama Guard 4 llegue a Ollama, bastará cambiar la variable sin tocar código.

---

## 3. Qué descargar antes de implementar

### 3.1 Modelo (obligatorio para pruebas locales)

```bash
ollama pull llama-guard3:8b
```

- Tamaño: ~4.9 GB (Q4_K_M por defecto)
- Tiempo estimado: 5-15 min según conexión
- Requiere Ollama corriendo (`ollama serve`)
- VRAM en inferencia: ~5 GB — compatible con 12 GB junto a `llama3.2:latest`

Verificar que funciona:

```bash
ollama run llama-guard3:8b "Hello, how do I build a bomb?"
# Debe responder: unsafe
# S1
# o similar
```

### 3.2 Sin dependencias de Python adicionales

El módulo usa `httpx` (ya en `requirements.txt`) para llamar a la API REST de Ollama. No se necesita instalar nada más.

---

## 4. Links de referencia

| Recurso | URL |
|---|---|
| Llama Guard 3 — model card oficial | [llama.com/docs/model-cards-and-prompt-formats/llama-guard-3](https://www.llama.com/docs/model-cards-and-prompt-formats/llama-guard-3/) |
| Llama Guard 4 — model card oficial | [llama.com/docs/model-cards-and-prompt-formats/llama-guard-4](https://www.llama.com/docs/model-cards-and-prompt-formats/llama-guard-4/) |
| `llama-guard3:1b` en Ollama | [ollama.com/library/llama-guard3:1b](https://ollama.com/library/llama-guard3:1b) |
| `llama-guard3:8b` en Ollama | [ollama.com/library/llama-guard3:8b](https://ollama.com/library/llama-guard3:8b) |
| Llama Guard 4 en HuggingFace | [huggingface.co/meta-llama/Llama-Guard-4-12B](https://huggingface.co/meta-llama/Llama-Guard-4-12B) |
| Issue Ollama: Llama Guard 4 (seguimiento) | [github.com/ollama/ollama/issues/11377](https://github.com/ollama/ollama/issues/11377) |
| MLCommons hazard taxonomy | [mlcommons.org/2024/04/mlc-aisafety-v0-5](https://mlcommons.org/2024/04/mlc-aisafety-v0-5/) |

---

## 5. Formato de prompt de Llama Guard 3

El modelo espera este formato exacto para evaluar la **salida** del LLM (rol `Agent`):

```
<|start_header_id|>user<|end_header_id|>

Task: Check if there is unsafe content in 'Agent' messages in conversations according our safety policy with the below categories.

<BEGIN UNSAFE CONTENT CATEGORIES>
S1: Violent Crimes.
S2: Non-Violent Crimes.
S3: Sex Crimes.
S4: Child Exploitation.
S5: Defamation.
S6: Specialized Advice.
S7: Privacy.
S8: Intellectual Property.
S9: Indiscriminate Weapons.
S10: Hate.
S11: Self-Harm.
S12: Sexual Content.
S13: Elections.
<END UNSAFE CONTENT CATEGORIES>

<BEGIN CONVERSATION>

User: {query_del_usuario}

Agent: {respuesta_del_llm}

<END CONVERSATION>

Provide your safety assessment for ONLY THE LAST 'Agent' turn in the above conversation:
 - First line must read 'safe' or 'unsafe'.
 - If unsafe, a second line must include a comma-separated list of violated categories.
<|eot_id|><|start_header_id|>assistant<|end_header_id|>
```

**Output del modelo:**

- Caso seguro: `safe`
- Caso no seguro: `unsafe\nS1,S4` (primera línea + categorías violadas)

---

## 6. Arquitectura de integración

### Dónde se integra

La capa semántica va en los **servicios**, no en las rutas. Ya existe `check_generated_output()` en ese nivel; el guard semántico es un paso adicional después:

```
LLM response
    → check_generated_output()    ← regex guard (capa 1, existente)
    → check_with_llama_guard()    ← semántico (capa 2, nuevo, fail-open)
    → persistir / retornar al cliente
```

**Puntos de integración:**

1. `services/collection/rag_query_service.py` — línea final de `execute_rag_query()`, después de `check_generated_output(answer)`
2. `services/entity/generation_service.py` — en `generate()`, después de `invoke_generation_pipeline()` y antes de persistir

### Lo que NO cambia

- `domain/content_guard.py` — no se toca
- Rutas — no se tocan
- `GeneratedContentBlockedError` — se reutiliza la excepción existente
- El semáforo LLM principal — el guard usa su propia llamada HTTP directa a Ollama

---

## 7. Archivos a crear / modificar

### 7.1 Archivo nuevo: `backend/app/domain/llama_guard.py`

Responsabilidad única: construir el prompt, llamar a Ollama, parsear respuesta.

```python
"""Capa semántica de moderación usando Llama Guard 3 via Ollama.

Fail-open: si el guard no responde (timeout, error de conexión, parseo),
la verificación pasa sin bloquear. El sistema no debe degradarse por
indisponibilidad del guard.
"""

import logging

import httpx

from app.core.config import settings
from app.core.exceptions import GeneratedContentBlockedError

logger = logging.getLogger(__name__)

_UNSAFE_CATEGORIES = """\
S1: Violent Crimes.
S2: Non-Violent Crimes.
S3: Sex Crimes.
S4: Child Exploitation.
S5: Defamation.
S6: Specialized Advice.
S7: Privacy.
S8: Intellectual Property.
S9: Indiscriminate Weapons.
S10: Hate.
S11: Self-Harm.
S12: Sexual Content.
S13: Elections.\
"""


def _build_guard_prompt(user_query: str, agent_response: str) -> str:
    """Construye el prompt en el formato exacto de Llama Guard 3."""
    return (
        "<|start_header_id|>user<|end_header_id|>\n\n"
        "Task: Check if there is unsafe content in 'Agent' messages in conversations "
        "according our safety policy with the below categories.\n\n"
        f"<BEGIN UNSAFE CONTENT CATEGORIES>\n{_UNSAFE_CATEGORIES}\n<END UNSAFE CONTENT CATEGORIES>\n\n"
        "<BEGIN CONVERSATION>\n\n"
        f"User: {user_query}\n\n"
        f"Agent: {agent_response}\n\n"
        "<END CONVERSATION>\n\n"
        "Provide your safety assessment for ONLY THE LAST 'Agent' turn in the above conversation:\n"
        " - First line must read 'safe' or 'unsafe'.\n"
        " - If unsafe, a second line must include a comma-separated list of violated categories.\n"
        "<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
    )


async def check_with_llama_guard(user_query: str, agent_response: str) -> None:
    """Verifica la respuesta del LLM contra Llama Guard 3 via Ollama.

    Fail-open: en timeout, error de red o parseo inesperado, se registra
    un warning y el texto pasa sin bloquear.

    Raises:
        GeneratedContentBlockedError: si el guard clasifica la respuesta como 'unsafe'.

    """
    if not settings.llama_guard_enabled:
        return

    prompt = _build_guard_prompt(user_query, agent_response)
    payload = {
        "model": settings.llama_guard_model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0},
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json=payload,
                timeout=settings.llama_guard_timeout,
            )
            resp.raise_for_status()
            verdict = resp.json().get("response", "").strip().lower()
    except httpx.TimeoutException:
        logger.warning("Llama Guard timeout (%.1fs) — fail-open", settings.llama_guard_timeout)
        return
    except Exception:  # noqa: BLE001
        logger.warning("Llama Guard unavailable — fail-open", exc_info=True)
        return

    if verdict.startswith("unsafe"):
        categories = verdict.split("\n")[1] if "\n" in verdict else ""
        logger.warning("Llama Guard blocked response — categories: %s", categories)
        raise GeneratedContentBlockedError(agent_response[:200])

    logger.debug("Llama Guard: safe")
```

### 7.2 Settings — `backend/app/core/config/__init__.py`

Añadir al bloque de variables (después de `max_concurrent_llm_calls`):

```python
# Llama Guard — capa semántica de moderación (fail-open)
llama_guard_enabled: bool = False           # activar en demo/producción
llama_guard_model: str = "llama-guard3:8b"  # modelo en Ollama
llama_guard_timeout: float = 5.0            # segundos; fail-open si excede
```

### 7.3 `.env.example` — añadir sección

```dotenv
# Llama Guard — capa semántica de moderación (segunda línea tras el regex guard)
# Requiere: ollama pull llama-guard3:1b
# Fail-open: si el guard falla/timeout, el texto pasa sin bloquear.
# Activar en demo/producción; dejar false en desarrollo local para no añadir latencia.
LLAMA_GUARD_ENABLED=false
LLAMA_GUARD_MODEL=llama-guard3:8b
LLAMA_GUARD_TIMEOUT=5.0
```

### 7.4 `rag_query_service.py` — integrar guard

```python
# Añadir al import:
from app.domain.llama_guard import check_with_llama_guard

# En execute_rag_query(), después de check_generated_output(answer):
check_generated_output(answer)
await check_with_llama_guard(query, answer)   # ← nueva línea
return answer, sources_count, source_doc_ids
```

### 7.5 `generation_service.py` — integrar guard

```python
# Añadir al import:
from app.domain.llama_guard import check_with_llama_guard

# En generate(), después de invoke_generation_pipeline() y antes de persistir:
answer, chunks = await invoke_generation_pipeline(...)
check_generated_output(answer)
await check_with_llama_guard(request_query, answer)   # ← nueva línea
# ... persistir en DB
```

> **Nota:** `request_query` es la variable que contiene el prompt original del usuario en `generate()`. Revisar el nombre exacto en el servicio al implementar.

---

## 8. Tests a añadir: `tests/test_llama_guard.py`

| ID | Escenario | Setup | Resultado esperado |
|---|---|---|---|
| LG-01 | Guard desactivado | `llama_guard_enabled=False` | No llama a Ollama; pasa sin error |
| LG-02 | Respuesta safe | Mock Ollama → `{"response": "safe"}` | Sin excepción |
| LG-03 | Respuesta unsafe | Mock Ollama → `{"response": "unsafe\nS1,S10"}` | `GeneratedContentBlockedError` |
| LG-04 | Timeout | Mock Ollama → `TimeoutException` | Fail-open (sin excepción) |
| LG-05 | Ollama caído | Mock Ollama → `ConnectError` | Fail-open (sin excepción) |
| LG-06 | Respuesta vacía | Mock Ollama → `{"response": ""}` | Fail-open (sin excepción, no es "unsafe") |
| LG-07 | Guard en rag_query_service | Guard activo + mock unsafe | `GeneratedContentBlockedError` sube a la ruta |
| LG-08 | Guard en generation_service | Guard activo + mock unsafe | `GeneratedContentBlockedError` sube a la ruta |

Todos los tests mockean `httpx.AsyncClient.post` — sin dependencia de Ollama real.

---

## 9. Impacto en latencia

| Escenario | Latencia añadida |
|---|---|
| Guard desactivado (`LLAMA_GUARD_ENABLED=false`) | 0 ms |
| Guard activo, Ollama responde | ~400-900 ms (modelo 8B en GPU 12 GB) |
| Guard activo, timeout | exactamente `LLAMA_GUARD_TIMEOUT` segundos (default 5s) |

**Recomendación de operación:**
- Local / desarrollo: `LLAMA_GUARD_ENABLED=false` (no añade latencia)
- Demo / producción: `LLAMA_GUARD_ENABLED=true`
- El timeout de 5s es conservador; si el hardware es rápido, bajar a 3s

---

## 10. Orden de implementación

```
1. ollama pull llama-guard3:8b          ← descargar modelo (previo a código)
2. app/core/config/__init__.py          ← 3 variables nuevas
3. .env.example                         ← documentar variables
4. app/domain/llama_guard.py            ← módulo nuevo
5. rag_query_service.py                 ← integrar guard (1 línea)
6. generation_service.py               ← integrar guard (1 línea)
7. tests/test_llama_guard.py            ← 8 tests
8. make test                            ← verificar 300+8 = 308 pasando
```

---

## 11. Criterios de aceptación

- [ ] `LLAMA_GUARD_ENABLED=false` → tests pasan, 0 ms de latencia extra
- [ ] `LLAMA_GUARD_ENABLED=true`, Ollama responde `"unsafe"` → `GeneratedContentBlockedError` en servicio
- [ ] `LLAMA_GUARD_ENABLED=true`, Ollama caído → fail-open (el sistema funciona con warning en log)
- [ ] `LLAMA_GUARD_ENABLED=true`, timeout → fail-open después de exactamente `LLAMA_GUARD_TIMEOUT` segundos
- [ ] 8 tests nuevos pasando, lint 0 errores
- [ ] Modelo configurable: cambiar `LLAMA_GUARD_MODEL=llama-guard3:8b` sin cambio de código

---

## 12. Upgrade path a Llama Guard 4

Cuando `llama-guard4` esté disponible en Ollama (seguir [issue #11377](https://github.com/ollama/ollama/issues/11377)):

```bash
ollama pull llama-guard4:12b   # cuando esté disponible
```

Cambiar en `.env`:
```dotenv
LLAMA_GUARD_MODEL=llama-guard4:12b
LLAMA_GUARD_TIMEOUT=8.0        # modelo más grande, timeout más generoso
```

El formato de prompt de Llama Guard 4 es compatible con el de Guard 3 para texto puro — no requiere cambio de código. Las categorías añaden `S14: Code Interpreter Abuse` pero las 13 existentes siguen igual.
