# Registro de Implementación — Fase 3 (Auditoría de Seguridad)

**Fecha:** 2026-05-11  
**Referencia:** `docs/AUDIT-RESULTS-11-05-26.md`, `docs/PLAN-AUDIT-PARTIALS.md`, `docs/AUDIT-FASE2-LOG.md`  
**Estado:** ✅ Completada  

---

## Problemas atacados en esta fase

| ID | Severidad | Problema | Estado final |
|---|---|---|---|
| C-6 | 🔴 Crítico | Mount `/media` público sin auth ni Content-Disposition | **Parcialmente resuelto → Completo** |
| C-8 | 🔴 Crítico | Postgres con credenciales hardcodeadas | **Parcialmente resuelto → Completo** |
| M-8 | 🟡 Medio | AWS credenciales de test en `.env.example` | **Parcialmente resuelto → Completo** |

---

## Cambios aplicados

### 1. C-6 — Lista blanca estricta de Content-Type en `/media`

**Archivo modificado:**
- `backend/app/api/routes/media.py`

**Descripción:**
Se reforzó el endpoint `/media/{path:path}` con dos mejoras de seguridad:

1. **Lista blanca estricta de extensiones:** Si `suffix` no está en `media_types` (`.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`), se devuelve **404** en lugar de servir como `application/octet-stream`. Esto previene que un archivo `.html` o `.js` subido maliciosamente se ejecute en el origin del API.

2. **`Content-Disposition: inline`:** Se agregó el header `Content-Disposition: inline; filename="..."` que ayuda al navegador a decidir cómo mostrar el recurso. Se usó `inline` (no `attachment`) para preservar la visualización de imágenes via `<img src=...>` en el frontend.

**Decisión de diseño:** No se agregó autenticación al endpoint `/media` porque los navegadores no envían headers `Authorization` en requests de recursos estáticos (`<img>`, `<link>`, etc.). Agregar auth rompería la carga de avatares e imágenes públicas. La mitigación se logra mediante:
- Lista blanca de extensiones
- `X-Content-Type-Options: nosniff`
- `Content-Disposition: inline`

**Rollback:** Revertir el bloque de validación de `suffix` y el header `Content-Disposition`.

---

### 2. C-8 — Docker Compose producción sin defaults hardcodeados

**Archivo creado:**
- `backend/docker-compose.prod.yml`

**Archivo modificado:**
- `backend/docker-compose.yml`

**Descripción:**
Se creó `docker-compose.prod.yml` con configuración estricta para producción:
- **Postgres:** Variables requeridas (`${POSTGRES_PASSWORD:?required}`), sin defaults. Bind a `127.0.0.1:5433:5432`.
- **Redis:** Bind a `127.0.0.1:6379:6379`.
- **Qdrant:** Sin exposición de puertos al host (solo red interna Docker).

Se agregó un comentario en `docker-compose.yml` (dev) indicando que para producción se debe usar `docker-compose.prod.yml`.

**Decisión de diseño:** Mantener `docker-compose.yml` intacto para desarrollo local (con defaults y puertos expuestos), mientras que `docker-compose.prod.yml` fuerza variables externas y binds restrictivos. Esto no rompe el flujo de desarrollo existente.

**Rollback:** Eliminar `docker-compose.prod.yml` y quitar el comentario en `docker-compose.yml`.

---

### 3. M-8 — Advertencias en `.env.example`

**Archivo modificado:**
- `backend/.env.example`

**Descripción:**
Se agregaron comentarios de advertencia (`⚠️ WARNING`) en dos secciones:
1. **JWT `SECRET_KEY`:** Indica que debe cambiarse antes de producción y que el validador rechazará valores por defecto en entornos no locales.
2. **AWS credenciales:** Indica que no se deben usar credenciales reales en el archivo y sugiere IAM roles o secrets manager para producción.

**Decisión de diseño:** `.env.example` es un template, no un archivo de configuración activo. Las advertencias sirven como recordatorio para operadores que hagan `cp .env.example .env`.

**Rollback:** Revertir los comentarios agregados.

---

## Resultados de validación

### Tests ejecutados

```
cd backend && python -m pytest -q

175 passed in 21.71s
```

**Desglose:**
- Todos los tests pasan, incluyendo los que requieren Ollama
- Sin tests modificados en esta fase

---

## Estado actual de la auditoría (post-Fase 3)

| Estado | Pre-Fase 3 | Post-Fase 3 | Delta |
|---|---|---|---|
| Resueltos | 24 | **27** | +3 |
| Parcialmente resueltos | 9 | **6** | -3 |
| No resueltos | 17 | 17 | 0 |
| No verificados | 3 | 3 | 0 |
| **Total** | **53** | **53** | — |

Los 3 problemas que pasaron de "parcialmente resueltos" a "resueltos" son: **C-6, C-8, M-8**.

---

## Resumen acumulado de las 3 fases

| Fase | Problemas resueltos |
|---|---|
| Fase 1 | C-3, C-5, H-1, H-2, C-7 (5) |
| Fase 2 | M-18, L-2, M-13, H-3 (4) |
| Fase 3 | C-6, C-8, M-8 (3) |
| **Total** | **12** |

**Queda pendiente:**
- **6 problemas parcialmente resueltos** (requieren acciones más complejas o de mayor riesgo)
- **17 problemas no resueltos** (algunos requieren cambios arquitectónicos como migración a cookies/CSRF)
- **3 problemas no verificados** (pendientes de revisión del frontend)

---

> **Nota de resolución (2026-05-11):** Los 3 problemas atacados en esta fase fueron verificados como **resueltos** y están reflejados en [`AUDIT-RESULTS-11-05-26.md`](AUDIT-RESULTS-11-05-26.md).

*Documento generado el 2026-05-11 tras la validación exitosa de la Fase 3.*
