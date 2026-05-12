# Plan de Implementacion — Fases 10-12 (C-2, H-4, H-5, H-13)

**Fecha:** 2026-05-11
**Referencia:** `docs/AUDIT-RESULTS-11-05-26.md`
**Estrategia:** Cambios minimos, defensa en profundidad, tests pasan despues de cada fase.

---

## Hallazgos a resolver

| ID | Severidad | Problema | Complejidad |
|---|---|---|---|
| **C-2** | Critico | Clerk branch en `get_current_user` no verifica `is_deleted` ni `token_version` | Media |
| **H-4** | Alto | Prompt injection via PDF: contenido extraido puede cerrar etiquetas `</context></user_request>` | Media |
| **H-5** | Alto | Prompt injection via `entity.name/description`: interpolados fuera de `<context>` sin escaping | Media |
| **H-13** | Alto | JWT almacenado en `localStorage` — vulnerable a exfiltracion XSS | Alta |

---

## Fase 10 — C-2: Clerk branch verifica usuario en BD

**Archivo:** `backend/app/core/auth/dependencies.py`
**Problema:** `get_current_user` retorna directamente `decode_clerk_token()` en produccion sin verificar BD.

### 10.1 Verificar is_deleted
Despues de `decode_clerk_token`, buscar usuario en BD por `sub` y verificar que no este eliminado.

### 10.2 Verificar token_version
Nota: Los tokens de Clerk no incluyen `token_version` por defecto. La solucion:
- Verificar `token_version` SOLO si existe en el payload del token Clerk (custom claim)
- Si no existe, solo verificar `is_deleted`
- Documentar que para revocacion completa con Clerk se requiere configurar custom claims o usar webhook de Clerk para sincronizar revocaciones

### 10.3 Tests
Verificar que `get_current_user` en produccion rechaza usuarios soft-deleted.

---

## Fase 11 — H-4/H-5: Defensa estructural contra prompt injection

**Archivos:**
- `backend/app/domain/prompt_templates.py`
- `backend/app/services/entity/generation_service.py`

### 11.1 H-4: Sanitizar contenido de documentos antes de interpolar
**Archivo:** `backend/app/services/document/documents_service.py` (o donde se construye el contexto RAG)
**Problema:** Texto extraido de PDFs se pasa directamente como `context` a `render_prompt`.
**Fix:** Agregar funcion `_sanitize_context()` que:
- Reemplace `</context>` por `&lt;/context&gt;` (HTML escape) o `[CONTEXT_CLOSE]`
- Reemplace `</user_request>` por `&lt;/user_request&gt;` o `[USER_REQUEST_CLOSE]`
- O agregar validacion que rechaze documentos que contengan estas secuencias

Decision: Escapar las secuencias para no rechazar documentos legitimos que mencionen estas etiquetas (ej. documentacion tecnica).

### 11.2 H-5: Sanitizar entity.name y entity.description
**Archivo:** `backend/app/services/entity/generation_service.py`
**Problema:** `entity.name` y `entity.description` se interpolan en `extra_context` sin escaping de etiquetas XML.
**Fix:** Aplicar el mismo escape a `entity.name` y `entity.description` antes de construir `extra_context`.

### 11.3 Centralizar escape en prompt_templates.py
**Archivo:** `backend/app/domain/prompt_templates.py`
**Fix:** Mejorar `_escape()` para tambien escapar etiquetas XML:
```python
def _escape(v: str) -> str:
    v = v.replace("{", "{{").replace("}", "}}")
    v = v.replace("</context>", "[ESCAPED_CONTEXT_CLOSE]")
    v = v.replace("</user_request>", "[ESCAPED_USER_REQUEST_CLOSE]")
    return v
```

**Decision de diseno:** Usar `[ESCAPED_*]` en lugar de HTML entities para que el LLM siga viendo el texto como contenido, no como markup.

### 11.4 Tests
Verificar que `render_prompt` escapa correctamente secuencias maliciosas.

---

## Fase 12 — H-13: Mitigar JWT en localStorage

**Archivo:** `frontend/src/utils/token.ts`
**Problema:** Token JWT persistente en `localStorage`, vulnerable a exfiltracion XSS.

### 12.1 Migrar a sessionStorage
**Fix:** Cambiar `localStorage` por `sessionStorage`:
- El token se pierde al cerrar la pestaña (reduce ventana de exposicion)
- No afecta funcionalidad durante la sesion activa
- Mitiga ataques XSS persistentes (el token no sobrevive al cerrar el navegador)

### 12.2 Documentar migracion a cookies HttpOnly
**Fix:** Agregar comentarios en `token.ts` indicando que la solucion definitiva es migrar a cookies `HttpOnly` + `SameSite=Strict` y que `sessionStorage` es solo una mitigacion intermedia.

### 12.3 Decision de diseno
No se implementa la migracion completa a cookies porque requiere:
- Backend: setear cookies en login/register
- Backend: leer cookies en `get_current_user`
- Frontend: eliminar manejo manual de Authorization header
- Frontend: actualizar `api/client.ts`

Esto es un cambio arquitectonico que se deja como plan futuro.

---

## Criterios de exito

- [ ] C-2: `get_current_user` en produccion verifica `is_deleted` (y `token_version` si disponible)
- [ ] H-4: Contenido de documentos escapa etiquetas de cierre de prompt
- [ ] H-5: `entity.name` y `entity.description` escapan etiquetas de cierre de prompt
- [ ] H-13: Token usa `sessionStorage` en lugar de `localStorage`
- [ ] 175 tests backend pasan
- [ ] 121 tests frontend pasan
- [ ] AUDIT-RESULTS actualizado

---

*Plan generado el 2026-05-11.*
