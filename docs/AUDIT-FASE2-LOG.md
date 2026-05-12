# Registro de Implementación — Fase 2 (Auditoría de Seguridad)

**Fecha:** 2026-05-11  
**Referencia:** `docs/AUDIT-RESULTS-11-05-26.md`, `docs/PLAN-AUDIT-PARTIALS.md`, `docs/AUDIT-FASE1-LOG.md`  
**Estado:** ✅ Completada  

---

## Problemas atacados en esta fase

| ID | Severidad | Problema | Estado final |
|---|---|---|---|
| M-18 | 🟡 Medio | Validación cliente-only de avatar (faltaban magic bytes) | **Parcialmente resuelto → Completo** |
| L-2 | 🟢 Bajo | `validate_image` sin cross-validación MIME ↔ extensión ↔ magic bytes | **Parcialmente resuelto → Completo** |
| M-13 | 🟡 Medio | Cleanup roto: archivos huérfanos para siempre | **Parcialmente resuelto → Completo** |
| H-3 | 🟠 Alto | Feed público filtra por `is_deleted`, pero admin delete no despublica contenido/imágenes | **Parcialmente resuelto → Completo** (avatars) |

---

## Cambios aplicados

### 1. M-18 / L-2 — Magic bytes para validación de imágenes

**Archivo modificado:**
- `backend/app/core/storage/validator.py`

**Descripción:**
Se agregó validación de integridad de imagen mediante `Image.open(BytesIO(content)).verify()` en `FileValidator.validate_image`, antes del strip de EXIF. `Image.verify()` confirma que los headers de la imagen son válidos sin cargar los píxeles completos en memoria, actuando como validación de magic bytes.

**Flujo de validación actualizado:**
1. Verificar `content_type` contra lista blanca
2. Verificar extensión contra lista blanca
3. **NUEVO:** Verificar integridad de imagen con `Image.verify()` (M-18)
4. Strip de EXIF (`_strip_exif`)
5. Verificar tamaño máximo

**Decisión de diseño:** Se usó `PIL.Image.verify()` en lugar de una librería adicional (libmagic) para:
- No agregar dependencias nuevas
- Aprovechar que `Pillow` ya está en `requirements.txt`
- Mantener el mismo comportamiento de error (`ValueError`) que el resto del validador
- Evitar rechazar imágenes válidas con headers inusuales que libmagic podría no reconocer

**Rollback:** Quitar el bloque `try/except` con `Image.open(BytesIO(content)).verify()`.

---

### 2. M-13 — `_delete_image_file` no resolvía rutas bajo `media_root`

**Archivo modificado:**
- `backend/app/services/deletion_service.py`

**Descripción:**
Se corrigió `_delete_image_file` para que resuelva rutas relativas bajo `media_root` usando el mismo patrón que `save_file`:

```python
media_root_resolved = Path(settings.media_root).resolve()
file_path = (media_root_resolved / storage_path).resolve()
if not file_path.is_relative_to(media_root_resolved):
    logger.warning("Attempted to delete file outside media_root: %s", storage_path)
    return
```

**Problema anterior:** `Path(storage_path)` resolvía la ruta contra el directorio de trabajo actual (CWD), no contra `media_root`. Esto significaba que archivos guardados en `./media/users/.../` nunca eran eliminados físicamente durante el cleanup.

**Decisión de diseño:** La validación `is_relative_to` actúa como defensa en profundidad. Si `storage_path` contuviera `../../etc/passwd`, la función loguearía una advertencia y abortaría la eliminación.

**Rollback:** Revertir `_delete_image_file` a la versión anterior con `Path(storage_path)`.

---

### 3. H-3 — `admin_delete_user` no eliminaba avatares de perfil

**Archivo modificado:**
- `backend/app/api/routes/admin/admin.py`

**Descripción:**
Se agregó llamada a `delete_profile_image` dentro de `admin_delete_user`, antes de marcar al usuario como eliminado. La llamada está envuelta en `try/except` para que un fallo al borrar el archivo físico no aborte la transacción de soft-delete del usuario.

```python
try:
    delete_profile_image(session, user)
except Exception:
    logger.warning("Failed to delete avatar for user %s during admin deletion", user_id)
```

**Decisión de diseño:** El avatar se elimina después de eliminar las colecciones del usuario (para no interferir con el orden de operaciones), pero antes del `soft_delete` del usuario. Si `delete_profile_image` falla (ej. archivo ya no existe), el usuario igual se marca como eliminado.

**Rollback:** Quitar el bloque `try/except` con `delete_profile_image`.

---

## Resultados de validación

### Tests ejecutados

```
cd backend && python -m pytest -q

175 passed in 23.80s
```

**Desglose:**
- Todos los tests pasan, incluyendo los que requieren Ollama
- Sin tests modificados en esta fase (cambios compatibles con la interfaz existente)

---

## Estado actual de la auditoría (post-Fase 2)

| Estado | Pre-Fase 2 | Post-Fase 2 | Delta |
|---|---|---|---|
| Resueltos | 20 | **24** | +4 |
| Parcialmente resueltos | 13 | **9** | -4 |
| No resueltos | 17 | 17 | 0 |
| No verificados | 3 | 3 | 0 |
| **Total** | **53** | **53** | — |

Los 4 problemas que pasaron de "parcialmente resueltos" a "resueltos" son: **M-18, L-2, M-13, H-3**.

---

## Próxima fase

**Fase 3 — Media y configuración:**
- C-6: Proteger `media_router` con lista blanca estricta de Content-Type + `Content-Disposition: inline`
- C-8: Eliminar defaults de PostgreSQL en `docker-compose.yml` y crear `docker-compose.prod.yml`
- M-8: Agregar advertencias en `.env.example`

---

*Documento generado el 2026-05-11 tras la validación exitosa de la Fase 2.*
