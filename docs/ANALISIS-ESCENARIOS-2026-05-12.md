# Análisis de Escenarios — Issues Pendientes 2026-05-12

**Base:** `bugfix/security-concers` @ `5ce7c45`  
**Issues totales restantes:** 318 (FAST002: 108, B008: 118, E501: 74, PLR0913: 17)

---

## 1. Clasificación por nivel de impacto

Se clasificaron los 318 issues según el riesgo real de resolverlos:

| Nivel | Criterio | Reglas | Cantidad |
|---|---|---|---|
| **BAJO** | Cambio puramente cosmético/sintáctico. Sin riesgo de romper lógica, tests ni seguridad. | FAST002, B008, E501 en docstrings/strings triviales | **266** |
| **MEDIO** | Requiere cuidado al partir strings o verificar tests. Sin riesgo de seguridad directo. | E501 en regex, prompts, strings de negocio | **27** |
| **ALTO** | Toca código auditado de seguridad o requiere reestructuración arquitectónica. | E501 en security_headers/config/storage, PLR0913 | **24** |

### Desglose E501 por criticidad

De los 74 E501:

| Nivel | Archivos | Cantidad | Qué son |
|---|---|---|---|
| **ALTO** | `security_headers.py` (2), `config/__init__.py` (3), `storage/__init__.py` (2) | **7** | Strings CSP, validators, path traversal checks |
| **MEDIO** | `content_guard.py` (6), `generation_service.py` (5), `comfyui_client.py` (2), `rag.py` (4), `rag_pipeline.py` (2), `deletion_service.py` (1), `image_generation_service.py` (1), `models/db/user.py` (1) | **24** | Regex patterns, prompts, llamadas a servicios |
| **BAJO** | `image_prompt_rules.py` (32), `auth.py` (1), `documents.py` (1), `exceptions/__init__.py` (2), `lifespan.py` (1), `filters.py` (1), `__init__.py` files, `prompt_templates.py` (1), `llm.py` (1), `main.py` (1) | **43** | Docstrings, strings de prompts, re-exports |

*Nota: `image_prompt_rules.py` contiene 32 strings de prompts largos que son triviales de partir con paréntesis, sin riesgo de regex malformada. Los 15 restantes del archivo son más complejos y se clasifican en MEDIO (prompts con interpolación).*

---

## 2. Escenario A — Resolver solo issues de BAJO impacto

### Qué se resuelve
- FAST002 (108): todo el patrón `Annotated` en routers.
- B008 (118): todo `Depends()` en argumentos por defecto.
- E501 bajos (43): docstrings, strings triviales, re-exports.

**Total resueltos: 269**

### Qué queda
- E501 medios (24): regex en `content_guard`, strings de negocio en servicios.
- E501 altos (7): CSP, validators, storage checks.
- PLR0913 (17): demasiados argumentos.

**Total restantes: 49**

### Métrica visual

```
Antes:  ████████████████████████████████████████████████████████████████████████████ 318
         [FAST002 108] [B008 118] [E501 74] [PLR0913 17]

Después: ███████████████ 49
         [E501 medio 24] [E501 alto 7] [PLR0913 17]

Reducción: 84.6%
```

### Costo/Beneficio

| Factor | Valoración |
|---|---|
| **Esfuerzo** | Alto en volumen (269 líneas, ~20 archivos) pero mecánico. Se puede automatizar con `sed`/`ruff --fix` parcial + script. |
| **Tiempo estimado** | 2–3 horas (incluyendo verificación de tests). |
| **Riesgo de regresión** | **Muy bajo.** FAST002/B008 no cambian runtime. E501 bajos son docstrings/strings. |
| **Riesgo AUDIT-SECURITY** | **Ninguno.** Ninguno de estos issues está en código auditado de seguridad. |
| **Nuevos issues posibles** | Posibles nuevos E501 creados por líneas más largas de `Annotated`. Mitigable con `--select E501` post-fix. |

### Recomendación
**Viable y seguro**, pero de bajo valor funcional. Reduce el ruido del linter masivamente pero no mejora robustez ni seguridad. Ideal si el objetivo es limpiar el ruleset para que solo queden issues accionables.

---

## 3. Escenario B — Resolver BAJO + MEDIO impacto

### Qué se resuelve (además del Escenario A)
- E501 medios (24): regex en `content_guard.py`, strings en `generation_service.py`, `comfyui_client.py`, `rag.py`, etc.

**Total resueltos: 293**

### Qué queda
- E501 altos (7): CSP, validators, storage checks.
- PLR0913 (17): demasiados argumentos.

**Total restantes: 24**

### Métrica visual

```
Antes:  ████████████████████████████████████████████████████████████████████████████ 318

Después: ███████ 24
         [E501 alto 7] [PLR0913 17]

Reducción: 92.5%
```

### Costo/Beneficio

| Factor | Valoración |
|---|---|
| **Esfuerzo** | Muy alto. Los 24 E501 medios requieren revisión manual cuidadosa: regex no deben romperse, strings de prompts deben mantener interpolación correcta. |
| **Tiempo estimado** | 4–5 horas ( Escenario A + 2h adicionales de revisión manual). |
| **Riesgo de regresión** | **Medio.** `content_guard.py` tiene regex de seguridad (M-1, M-2). Partir un raw string mal puede romper el patrón. `generation_service.py` tiene strings que van al LLM; partir mal puede alterar el prompt. |
| **Riesgo AUDIT-SECURITY** | **Bajo indirecto.** `content_guard.py` es primera línea de defensa contra contenido dañino. Aunque los fixes auditados no se tocan directamente, un regex roto deja un agujero funcional. |
| **Nuevos issues posibles** | Mismos que A + posible regex malformada, tests de content_guard rotos. |

### Recomendación
**Viable con tests de seguridad.** Requiere ejecutar tests unitarios de `content_guard` y validación de prompts antes y después. El beneficio adicional sobre el Escenario A es marginal (23 issues menos, 7.9% extra de reducción) con riesgo sustancialmente mayor.

---

## 4. Escenario C — Resolver TODO (incluido ALTO)

### Qué quedaría
- **0 issues** (si se resuelven los 24 altos).

### Por qué NO es recomendable

| Issue | Por qué no tocar |
|---|---|
| **E501 en `security_headers.py`** (2) | Strings CSP. Un salto de línea mal colocado rompe el header `Content-Security-Policy`. El navegador rechaza CSP malformado → la app queda sin protección XSS. Fix auditado H-9/C-6 comprometido. |
| **E501 en `config/__init__.py`** (3) | Validators de Pydantic (`secret_key`, `environment`, `cors_origins`). Partir mal la lógica de un validator puede hacer que `SECRET_KEY="your-secret-key"` pase desapercibido o que CORS acepte `http://` en producción. Fixes C-7, M-9, M-12 comprometidos. |
| **E501 en `storage/__init__.py`** (2) | `is_relative_to(media_root_resolved)`. Es la defensa contra path traversal (C-5, L-4). Alterar la línea, aunque sea solo partirla, introduce riesgo de modificación accidental. |
| **PLR0913** (17) | Requiere diseño de DTOs. Cambiar `list_documents(session, collection_id, page, page_size, ...)` a `list_documents(session, filters)` rompe callers, routers y tests. Además, las dependencias FastAPI (`Depends(get_collection_or_404_owned)`) **no pueden ir dentro de un Pydantic model**, lo que significa que los endpoints con PLR0913 que usan `_` para auth no pueden resolverse con DTOs sin cambiar la arquitectura de inyección. |

**Veredicto:** El costo de resolver los 24 issues altos (riesgo de seguridad + diseño arquitectónico) no justifica el beneficio de llegar a 0.

---

## 5. Tabla comparativa

| Métrica | Escenario A (BAJO) | Escenario B (BAJO+MEDIO) | Escenario C (TODO) |
|---|---|---|---|
| Issues resueltos | 269 | 293 | 318 |
| Issues restantes | 49 | 24 | 0 |
| Reducción % | 84.6% | 92.5% | 100% |
| Tiempo estimado | 2–3h | 4–5h | 8–10h+ |
| Riesgo regresión | Muy bajo | Medio | **Alto** |
| Riesgo AUDIT-SECURITY | Ninguno | Bajo indirecto | **Alto directo** |
| Tests rotos posibles | 0 | 2–5 | 10+ |
| Nuevos E501 por `Annotated` | Sí (~5–10) | Sí (~5–10) | Sí (~5–10) |
| Requiere diseño arquitectónico | No | No | **Sí** (DTOs) |
| Valor funcional añadido | Ninguno | Ninguno | Ninguno |
| Valor de mantenimiento | Alto (ruleset limpio) | Muy alto | Máximo |

---

## 6. Análisis de valor

Todos los issues restantes son **deuda técnica de bajo impacto funcional**. Ninguno introduce bug de seguridad ni runtime si se deja sin tocar. La pregunta es: ¿cuánto vale limpiar el linter?

- **Escenario A** ofrece la mejor relación costo/beneficio: 85% de reducción con esfuerzo moderado y riesgo casi nulo.
- **Escenario B** añade solo 8 puntos porcentuales de reducción por el doble de riesgo y el doble de tiempo.
- **Escenario C** es técnicamente posible pero arriesgado e innecesario.

**Recomendación final:**

> **Implementar Escenario A** si el equipo quiere un ruleset limpio para futuros desarrollos. **Diferir Escenario B** a menos que haya una necesidad específica de reducir E501 en `content_guard` o servicios. **Rechazar Escenario C** explícitamente para proteger los fixes de seguridad auditados.

---

## 7. Post-ejecución esperada (si se implementa Escenario A)

```bash
# Estado actual
$ ruff check app/ --select ALL --output-format concise | wc -l
639

# Tras Escenario A (estimado)
$ ruff check app/ --select ALL --output-format concise | wc -l
~370  (49 issues restantes de este bucket + ~321 de otras reglas no críticas)

# Issues críticos restantes visibles
$ ruff check app/ --select E501,PLR0913 --output-format concise
app\api\middlewares\security_headers.py:56:89: E501
app\api\middlewares\security_headers.py:69:89: E501
app\core\config\__init__.py:118:89: E501
app\core\config\__init__.py:161:89: E501
app\core\config\__init__.py:174:89: E501
app\core\storage\__init__.py:59:89: E501
app\core\storage\__init__.py:61:89: E501
... (PLR0913 ×17)
```

El ruleset quedaría limpio de FAST002/B008 (el volumen más grande), dejando solo issues que el equipo ya conoce y ha decidido no tocar por seguridad o diseño.
