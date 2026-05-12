# Registro de Implementacion — Fase 6 (Auditoria de Seguridad)

**Fecha:** 2026-05-11
**Referencia:** `docs/AUDIT-RESULTS-11-05-26.md`, `docs/PLAN-AUDIT-MEDIUM-LOW.md`
**Estado:** Completada

---

## Problemas atacados en esta fase

| ID | Severidad | Problema | Estado final |
|---|---|---|---|
| M-9 | Medio | CORS no exige HTTPS en entorno `demo` | **No resuelto → Completo** |
| M-12 | Medio | Default `environment="local"` fail-open | **No resuelto → Parcialmente resuelto** |
| L-11 | Bajo | Token revocation TTL no documentado | **No resuelto → Completo** |
| L-13 | Bajo | Docker compose expone Qdrant/Redis al host | **No resuelto → Completo** |

---

## Cambios aplicados

### 1. M-9 — CORS HTTPS en `demo`

**Archivo modificado:**
- `backend/app/core/config/__init__.py`

**Descripcion:**
Se extendio la validacion de HTTPS en `ALLOWED_ORIGINS` para incluir el entorno `demo`:

**Antes:**
```python
if self.environment == "production":
```

**Despues:**
```python
if self.environment in ("production", "demo"):
```

Esto asegura que tanto `production` como `demo` requieran HTTPS en todos los origenes CORS.

**Decision de diseno:** El entorno `demo` se trata con la misma rigurosidad que `production` para CORS, ya que tipicamente es accesible desde Internet.

**Rollback:** Revertir a `if self.environment == "production":`.

---

### 2. M-12 — Default `environment="local"` fail-open

**Archivo modificado:**
- `backend/app/main.py`

**Descripcion:**
Se agrego un log de WARNING en el startup de la aplicacion cuando `environment == "local"`:

```python
if settings.environment == "local":
    logger.warning(
        "WARNING: Ejecutando en entorno 'local'. "
        "Algunas guardas de seguridad estan relajadas. "
        "No usar en produccion (M-12)."
    )
```

**Decision de diseno:** No se cambio el valor default (`environment="local"`) para no romper el flujo de desarrollo local. En su lugar, se hace visible el riesgo mediante un WARNING en los logs. Esto alerta a los operadores si accidentalmente despliegan en produccion sin cambiar el entorno.

**Rollback:** Quitar el bloque `if settings.environment == "local"`.

---

### 3. L-11 — Token revocation TTL documentado

**Archivo modificado:**
- `backend/app/core/auth/__init__.py`

**Descripcion:**
Se agrego un comentario/documentacion de politica de `token_version` al inicio del modulo:

```python
# Politica de token_version (L-11):
# - token_version se incrementa en logout para invalidar tokens previos
# - Tokens tienen TTL de ACCESS_TOKEN_EXPIRE_MINUTES (default 24h)
# - Recomendacion: usar refresh tokens de 7 dias con access tokens de 15-60 min
#   en produccion para minimizar ventana de exposicion
```

Se actualizo tambien el docstring de `create_access_token` para referenciar esta politica.

**Decision de diseno:** Documentacion como primera medida. En el futuro se puede implementar refresh tokens formales si el proyecto lo requiere.

**Rollback:** Eliminar el comentario y revertir el docstring.

---

### 4. L-13 — Docker compose bind a 127.0.0.1

**Archivo modificado:**
- `backend/docker-compose.yml`

**Descripcion:**
Se agrego bind a `127.0.0.1` para todos los servicios expuestos:

- Qdrant: `127.0.0.1:6333:6333`
- PostgreSQL: `127.0.0.1:5433:5432`
- Redis: `127.0.0.1:6379:6379`

**Decision de diseno:** Esto limita el acceso a los servicios internos solo a la maquina local, previniendo exposicion accidental en redes compartidas (ej. Wi-Fi publico). En produccion, `docker-compose.prod.yml` ya no expone estos puertos al host.

**Rollback:** Revertir los binds a `127.0.0.1`.

---

## Resultados de validacion

### Tests ejecutados

```
cd backend && python -m pytest -q

175 passed in 23.28s
```

**Desglose:**
- Todos los tests pasan sin modificaciones
- Sin tests nuevos (cambios de configuracion/documentacion)

---

## Estado actual de la auditoria (post-Fase 6)

| Estado | Pre-Fase 6 | Post-Fase 6 | Delta |
|---|---|---|---|
| Resueltos | 34 | **37** | +3 |
| Parcialmente resueltos | 2 | **3** | +1 |
| No resueltos | 14 | **11** | -3 |
| No verificados | 3 | 3 | 0 |
| **Total** | **53** | **53** | — |

Los 3 problemas que pasaron de "no resueltos" a "resueltos" son: **M-9, L-11, L-13**.

**M-12** paso de "no resuelto" a "parcialmente resuelto" (log WARNING en lugar de cambiar el default).

---

## Proxima fase

**Fase 7 — Content/Entity Hardening:**
- M-3: `edit_content` sin `check_user_input`
- L-3: TOCTOU en `delete_image_service`

---

*Documento generado el 2026-05-11 tras la validacion exitosa de la Fase 6.*

> **Nota de resolucion (2026-05-11):** Los problemas atacados en esta fase fueron verificados y estan reflejados en [`AUDIT-RESULTS-11-05-26.md`](AUDIT-RESULTS-11-05-26.md).
