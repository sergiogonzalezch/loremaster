# Sesión AI Engineering — Frontend Lore Master

Fecha: 2026-04-18

## Contexto

Revisión del frontend (React 19 + Vite + TS + React Bootstrap) enfocada en brechas
de AI Engineering sobre el flujo RAG contra el backend FastAPI + Ollama + Qdrant.

El diseño visual y la integración CRUD con el backend ya estaban hechos. La sesión
cubre las brechas de experiencia y robustez para features LLM.

## Plan

### Fase 1 — Solo frontend
1. Markdown rendering en salida LLM
2. Hook `useGenerate` con `AbortController` (cancelar generación)
3. Guardrail de drafts pendientes (≤5)
4. Estimación de tokens en inputs
5. Auditoría de revalidaciones post-mutación

### Fase 2 — Requiere cambios de backend
6. Sources visibles (chunks recuperados, no solo `sources_count`)
7. Streaming SSE

### Fase 3 — Opcional
8. TanStack Query para cache/dedupe/retry

## Referencias del backend relevantes

- `backend/app/services/entity_text_draft_service.py:19` → `MAX_PENDING_DRAFTS = 5`
- `backend/app/models/entity_text_draft.py:54` → `query: min_length=5`
- `backend/app/models/generate.py:6` → `query: min_length=5`
- `backend/app/core/config.py` → `temperature=0.7`, `max_tokens=2000`, `top_k=4`
- `backend/app/core/llm_client.py:6-24` → system prompt en español (produce markdown)

## Progreso

### ✅ 1.1 Markdown rendering
- Instalado `react-markdown`, `rehype-sanitize`, `remark-gfm`
- Nuevo componente `src/components/MarkdownContent.tsx` sanitiza y soporta GFM (tablas, task lists, strikethrough)
- Estilos dedicados `.lm-markdown` añadidos en `src/index.css`
- Reemplazado `<p style={pre-wrap}>` por `<MarkdownContent>` en:
  - `src/pages/GeneratePage.tsx:107`
  - `src/pages/CollectionDetailPage.tsx` (Generate tab)
  - `src/pages/EntityDetailPage.tsx` (DraftCard body)

### ✅ 1.2 Hook useGenerate con AbortController
- `src/api/apiClient.ts`: nueva `ApiAbortError`; `apiFetch` propaga `signal` y traduce `AbortError` del navegador
- `src/api/generate.ts` y `src/api/drafts.ts`: ambas funciones aceptan `AbortSignal` opcional como último argumento
- Nuevo `src/hooks/useGenerate.ts`: hook genérico que envuelve funciones de API con soporte de cancelación. Expone `{ data, error, isLoading, isCancelled, run, cancel, reset }` y aborta peticiones en curso al desmontarse
- Botón "Cancelar" visible durante generación en las 3 páginas (GeneratePage, CollectionDetailPage Generate tab, EntityDetailPage)
- Muestra "Generación cancelada" como alerta secundaria cuando el usuario aborta

### ✅ 1.3 Guardrail de drafts pendientes
- Constantes centralizadas en `src/utils/constants.ts`: `MAX_PENDING_DRAFTS=5`, `MIN_QUERY_LENGTH=5`, `MAX_GENERATION_TOKENS=2000` (reflejan el backend)
- En `EntityDetailPage`: cuento `pendingCount` del array de drafts
- Si `>= 5`: input y botón quedan deshabilitados, con `title` tooltip y un `Alert` explicativo
- Si `> 0 && < 5`: contador sutil `N/5 borradores pendientes` bajo el form

### ✅ 1.4 Estimación de tokens
- `src/utils/tokens.ts`: `estimateTokens(text)` = `chars/4` (aproximación razonable en ES/EN)
- `src/components/TokenCounter.tsx`: muestra `≈ N tokens` en gris; vira a amarillo si supera `QUERY_TOKEN_WARN_AT` (400) sugiriendo acortar
- Integrado bajo los 3 textareas de query

### ✅ 1.5 Revalidación post-mutación
- Auditadas todas las mutaciones (collections, documents, entities, drafts)
- Fix: función `refreshEntityQuiet` + `handleContentAction` en `EntityDetailPage` refetchea **entity + contents** después de cada acción, sin tocar el loading global (para no parpadear la página).

## Cómo probar

1. Backend arriba (`http://localhost:8000`), Ollama + Qdrant corriendo
2. Frontend: `cd frontend && npm run dev` (necesita Node 20+; ver nota abajo)
3. Abrir una colección con documentos ya indexados
4. **Markdown**: generar texto con una query que invite listas o código → respuesta con formato
5. **Cancelar**: durante generación aparece botón "Cancelar"; al pulsarlo la petición aborta y se muestra alerta
6. **Token counter**: escribir >1600 caracteres en el textarea → el contador vira a amarillo
7. **Guardrail drafts**: en una entidad, generar 5 drafts sin confirmar; al 6to el botón queda deshabilitado con tooltip
8. **Revalidación post-confirm**: confirmar un draft → el description de la entity en la cabecera refleja el cambio sin recargar

## Nota operativa

- El entorno tiene Node 18.19. Vite 8 requiere Node 20+, así que `npm run build` falla en el entorno actual (no por los cambios de esta sesión). `tsc -b` (typecheck) sí pasa limpio. Sugerido: `nvm use 20` o actualizar `.nvmrc`.

## Próximos pasos

**Fase 2 (requiere backend):**
- Devolver los chunks recuperados (texto + documento + score) en `/generate/text` y `/entities/{id}/generate`. Con eso el frontend puede mostrar un acordeón de fuentes bajo cada respuesta.
- Endpoint SSE que emita tokens del LLM en streaming. Frontend consume con `fetch` + `ReadableStream`.

**Fase 3 (opcional, escala):**
- TanStack Query para cache, dedupe de queries RAG idénticas y retries exponenciales en 503.
- React Hook Form para los formularios de creación/edición.

