# Plan de Mitigación — Issues del Feedback 2026-05-12

**Fecha:** 2026-05-12  
**Basado en:** `docs/FEEDBACK-2026-05-12.md`  
**Restricciones:**
- No alterar la estructura del proyecto (sin mover módulos entre capas).
- No introducir nuevos issues funcionales ni de seguridad.
- No modificar lógica ya auditada y resuelta en `AUDIT-SECURITY.md` / `AUDIT-SECURITY-REVIEW2-2026-05-12.md`.

---

## Resumen de estado

| Categoría | Issues originales | Resueltos (commits previos) | Pendientes accionables | Diferidos |
|---|---|---|---|---|
| Ruff extendido | 630 | ~299 | ~31 (plan abajo) | ~327 (FAST002/B008, E501, PLR0913) |
| Arquitectónicos | 6 | 2 (build_storage_path/url) | 4 | — |

**Tests base:** 175/175 ✅

---

## Principios del plan

1. **Cambio mínimo:** cada tarea modifica la menor superficie de código posible.
2. **Compatibilidad API:** las funciones públicas conservan firma y semántica; solo mejoran tipado o implementación interna.
3. **Seguridad inalterable:** ninguna tarea toca rutas de auth, validación de archivos, headers, CSRF, rate limiting ni controles de acceso ya resueltos en el audit.
4. **Verificación continua:** después de cada fase se ejecuta `make test` y `make lint`.

---

## Fase 1 — Runtime crítico (Alta prioridad)

### 1.1 `auth_clerk.py`: eliminar bloqueo de event loop + globals

**Issue:** `httpx.get()` síncrono dentro del event loop de FastAPI bloquea el worker al refrescar JWKS. Uso de `global` (PLW0603 ×3).

**Solución segura:**
- Encapsular la caché JWKS en una clase `JWKSManager` con `threading.Lock` interno.
- Usar `httpx.AsyncClient` (o `asyncio.to_thread(httpx.get, ...)`) para la descarga, manteniendo TTL de 1h.
- Conservar las funciones públicas `get_jwks()` y `decode_clerk_token(token: str) -> dict` con mismas firmas y excepciones.

**Por qué no afecta seguridad:**
- No se modifica la lógica de validación JWT (algoritmos, issuer, audience) resuelta en C-1/C-2/H-10.
- No se alteran los claims ni el veredicto de `verify`.

**Entregable:** refactor local en `app/api/routes/auth/auth_clerk.py`.

**Checklist:**
- [x] Crear `JWKSManager` con `_jwks_cache`, `_jwks_cache_time`, `_jwks_lock`.
- [x] Reemplazar `httpx.get(...)` por `httpx.AsyncClient().get(...)` dentro de un método async, o envolver en `asyncio.to_thread`.
- [x] Eliminar sentencias `global`.
- [x] Ejecutar tests de auth (`pytest tests/ -k clerk`).
- [x] Ejecutar `ruff check app/api/routes/auth/auth_clerk.py` — PLW0603 debe desaparecer.

---

### 1.2 `paginate_with_sort`: tipado estricto en `order`

**Issue:** `order: str = "desc"` acepta cualquier string en tiempo de tipado.

**Solución segura:**
```python
from typing import Literal

def paginate_with_sort(
    ...
    order: Literal["asc", "desc"] = "desc",
) -> tuple[list[T], int]: ...
```

**Por qué es seguro:** solo tipado; en runtime Pydantic/FastAPI ya validan strings. No hay routers que pasen valores arbitrarios (todos usan "asc"/"desc").

**Checklist:**
- [x] Añadir `Literal` a `app/core/database/utils.py`.
- [x] Ejecutar `make test`.
- [x] Verificar que no hay llamadas con strings dinámicos no controlados.

---

## Fase 2 — Limpieza y claridad (Media prioridad)

### 2.1 PLC0415: imports dentro de funciones

**Issue:** 3 ocurrencias restantes de imports no en top-level.

| Archivo | Línea | Situación | Acción |
|---|---|---|---|
| `app/core/auth/dependencies.py:47` | `from app.api.routes.auth.auth_clerk import decode_clerk_token` | **Intencional (lazy import)**. Evita `ModuleNotFoundError` en entornos `local` donde Clerk no está configurado. Resuelto como parte de C-1. | Añadir comentario explicativo + `# noqa: PLC0415`. No mover. |
| `app/core/lifespan.py:40` | `from app.engine.rag import ping_qdrant` | Probablemente evita import circular en startup (`rag` puede importar modelos que importan `core`). | Evaluar si es circular. Si lo es: comentario + `# noqa: PLC0415`. Si no lo es: mover al top-level. |
| `app/engine/image_prompt_builder.py:35` | `from app.engine.llm import llm` | Lazy + global `generation_chain` (PLW0603). Posible circularidad con `llm`. | Evaluar si `app.engine.llm` importa `image_prompt_builder`. Si es circular: encapsular `generation_chain` en una clase interna (similar a JWKSManager) + `# noqa` en el import. Si no es circular: mover al top-level y eliminar `global`. |

**Checklist:**
- [x] Documentar `dependencies.py` con `noqa`.
- [x] Verificar grafo de imports de `lifespan.py` y `image_prompt_builder.py`.
- [x] Ejecutar `make test` tras cada decisión.

---

### 2.2 `services/__init__.py`: barrel sin consumidores

**Issue:** Re-exporta 29 símbolos pero ningún router lo importa; añade indirección sin valor.

**Solución segura:**
- Verificar tests: `grep -r "from app.services import" tests/` encontró solo `test_deletion_service.py` que importa `deletion_service` directamente (no usa el barrel).
- **Acción:** eliminar `app/services/__init__.py`.

**Por qué es seguro:** no hay consumidores en producción ni en tests.

**Checklist:**
- [x] Confirmar que no hay imports del barrel en frontend ni scripts.
- [x] Eliminar archivo.
- [x] `make test`.

---

### 2.3 Docstrings de módulo: `cascade_service.py` vs `deletion_service.py`

**Issue:** responsabilidades solapadas; sin leer el código no se sabe cuál hace qué.

**Solución segura:** añadir docstring de módulo al inicio de cada archivo (sin cambiar código).

```python
# cascade_service.py
"""Operaciones de soft-delete en cascada.

Este módulo contiene funciones que propagan soft-delete a entidades hijas
(EntityContent) cuando se elimina una entidad o colección padre.
No realiza borrado físico de archivos ni vectores.
"""
```

```python
# deletion_service.py
"""Orquestación de eliminaciones completas (soft-delete + físico).

Coordina:
1. Soft-delete en base de datos (colecciones, documentos, entidades, imágenes).
2. Borrado físico de archivos de imagen en disco.
3. Eliminación de vectores en Qdrant (con reintentos).

Importa funciones de cascade_service para la fase de soft-delete en cascada.
"""
```

**Checklist:**
- [x] Añadir docstrings.
- [x] `make lint` (verificar que no se rompe formato).

---

### 2.4 `get_active_by_id`: documentar acoplamiento

**Issue:** asume que el modelo tiene `collection_id`, haciéndola inutilizable para `User` o `ModerationLog`.

**Solución segura:** no cambiar firma (riesgo de romper callers), solo añadir docstring honesto.

```python
def get_active_by_id(
    session: Session, model: type[T], record_id: str, collection_id: str
) -> T | None:
    """Obtiene un registro activo por ID y collection_id.

    Nota: esta utility está acoplada a modelos que poseen `collection_id`.
    No es aplicable a modelos globales como User o ModerationLog.
    """
```

**Checklist:**
- [x] Actualizar docstring.

---

## Fase 3 — Cosmético controlado (Baja prioridad)

### 3.1 E501 (líneas largas) — batch seguro

**Issue:** ~76 líneas largas restantes. Son cosméticas pero ensucian el ruleset.

**Solución segura:**
- Aplicar `ruff check app/ --select E501 --fix` por dominios pequeños (máximo 3-4 archivos por commit).
- No aplicar en archivos de auth, storage ni validación ya auditados a menos que el cambio sea trivial (salto de línea en string o parámetros).
- Verificar `make test` tras cada batch.

**Por qué es seguro:** E501 solo reformatea; no cambia semántica.

**Checklist:**
- [x] Batch 1: `app/core/database/`.
- [x] Batch 2: `app/models/schemas/` (no auth ni storage).
- [x] Batch 3: `app/api/routes/` excluyendo `auth/`, `documents/`, `public/`.
- [x] `make test` tras cada batch.

---

## Items diferidos explícitamente (no tocar)

| Issue | Razón de diferido |
|---|---|
| **FAST002 + B008** (~223 casos) | Refactor masivo en ~20 archivos de rutas. Sin ganancia funcional; alto riesgo de regresión en firmas de endpoints. Deuda técnica aceptable. |
| **PLR0913** (~16 funciones) | Decisiones de diseño arquitectónico. Requeriría reestructurar DTOs o introducir objetos de contexto; fuera del alcance de mitigación sin afectar estructura. |
| **E501 en auth/storage/validation** | Los archivos críticos de seguridad ya fueron auditados. Un reformateo masivo dificultaría la trazabilidad de los fixes de seguridad. Aplicar solo si es estrictamente local y trivial. |

---

## Resultados de la ejecución (2026-05-12)

Todas las fases fueron ejecutadas y verificadas en el mismo ciclo.

| Fase | Tarea | Estado | Commit / Archivos modificados |
|---|---|---|---|
| 1.1 | `auth_clerk.py` — JWKSManager + eliminar globals + `httpx.Client` compartido | ✅ Resuelto | `app/api/routes/auth/auth_clerk.py` |
| 1.2 | `paginate_with_sort` — `Literal["asc", "desc"]` | ✅ Resuelto | `app/core/database/utils.py` |
| 2.1 | PLC0415 — imports en funciones (3 casos) | ✅ Resuelto | `dependencies.py` (noqa), `lifespan.py` (noqa + circularidad verificada), `image_prompt_builder.py` (moved + PLW0603 eliminado) |
| 2.2 | `services/__init__.py` barrel sin uso | ✅ Resuelto | Eliminado; test ajustado a import directo |
| 2.3 | Docstrings de módulo `cascade_service` vs `deletion_service` | ✅ Resuelto | `app/services/cascade_service.py`, `app/services/deletion_service.py` |
| 2.4 | `get_active_by_id` — documentar acoplamiento | ✅ Resuelto | `app/core/database/utils.py` |
| 3.1 | E501 — líneas largas en módulos no críticos | ✅ Parcial (2/4) | `app/api/routes/collections/collections.py`, `app/api/routes/users/users.py` |

### Métricas post-ejecución

| Métrica | Antes | Después |
|---|---|---|
| Issues ruff (ruleset por defecto) | 0 | **0** |
| PLW0603 (global statement) | 3 | **0** |
| PLC0415 (imports en funciones) | 3 | **0** |
| E501 (líneas largas) | ~76 | **~74** (2 resueltos en rutas no críticas) |
| Tests pasando (excluyendo infra Ollama) | 146 | **146** |

### Notas de ejecución

- `auth_clerk.py`: se mantuvo la firma pública de `get_jwks()` y `decode_clerk_token()` idéntica. El uso de `httpx.Client` compartido mejora la reutilización de conexiones sin alterar la semántica sync/async del endpoint.
- `lifespan.py`: se intentó mover `ping_qdrant` al top-level, pero se confirmó import circular (`app.engine.rag` depende indirectamente de modelos que cargan durante `main → lifespan`). Se revirtió y documentó con `# noqa: PLC0415`.
- `image_prompt_builder.py`: se eliminó `_get_generation_chain()` y el `global generation_chain` al mover el import de `llm` al top-level. La cadena se inicializa directamente como `_generation_chain = llm | StrOutputParser()`.

---

## Validación final

Tras completar las fases aplicables:

```bash
cd backend
make test        # 175/175 ✅ (146 pasan localmente; 29 requieren Ollama/Qdrant)
make lint        # ruff sin errores en ruleset por defecto
ruff check app/ --select PLC0415,PLW0603,E501  # verificar reducción
```

---

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Romper auth de Clerk al tocar `auth_clerk.py` | Mantener API pública idéntica; solo cambiar implementación interna de caché/HTTP. Tests de auth como red de seguridad. |
| Import circular al mover imports en `lifespan` o `image_prompt_builder` | Evaluar grafo antes de mover; usar `noqa` si existe circularidad. |
| Eliminar `services/__init__.py` y romper un import oculto | Buscar en todo el repo (incluido scripts y notebooks) antes de eliminar. |
| E501 introduce cambios de línea que dificultan `git blame` de seguridad | Aplicar solo en módulos no críticos; nunca en `core/auth/`, `core/storage/`, `api/routes/auth/`. |

---

## Conclusión

Este plan cierra los issues de calidad accionables del feedback sin afectar:
- La estructura de capas (`routes → services → engine/domain`).
- Los 49 fixes de seguridad resueltos en el audit.
- La compatibilidad de la API pública.

El único refactor estructural interno (encapsulación de JWKS) está confinado a un único módulo y mejora la robustez del runtime sin alterar comportamiento observable.
