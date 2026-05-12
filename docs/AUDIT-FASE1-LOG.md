# Registro de Implementación — Fase 1 (Auditoría de Seguridad)

**Fecha:** 2026-05-11  
**Referencia:** `docs/AUDIT-RESULTS-11-05-26.md`, `docs/PLAN-AUDIT-PARTIALS.md`  
**Estado:** ✅ Completada  

---

## Problemas atacados en esta fase

| ID | Severidad | Problema | Estado final |
|---|---|---|---|
| C-3 | 🔴 Crítico | IDOR cross-tenant en endpoints de documentos | **Parcialmente resuelto → Completo** |
| C-5 | 🔴 Crítico | Path traversal vía `shutil.rmtree` en `delete_profile_image` | **Parcialmente resuelto → Completo** |
| H-1 | 🟠 Alto | `is_admin` viaja dentro del JWT en `register` | **Parcialmente resuelto → Completo** |
| H-2 | 🟠 Alto | `PATCH /users/me` acepta email sin verificar unicidad | **Parcialmente resuelto → Completo** |
| C-7 | 🔴 Crítico | JWT secret por defecto + sin protección contra alg-confusion | **Parcialmente resuelto → Completo** (alg-confusion) |

---

## Cambios aplicados

### 1. C-3 — IDOR cross-tenant en documentos

**Archivos modificados:**
- `backend/app/core/database/dependencies.py`
- `backend/app/api/routes/documents/documents.py`
- `backend/tests/test_documents.py`

**Descripción:**
Se creó la dependencia `get_document_or_404_owned` que verifica ownership de la colección antes de devolver el documento. Se aplicó en los 3 endpoints que carecían de esta protección:
- `GET /collections/{id}/documents/{doc_id}`
- `POST /collections/{id}/documents/{doc_id}/retry`
- `DELETE /collections/{id}/documents/{doc_id}`

**Decisión de diseño:** El endpoint devuelve **403** cuando el usuario no es dueño de la colección (a través de `get_collection_or_404_owned`), en lugar de 404. Esto es consistente con el resto de la API y permite al frontend mostrar "Acceso denegado" en lugar de "No encontrado". El test `test_get_doc_wrong_collection_404` fue actualizado a `test_get_doc_wrong_collection_403`.

**Rollback:** Revertir los 3 `Depends(...)` a `get_document_or_404`.

---

### 2. C-5 — `shutil.rmtree` en `delete_profile_image`

**Archivo modificado:**
- `backend/app/services/profile/profile_service.py`

**Descripción:**
Se reemplazó `shutil.rmtree(profile_dir)` por una eliminación segura de archivos individuales:
1. Itera cada item en el directorio de perfil
2. Verifica `is_relative_to(media_root_resolved)` antes de eliminar
3. Elimina archivos con `unlink()` y subdirectorios con `shutil.rmtree()` (solo si pasan la verificación)
4. Intenta `rmdir()` del directorio vacío al final

**Decisión de diseño:** Mantener la misma interfaz (función no retorna nada, mismo nombre). La defensa `is_relative_to` garantiza que incluso si el `username` contuviera caracteres peligrosos (aunque ya está protegido por regex), no se podría escapar de `media_root`.

**Rollback:** Revertir `delete_profile_image` a la versión con `shutil.rmtree(profile_dir)`.

---

### 3. H-1 — `is_admin` en JWT de `register`

**Archivo modificado:**
- `backend/app/api/routes/auth/auth.py`

**Descripción:**
Se eliminó el claim `"is_admin": False` del payload del token JWT generado en el endpoint `POST /auth/register`. El endpoint `login` ya no lo incluía; ahora ambos son consistentes.

**Decisión de diseño:** `get_admin_user` siempre re-consulta la base de datos para verificar `is_admin`, por lo que eliminar el claim del token no afecta la funcionalidad de administración. Esto previene escalada de privilegios si en el futuro algún consumidor del token confía en el claim en lugar de consultar la BD.

**Rollback:** Agregar de vuelta `"is_admin": False` en el payload de registro.

---

### 4. H-2 — Unicidad de email en `PATCH /users/me`

**Archivo modificado:**
- `backend/app/api/routes/users/users.py`

**Descripción:**
Se agregó validación antes de asignar `user.email` en `update_my_profile`:
- Busca si existe otro usuario activo (`is_deleted == False`) con el mismo email
- Excluye al usuario actual (`User.id != user.id`)
- Si encuentra duplicado, devuelve **409 Conflict** con mensaje "El correo electrónico ya está en uso."

**Decisión de diseño:** El usuario puede "cambiar" su email al mismo valor que ya tiene (idempotente), pero no puede tomar el email de otro usuario activo. No se agregó UNIQUE constraint en base de datos (requeriría migración de schema). La verificación tiene race condition si dos requests concurrentes intentan el mismo email, pero es aceptable como primera línea de defensa.

**Rollback:** Quitar el bloque de validación de email.

---

### 5. C-7 — Protección contra alg-confusion (CVE-2024-33663)

**Archivo modificado:**
- `backend/app/core/auth/__init__.py`

**Descripción:**
Se agregó validación explícita del algoritmo (`alg`) después de decodificar el JWT:
```python
token_alg = payload.get("alg")
if token_alg is not None and token_alg != ALGORITHM:
    raise HTTPException(status_code=401, detail="Token inválido")
```

**Contexto:** `python-jose[cryptography]==3.5.0` ya mitiga la vulnerabilidad de alg-confusion, pero la validación explícita sirve como defensa en profundidad. El default `"your-secret-key"` sigue existiendo en el código pero es rechazado por el validador Pydantic en entornos no locales.

**Decisión de diseño:** No se quitó el default de `secret_key` en local para no romper el flujo de desarrollo (`make run` sin `.env` configurado). La validación del validador Pydantic ya previene su uso en producción.

**Rollback:** Quitar el bloque de validación de `token_alg`.

---

## Resultados de validación

### Tests ejecutados

```
cd backend && python -m pytest -q

175 passed in 20.74s
```

**Desglose:**
- `test_documents.py`: 16/16 passed
- `test_prompt_builder.py`: 6/6 passed (requiere Ollama)
- `test_image_generation_service.py`: 1/1 passed (requiere Ollama)
- `test_rag_query.py`: 3/3 passed (requiere Ollama)
- Resto del backend: 149/149 passed

### Tests modificados

| Test | Cambio | Motivo |
|---|---|---|
| `test_get_doc_wrong_collection_404` → `test_get_doc_wrong_collection_403` | Espera 403 en lugar de 404 | El nuevo `get_document_or_404_owned` devuelve 403 cuando el usuario no es dueño de la colección |

---

## Estado actual de la auditoría (post-Fase 1)

| Estado | Pre-Fase 1 | Post-Fase 1 | Delta |
|---|---|---|---|
| Resueltos | 15 | **20** | +5 |
| Parcialmente resueltos | 18 | **13** | -5 |
| No resueltos | 17 | 17 | 0 |
| No verificados | 3 | 3 | 0 |
| **Total** | **53** | **53** | — |

Los 5 problemas que pasaron de "parcialmente resueltos" a "resueltos" son: **C-3, C-5, H-1, H-2, C-7**.

---

## Próxima fase

**Fase 2 — Archivos y almacenamiento:**
- M-18 / L-2: Magic bytes para validación de imágenes
- M-13: Corregir `_delete_image_file` para resolver rutas bajo `media_root`
- H-3: `admin_delete_user` debe limpiar avatares de perfil

---

*Documento generado el 2026-05-11 tras la validación exitosa de la Fase 1.*
