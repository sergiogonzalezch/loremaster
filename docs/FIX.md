# Problemas pendientes de corrección

Lista de tech debt identificado y aún no corregido. Ordenado por impacto estimado.

---

## 1. Sin autenticación

**Capa:** Backend  
**Impacto:** Alto — crítico para cualquier despliegue fuera de entorno local.

Todos los endpoints son públicos. No hay API keys, JWT ni ningún mecanismo de identidad. Cualquier cliente con acceso a la red puede leer, escribir o borrar colecciones, entidades y documentos.

**Solución sugerida:** Añadir autenticación HTTP Basic o JWT con middleware de FastAPI. Para un proyecto single-user, un API key estático configurado vía `.env` es suficiente en primera iteración.

---

## 2. Ingest de documentos síncrono

**Capa:** Backend  
**Impacto:** Medio — bloquea la respuesta HTTP mientras se procesa el documento completo (extracción, chunking, embedding, upsert en Qdrant).

`ingest_document_service` es `async` pero no delega el trabajo pesado a un worker real. Redis está en el `docker-compose.yml` pero no está conectado a ninguna cola.

**Solución sugerida:** Integrar Celery o ARQ sobre Redis para ejecutar el pipeline de ingest en background. El endpoint devolvería 202 Accepted con el `document_id`; el frontend ya tiene polling de estado de documento (`useCollectionDocumentsStatus`) que soporta esta UX.

---

## 3. Sin optimistic updates en la lista de contenidos

**Capa:** Frontend  
**Impacto:** Bajo — cada acción (confirmar, editar, descartar) hace un refresh completo de la lista de contenidos desde el backend, causando un parpadeo y latencia perceptible.

`handleContentAction` en `EntityDetailPage.tsx` llama a `refreshContents(...)` tras cada operación.

**Solución sugerida:** Actualizar el estado local de `contents` directamente tras la acción (optimistic update), y sincronizar con el backend en background. Si la operación falla, revertir al estado anterior con un mensaje de error.

---

## 4. Token counter aproximado

**Capa:** Frontend  
**Impacto:** Bajo — solo afecta a la información que se muestra al usuario, no a la funcionalidad.

`estimateTokens()` en `frontend/src/utils/tokens.ts` usa una heurística de caracteres dividido por 4. El modelo real (llama3.2) puede tener un ratio diferente, y el conteo real solo es conocido por el backend tras la llamada.

**Solución sugerida:** Exponer el conteo de tokens real en la respuesta del endpoint de generación (`/generate/{category}`) y mostrarlo en el `ContentCard` tras generar. El campo `sources_count` ya demuestra que la respuesta puede devolver metadatos de este tipo.

---

*Generado el 2026-04-25. Ver historial de correcciones aplicadas en los commits del branch `main`.*