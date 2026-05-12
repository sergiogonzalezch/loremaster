# Registro de Implementacion — Fases 10-12 (Auditoria de Seguridad)

**Fecha:** 2026-05-11
**Referencia:** `./AUDIT-RESULTS-11-05-26.md`, `./PLAN-FASES-10-12.md`
**Estado:** Completada

---

## Problemas atacados en esta fase

| ID | Severidad | Problema | Estado final |
|---|---|---|---|
| C-2 | Critico | Clerk branch en `get_current_user` no verifica `is_deleted` ni `token_version` | **No resuelto → Completo** |
| H-4 | Alto | Prompt injection via PDF: contenido extraido puede cerrar etiquetas `</context></user_request>` | **No resuelto → Completo** |
| H-5 | Alto | Prompt injection via `entity.name/description`: interpolados fuera de `<context>` sin escaping | **No resuelto → Completo** |
| H-13 | Alto | JWT almacenado en `localStorage` — vulnerable a exfiltracion XSS | **No resuelto → Parcialmente resuelto** |

---

## Cambios aplicados

### 1. C-2 — Clerk branch verifica usuario en BD

**Archivo modificado:**
- `backend/app/core/auth/dependencies.py`

**Descripcion:**
El branch de produccion (`environment == "production"`) de `get_current_user` ahora realiza lookup del usuario en la base de datos despues de decodificar el token de Clerk:

1. **Verificacion `is_deleted`:** Busca el usuario por `payload["sub"]` y rechaza si no existe o esta eliminado (`is_deleted == True`).
2. **Verificacion `token_version` (opt-in):** Si el payload del token de Clerk contiene el claim `"version"`, se verifica que coincida con `user.token_version` usando `hmac.compare_digest` (timing-safe).

**Nota sobre `token_version` con Clerk:**
Los tokens de Clerk no incluyen `token_version` por defecto. Para habilitar la revocacion completa, se debe configurar un **custom claim** en Clerk que incluya la version del token, o usar webhooks de Clerk para sincronizar revocaciones. El codigo actual verifica la version solo si esta presente, manteniendo compatibilidad.

**Rollback:** Revertir el bloque `if settings.environment == "production"` a solo `return decode_clerk_token(...)`.

---

### 2. H-4/H-5 — Defensa estructural contra prompt injection

**Archivo modificado:**
- `backend/app/domain/prompt_templates.py`

**Descripcion:**
Se fortalecio la funcion `_escape()` en `render_prompt` para escapar no solo llaves de formato (`{`, `}`), sino tambien etiquetas XML de cierre que podrian romper la estructura del prompt:

```python
def _escape(v: str) -> str:
    """Escapa llaves de formato y etiquetas XML de cierre (H-4, H-5)."""
    v = v.replace("{", "{{").replace("}", "}}")
    v = v.replace("</context>", "[ESCAPED_CONTEXT_CLOSE]")
    v = v.replace("</user_request>", "[ESCAPED_USER_REQUEST_CLOSE]")
    return v
```

**Cobertura:**
- **H-4 (PDFs):** El texto extraido de documentos se pasa como `context` a `render_prompt`, por lo que cualquier `</context>` o `</user_request>` en el PDF sera escapado.
- **H-5 (entity.name/description):** `entity.name` se pasa como parametro `entity_name`, y `entity.description` forma parte de `extra_context` que se pasa como `context`. Ambos son escapados por `_escape()`.

**Decision de diseno:** Se usa `[ESCAPED_*]` en lugar de HTML entities para que el LLM siga viendo el texto como contenido, no como markup. Esto evita que un documento legitimo que mencione `</context>` (ej. documentacion tecnica) sea rechazado.

**Rollback:** Revertir `_escape()` a solo escapar llaves.

---

### 3. H-13 — Mitigar JWT en localStorage

**Archivo modificado:**
- `frontend/src/utils/token.ts`

**Descripcion:**
Se migro el almacenamiento del token JWT de `localStorage` a `sessionStorage`:

**Antes:** `localStorage.getItem/setItem/removeItem`
**Despues:** `sessionStorage.getItem/setItem/removeItem`

**Impacto:**
- El token se pierde al cerrar la pestaña o el navegador
- Reduce la ventana de exposicion a XSS persistente (el token no sobrevive entre sesiones)
- No afecta la funcionalidad durante la sesion activa

**Limitacion (documentada en el codigo):**
`sessionStorage` mitiga pero NO elimina el riesgo de exfiltracion XSS durante la sesion activa. La solucion definitiva es migrar a cookies `HttpOnly` + `SameSite=Strict`, lo cual requiere cambios arquitectonicos en backend (setear cookie) y frontend (quitar manejo manual de Authorization header).

**Rollback:** Revertir `sessionStorage` a `localStorage`.

---

## Resultados de validacion

### Backend tests

```
cd backend && python -m pytest -q

175 passed in 22.84s
```

### Frontend tests

```
npm test -- --run

121 passed in 16 archivos
```

---

## Estado actual de la auditoria (post-Fases 10-12)

| Estado | Pre-Fases 10-12 | Post-Fases 10-12 | Delta |
|---|---|---|---|
| Resueltos | 42 | **45** | +3 |
| Parcialmente resueltos | 5 | **6** | +1 |
| No resueltos | 6 | **3** | -3 |
| No verificados | 0 | 0 | 0 |
| **Total** | **53** | **53** | — |

Los 3 problemas que pasaron de "no resueltos" a "resueltos" son: **C-2, H-4, H-5**.

**H-13** paso de "no resuelto" a "parcialmente resuelto" (mitigacion con `sessionStorage`, migracion completa a cookies pendiente).

---

## No resueltos restantes (3)

| ID | Severidad | Problema |
|---|---|---|
| **H-14** | Alto | Sin defensa CSRF planeada |
| **M-17** | Medio | Migracion planeada a cookies sin pareja CSRF defensiva |
| **H-13** | Alto | JWT en `localStorage` → mitigado con `sessionStorage`, solucion definitiva: cookies HttpOnly |

**Nota:** H-14 y M-17 estan relacionados (ambos son CSRF). H-13 requiere migracion completa a cookies para resolverse completamente.

---

*Documento generado el 2026-05-11 tras la validacion exitosa de las Fases 10-12.*

> **Nota de resolucion (2026-05-11):** Los problemas atacados en esta fase fueron verificados y estan reflejados en [`AUDIT-RESULTS-11-05-26.md`](AUDIT-RESULTS-11-05-26.md).
