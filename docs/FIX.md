# Problemas pendientes de corrección

Lista de tech debt identificado y aún no corregido. Ordenado por impacto estimado.

---

## 1. Sin autenticación

**Capa:** Backend  
**Impacto:** Alto — crítico para cualquier despliegue fuera de entorno local.

Todos los endpoints son públicos. No hay API keys, JWT ni ningún mecanismo de identidad. Cualquier cliente con acceso a la red puede leer, escribir o borrar colecciones, entidades y documentos.

**Solución sugerida:** Añadir autenticación HTTP Basic o JWT con middleware de FastAPI. Para un proyecto single-user, un API key estático configurado vía `.env` es suficiente en primera iteración.

---

## ~~2. Ingest de documentos síncrono~~ ✅ Resuelto

**Capa:** Backend  
**Solución aplicada:** El endpoint `POST /documents` ahora devuelve `202 Accepted` inmediatamente tras crear el registro en DB con `status=processing`. La fase pesada (`ingest_chunks` → Qdrant → embeddings) se ejecuta como `BackgroundTask` de FastAPI usando la misma sesión de BD inyectada por dependencia. El frontend ya tenía polling de estado (`useCollectionDocumentsStatus`) que soporta esta UX sin cambios.

---

## ~~3. Sin optimistic updates en la lista de contenidos~~ ✅ Resuelto

**Capa:** Frontend  
**Solución aplicada:** `ContentCard` aplica ahora actualizaciones optimistas antes de cada llamada a la API (confirm → `status: confirmed` + descarte de hermanos; discard → `status: discarded`; delete → eliminación inmediata; edit → actualiza `content` y `updated_at`). Si la API falla, revierte al estado anterior. El `handleContentAction` en `EntityDetailPage` usa `{ silent: true }` en `refreshContents` para la sincronización en background, eliminando el parpadeo del spinner.

---

## ~~4. Token counter aproximado~~ ✅ Resuelto

**Capa:** Backend + Frontend  
**Solución aplicada:** `EntityContent` incluye ahora el campo `token_count` (heurística `len(answer) // 4` calculada en el backend tras generar). Se añadió migración Alembic (`a1b2c3d4e5f6`). El frontend muestra `~N tokens` como badge en el `ContentCard`, junto al badge de fuentes, cuando el valor es mayor que 0.

---

*Generado el 2026-04-25. Actualizado el 2026-04-26. Ver historial de correcciones aplicadas en los commits del branch `main`.*