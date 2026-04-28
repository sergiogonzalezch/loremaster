# Análisis profundo de cambios recientes en main

*Fecha:* 2026-04-25
*Rango analizado:* últimos 10 commits (HEAD~10..HEAD)
*Volumen:* 58 archivos modificados, +4 105 / −792 líneas

---

## Resumen ejecutivo

En los últimos días se cerraron tres frentes paralelos:

1. *Guardrails de contenido en 3 capas* — validación de input de usuario, contenido extraído y output del LLM.
2. *Filtros, paginación y status filtering* sincronizados entre backend y frontend, con realineación de códigos HTTP.
3. *Suite de tests del frontend* (vitest + happy-dom) con ~658 líneas nuevas.

En paralelo: conteo de documentos/entidades en colecciones, fix de staleness en generación, token counter, y limpieza de whitespace (strip + trim) en ambos lados.

---

## 1. Guardrails de contenido en 3 capas

*Commits:* f6dec1a, 3938af7
*Archivos clave:* backend/app/domain/content_guard.py (nuevo, 39 líneas)

| Capa | Dónde se invoca | Qué bloquea | HTTP devuelto |
|------|----------------|-------------|---------------|
| *1. Input de usuario* | generation_service.py:30 | Query del usuario antes del LLM | *422* |
| *2. Documento extraído* | documents_service.py:40 | Texto de PDFs/docs en ingesta | *422* |
| *3. Output del LLM* | generation_service.py:69, rag_query_service.py | Respuesta antes de persistir | *503* |

Patrones bloqueados (5 regex): contenido sexual explícito, hate speech, instrucciones para armas/explosivos, síntesis de drogas, acoso/humillación.

*Capa 2.5 (soft):* backend/app/engine/llm.py:5-11 inyecta una instrucción de seguridad dentro del prompt del LLM como defensa adicional.

*Manejo en routes:* backend/app/api/routes/entity_content.py:38-44 distingue entre ValueError (input usuario → 422) y RuntimeError (output bloqueado → 503).

---

## 2. Filtros, paginación y status filtering

*Commits:* 61a2700, b643dd0, 297e73b, 81917f0, 3b3265f

*Contrato nuevo del endpoint /contents:*

python
# backend/app/api/routes/entity_content.py:55-57
status: Literal["active", "pending", "confirmed", "discarded", "all"] = Query(default="active")


| Valor | Significado |
|-------|-------------|
| active (default) | pending + confirmed |
| pending | solo pendientes |
| confirmed | solo confirmados |
| discarded | solo descartados |
| all | sin filtro de estado |

*Respuesta:* migrada a PaginatedResponse[T] con meta: { total, page, page_size, total_pages }.

*Frontend:*
- EntityDetailPage.tsx (+58 líneas): tabs UI + estado contentsStatusFilter (default "pending").
- useEntityContents.ts: nuevo parámetro de status.

*Realineación de HTTP status codes (3b3265f):*

| Escenario | Antes | Ahora |
|-----------|-------|-------|
| Editar contenido descartado | 404 | *409* |
| Límite de pendientes excedido | — | *409* |
| Input usuario bloqueado | 422 | 422 |
| Output LLM bloqueado | 503 | 503 |

*Frontend (utils/errors.ts):* clasifica 400-422 como warning (acción del usuario) y 503 como danger (servicio temporal).

---

## 3. Conteo de documentos y entidades en colecciones

*Commit:* 3311179
*Archivos:* backend/app/services/collection_service.py (+59), frontend/src/pages/CollectionsPage.tsx (+10), frontend/src/types/collection.ts (+2)

Implementación con batch query (no N+1):

python
def _fetch_counts(session, collection_ids):
    doc_rows = session.exec(
        select(Document.collection_id, func.count(Document.id))
        .where(Document.collection_id.in_(collection_ids), Document.is_deleted == False)
        .group_by(Document.collection_id)
    ).all()

    entity_rows = session.exec(
        select(Entity.collection_id, func.count(Entity.id))
        .where(Entity.collection_id.in_(collection_ids), Entity.is_deleted == False)
        .group_by(Entity.collection_id)
    ).all()
    return ({c: n for c, n in doc_rows}, {c: n for c, n in entity_rows})


*Costo:* 3 queries por página de colecciones (1 list + 2 counts). Mejorable con subqueries correlacionadas, pero es razonable.

---

## 4. Suite de tests del frontend

*Commit:* ea433cc
*Setup:* nuevo frontend/vitest.config.ts + src/test/setup.ts. Entorno happy-dom, coverage v8.

| Archivo | Líneas | Cubre |
|---------|--------|-------|
| ConfirmModal.test.tsx | 54 | Render + callbacks |
| ContentCard.test.tsx | 153 | Status, acciones, estado |
| TokenCounter.test.tsx | 32 | Vacío / corto / largo / warning |
| constants.test.ts | 75 | Labels y enums |
| errors.test.ts | 58 | parseApiError, getErrorMessage |
| formatters.test.ts | 22 | Fechas y formatos |
| tokens.test.ts | 31 | estimateTokens |
| useDebouncedValue.test.ts | 36 | Hook debounce |
| useEntityContents.test.ts | 101 | Fetch paginado |
| useGenerate.test.ts | 95 | Loading / error / cancel |

*Total:* ~658 líneas nuevas.

*Gap relevante:* vitest.config.ts *excluye* src/pages/** y src/api/** del coverage. Las páginas grandes (EntityDetailPage, GeneratePage, CollectionDetailPage) — donde vive la mayor parte de la lógica de UX — no se prueban.

---

## 5. Fix de generate staleness

*Commit:* d717048
*Archivo nuevo:* frontend/src/hooks/useCollectionDocumentsStatus.ts

Polling cada 3s mientras existan documentos en processing. GeneratePage.tsx consulta el estado antes de generar y bloquea si no hay documentos completed.

typescript
const canGenerate = await refresh();
if (!canGenerate) return;


*Tradeoff:* polling de 3s no escala bien con muchas colecciones grandes. Candidato natural a SSE / WebSocket más adelante.

---

## 6. Token counter

*Plan:* 7199d84 (Feature Plan)
*Componente:* TokenCounter con estimateTokens(text) (~4 chars/token) y prop warnAt (default QUERY_TOKEN_WARN_AT).

Cuando tokens >= warnAt cambia a estilo text-warning y muestra "considera acortarla".

*Usado en:* GeneratePage, EntityDetailPage, CollectionDetailPage.

---

## 7. Strip-fields (backend) + trim (frontend)

*Commits:* 1cc459e, cde0fa9

*Backend* — .strip() en:
- entities_service.py (name/description en create/update)
- collection_service.py (name/description)
- content_management_service.py:77 (new_text)
- generation_service.py:29 (query)

*Frontend* — frontend/src/utils/strings.ts:

typescript
export function trimStringValues<T extends object>(obj: T): T {
  return Object.fromEntries(
    Object.entries(obj).map(([k, v]) => [k, typeof v === "string" ? v.trim() : v])
  ) as T;
}


Aplicado en api/{collections,contents,entities,generate}.ts. Defensa en profundidad razonable contra whitespace problemático.

---

## 8. Documentación

*Commits:* 604d1d5, e9bf5a7, 08bde7f

- docs/DOCUMENTATION.md +118 líneas (3 partes).
- Eliminado docs/GUARDRAILS-PLAN.md (−166).
- Eliminado docs/backend-pendientes-fase-posterior.md (−29).
- backend/README.md +18, frontend/README.md +54.

---

## 9. Distribución de cambios

| Bloque | Líneas netas (aprox.) |
|--------|----------------------|
| Frontend feature | ~700 |
| Backend feature | ~400 |
| Tests frontend | ~658 |
| Tests backend | ~100 |
| Docs | +118 / −195 |
| package-lock.json | +3 207 (devDeps de testing) |

---

## 10. Red flags ordenados por prioridad

### Críticos

1. *Guardrails sin normalización ni tests adversariales.* Los regex no aplican lower() ni normalización Unicode (unicodedata.normalize("NFKD", ...)). Variantes triviales (p0rn, s3xo, espacios entremedios) pasan sin problema. Falta una batería de tests de evasión.

2. *Páginas excluidas del coverage de tests.* vitest.config.ts excluye src/pages/**. La lógica de UX más compleja (filtros, paginación, polling, gating de generación) no está probada.

3. *Sin auditoría de contenido bloqueado.* Los rechazos por guardrail no se persisten. No existe campo flagged ni moderation_reason en EntityContent. Imposible revisar falsos positivos a posteriori.

### Medianos

4. *Polling de 3 s* en useCollectionDocumentsStatus: funcional pero pesado a escala.

5. *RuntimeError capturado genérico* en entity_content.py:41-44: si otro RuntimeError borbotea, se confunde con bloqueo de guardrail.

6. *Bumps mayores de deps* (Bootstrap 5.3.8, React 19, TS 5) sin nota de regresión visible en commits.

### Menores

7. *Mensajes de commit bilingües e inconsistentes* (Fronend fix, Strip-fields, Implementa guardrails…): dificulta lectura de git log.

8. *Runbook de guardrails ausente.* GUARDRAILS-PLAN.md se eliminó sin un reemplazo que documente cómo mantener/actualizar los patrones.

---

## Próximos pasos sugeridos

1. PR pequeño: normalización (lower() + NFKD) y tests adversariales en content_guard.py.
2. PR pequeño: tabla moderation_log (id, content_id, layer, pattern_matched, snippet, created_at) para auditar rechazos.
3. Revisar la exclusión de src/pages/** en vitest.config.ts — al menos cubrir los happy paths de EntityDetailPage y GeneratePage.
4. Considerar SSE/WebSocket para useCollectionDocumentsStatus en lugar de polling.