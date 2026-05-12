# Plan de Acción — Problemas Parcialmente Resueltos

**Fecha:** 2026-05-11  
**Referencia:** `docs/AUDIT-RESULTS-11-05-26.md`  
**Problemas a cubrir:** 18 problemas parcialmente resueltos  

---

## Principios del plan

> **Lección aprendida (rate limit / safe image):** Correcciones de seguridad aplicadas de forma agresiva sobre endpoints activos pueden generar errores 500 en cascada, romper componentes de frontend que dependen de respuestas exactas, o bloquear flujos legítimos (como baseline evaluations).  
> **Regla de oro:** *Cambiar la autorización, no la interfaz.* Si un endpoint debe ser más restrictivo, la forma de rechazar la petición (404 vs 403, con o sin body) debe seguir siendo manejable por el código existente.

### Cómo leer este plan

| Campo | Descripción |
|---|---|
| **Impacto** | Qué tanto toca el código existente (bajo = refactor interno; alto = cambio de contrato API) |
| **Riesgo de ruptura** | Probabilidad de que el frontend o los tests fallen tras el cambio |
| **Qué puede romper** | Escenarios concretos de fallo |
| **Estrategia** | Enfoque para aplicar el cambio sin afectar estabilidad |
| **Pasos** | Orden recomendado de ejecución |
| **Rollback** | Cómo revertir rápido si hay problemas |

---

## 🔴 CRÍTICOS (5)

---

### C-3. IDOR cross-tenant en `get_document`, `retry_ingest`, `delete_document`

| | |
|---|---|
| **Impacto** | Medio |
| **Riesgo de ruptura** | Medio-Bajo |
| **Qué puede romper** | • Tests que esperan 404 al acceder a un doc de otro usuario (ahora será 403)  <br>• Si el frontend maneja 404 pero no 403, mostrará "No encontrado" en lugar de "Acceso denegado" (UX degradada, no crash) |
| **Estrategia** | **Defensa en profundidad sin cambiar la interfaz:** crear `get_document_or_404_owned` que devuelva **404** (no 403) cuando el usuario no es dueño, igual que hoy. Esto cierra el IDOR sin cambiar el contrato de la API. |

**Pasos:**

1. **Crear la nueva dependencia** en `app/core/database/dependencies.py`:
   ```python
   def get_document_or_404_owned(
       doc_id: str,
       collection: Collection = Depends(get_collection_or_404_owned),
       session: Session = Depends(get_session),
   ) -> Document:
       doc = get_active_by_id(session, Document, doc_id, collection.id)
       if not doc:
           raise HTTPException(status_code=404, detail="Documento no encontrado.")
       return doc
   ```
   > **Nota:** No lanzar 403. Un atacante no debe poder distinguir "no existe" de "no es tuyo".

2. **Cambiar los 3 endpoints** en `documents.py`:
   - `get_document`: `Depends(get_document_or_404)` → `Depends(get_document_or_404_owned)`
   - `retry_ingest`: idem
   - `delete_document`: idem

3. **Verificar compatibilidad:**
   - Ejecutar `pytest` (tests de documentos)
   - Si algún test espera 404 para doc de otro user, seguirá pasando (se mantiene 404)
   - Si algún test espera 403, ajustar a 404 (breaking test, no breaking app)

4. **Commit y deploy.**

**Rollback:** Revertir el cambio de los 3 `Depends(...)` a la versión anterior.

---

### C-5. Path traversal — `shutil.rmtree` en `delete_profile_image`

| | |
|---|---|
| **Impacto** | Bajo |
| **Riesgo de ruptura** | Bajo |
| **Qué puede romper** | Si el directorio de perfil contiene subdirectorios inesperados, iterar archivos uno por uno podría dejarlos huérfanos. Hoy `rmtree` los borra todos. |
| **Estrategia** | Eliminar archivos individualmente con la misma defensa `is_relative_to` que ya existe en `save_file`. Mantener el comportamiento observable (directorio vacío tras borrar). |

**Pasos:**

1. **Refactorizar** `delete_profile_image` en `profile_service.py`:
   ```python
   def delete_profile_image(session: Session, user: User) -> None:
       if not user.avatar_path:
           return
       profile_dir = _get_profile_dir(user.username)
       if profile_dir.exists() and profile_dir.is_dir():
           media_root_resolved = Path(settings.media_root).resolve()
           for item in profile_dir.iterdir():
               resolved = item.resolve()
               if resolved.is_file() and resolved.is_relative_to(media_root_resolved):
                   resolved.unlink()
               elif resolved.is_dir():
                   # Opción segura: no borrar subdirs recursivamente
                   # o usar shutil.rmtree solo tras verificar is_relative_to
                   if resolved.is_relative_to(media_root_resolved):
                       shutil.rmtree(resolved)
           # Intentar eliminar el directorio vacío
           try:
               profile_dir.rmdir()
           except OSError:
               pass
       user.avatar_path = None
       session.add(user)
       db_commit(session, f"delete_profile_image({user.username})")
   ```

2. **Tests:** Verificar que subir avatar → borrar avatar → subir nuevo avatar sigue funcionando (el caso más común).

**Rollback:** Revertir a la función original con `shutil.rmtree(profile_dir)`.

---

### C-6. Mount `/media` público sin auth / sin `Content-Disposition`

| | |
|---|---|
| **Impacto** | **ALTO** |
| **Riesgo de ruptura** | **ALTO** |
| **Qué puede romper** | • **TODAS las imágenes del frontend dejarán de cargar** si se agrega autenticación Bearer a `/media`, porque `<img src="...">` no envía headers de auth.  <br>• Las evaluaciones baseline que descargan imágenes fallarán con 401.  <br>• Los avatares públicos y el feed de imágenes compartidas se romperán visualmente. |
| **Estrategia** | **NO agregar auth a `/media` para contenido público.** En su lugar, aplicar capas de mitigación que no rompan la carga de recursos estáticos: lista blanca de Content-Type, `nosniff`, `Content-Disposition: inline` (no attachment, que rompería la visualización en `<img>`). Para contenido **privado** (imágenes generadas no compartidas), crear un endpoint separado con auth. |

**Pasos:**

1. **Lista blanca de Content-Type estricta** en `media.py`:
   ```python
   ALLOWED_MEDIA_TYPES = {
       ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
       ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif",
   }
   ```
   Si `suffix` no está en la lista, devolver **404** (no octet-stream), evitando que un `.html` subido se ejecute.

2. **Agregar `Content-Disposition: inline`** (NO `attachment`, que forzaría descarga y rompería `<img>`):
   ```python
   headers={
       "Cache-Control": "public, max-age=3600",
       "X-Content-Type-Options": "nosniff",
       "Content-Disposition": f'inline; filename="{file_path.name}"',
   }
   ```

3. **Endpoint privado opcional (fase 2):** Si se requiere protección para imágenes no compartidas, crear `/api/v1/media/private/{path}` con auth, y que el frontend use esa URL para imágenes privadas. Mantener `/media` solo para contenido público (avatars, feeds).

4. **Test de regresión:** Verificar que el feed público, perfiles de usuario, y avatar siguen cargando correctamente en el navegador.

> **⚠️ Basado en experiencia previa:** Un cambio de `Content-Disposition: attachment` en imágenes servidas por `<img>` las haría descargar en lugar de mostrarse, rompiendo el componente de imagen del frontend. Usar `inline` preserva el comportamiento actual.

**Rollback:** Revertir `media.py` a la versión anterior.

---

### C-7. JWT secret por defecto `"your-secret-key"` + alg-confusion

| | |
|---|---|
| **Impacto** | Medio |
| **Riesgo de ruptura** | Bajo (solo afecta arranque en entornos mal configurados) |
| **Qué puede romper** | • Si se quita el default por completo, entornos de desarrollo local que no tengan `.env` configurado fallarán al arrancar con `ValidationError`.  <br>• Tests que no mockeen `settings.secret_key` podrían fallar. |
| **Estrategia** | No quitar el default de local, pero reforzar validación y agregar protección contra alg-confusion en runtime. |

**Pasos:**

1. **Agregar chequeo de algoritmo en `verify_token`** (`core/auth/__init__.py`):
   ```python
   def verify_token(token: str) -> dict:
       try:
           payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
           if payload.get("sub") is None:
               raise HTTPException(status_code=401, detail="Token inválido")
           # Protección contra alg-confusion (CVE-2024-33663)
           if payload.get("alg") and payload["alg"] != ALGORITHM:
               raise HTTPException(status_code=401, detail="Token inválido")
           return payload
       except JWTError:
           raise HTTPException(status_code=401, detail="Token inválido")
   ```

2. **Fortalecer validador** (`config/__init__.py`):  
   Ya rechaza default en non-local y exige `>= 32` chars. Esto es suficiente. No tocar el default de local para no romper DX.

3. **Tests:** Agregar test con token que tenga `"alg": "none"` → debe retornar 401.

**Rollback:** Revertir `verify_token`.

---

### C-8. Postgres con credenciales hardcodeadas en `docker-compose.yml`

| | |
|---|---|
| **Impacto** | Medio |
| **Riesgo de ruptura** | Medio |
| **Qué puede romper** | • `docker-compose up` sin variables de entorno definidas fallará si eliminamos los defaults.  <br>• Nuevos desarrolladores no podrán levantar el stack fácilmente. |
| **Estrategia** | Mantener compatibilidad de desarrollo mediante archivo separado. En producción, forzar variables externas. |

**Pasos:**

1. **Crear `docker-compose.prod.yml`** con configuración estricta:
   ```yaml
   services:
     postgres:
       environment:
         POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}
       ports: []  # Sin exposición al host
   ```

2. **En `docker-compose.yml` (dev):** Agregar comentario explícito:
   ```yaml
   # NOTA: Estos valores son para desarrollo local únicamente.
   # En producción usar docker-compose.prod.yml con variables requeridas.
   ```
   Opcionalmente cambiar `5433:5432` → `127.0.0.1:5433:5432` para bind local únicamente.

3. **Documentar** en `backend/README.md` o `CLAUDE.md` que producción requiere `docker-compose -f docker-compose.prod.yml up`.

**Rollback:** Eliminar `docker-compose.prod.yml` y revertir cambios en `docker-compose.yml`.

---

## 🟠 ALTOS (4)

---

### H-1. `is_admin` viaja en el JWT del `register`

| | |
|---|---|
| **Impacto** | Bajo |
| **Riesgo de ruptura** | Bajo |
| **Qué puede romper** | Nada conocido; el frontend no consume `is_admin` del token para decisiones de UI (lo obtiene de `/users/me`). |
| **Estrategia** | Eliminar el claim del payload de registro, alineando con `login`. |

**Pasos:**

1. En `auth.py:175`, quitar `"is_admin": False,` del payload de `create_access_token`.
2. Ejecutar tests de auth/registro.

**Rollback:** Agregar de vuelta la línea.

---

### H-2. `PATCH /users/me` acepta email sin verificar unicidad

| | |
|---|---|
| **Impacto** | Medio |
| **Riesgo de ruptura** | Medio |
| **Qué puede romper** | • Si un usuario intenta "cambiar" su email al que ya tiene, y la validación es estricta, podría rechazarlo injustamente.  <br>• Race condition: dos usuarios cambiando al mismo email simultáneamente podrían ambos pasar la verificación (no hay UNIQUE constraint en BD aparentemente). |
| **Estrategia** | Verificar unicidad excluyendo al usuario actual. No agregar UNIQUE constraint ahora (migración de BD fuera de scope), pero validar en Python. |

**Pasos:**

1. En `users.py` (`update_my_profile`), antes de asignar `user.email`:
   ```python
   if request.email is not None:
       existing = session.exec(
           select(User).where(
               User.email == request.email,
               User.is_deleted == False,
               User.id != user.id,
           )
       ).first()
       if existing:
           raise HTTPException(status_code=409, detail="El correo electrónico ya está en uso.")
       user.email = request.email
   ```

2. **Test de regresión:** Verificar que un usuario puede cambiar su email a uno nuevo, pero no a uno usado por otro usuario. Verificar que puede "cambiar" al mismo email que ya tiene (idempotente).

**Rollback:** Revertir el bloque de validación.

---

### H-3. `admin_delete_user` no elimina avatares de perfil / archivos físicos

| | |
|---|---|
| **Impacto** | Medio |
| **Riesgo de ruptura** | Bajo |
| **Qué puede romper** | Si el avatar path es inválido o ya fue borrado, el intento de borrarlo no debe lanzar excepción que aborte la transacción de eliminación del usuario. |
| **Estrategia** | Llamar a `delete_profile_image` (ya existente) dentro de `admin_delete_user`, envuelto en try/except para que un fallo de disco no impida el soft-delete del usuario. |

**Pasos:**

1. En `admin.py` (`admin_delete_user`), antes de `user.is_deleted = True`:
   ```python
   try:
       from app.services.profile.profile_service import delete_profile_image
       delete_profile_image(session, user)
   except Exception:
       logger.warning("Failed to delete avatar for user %s during admin deletion", user_id)
   ```

2. **Nota:** `delete_profile_image` debe ser seguro tras aplicar C-5.

**Rollback:** Quitar el bloque try/except.

---

### H-8. Rate limiting — ya existe pero baseline_evals marcó 500

| | |
|---|---|
| **Impacto** | Medio |
| **Riesgo de ruptura** | **ALTO** (basado en experiencia previa) |
| **Qué puede romper** | • Baseline evaluations que hacen múltiples requests seguidos → 429 en lugar de resultados.  <br>• Tests de integración que ejecutan POSTs rápidos.  <br>• Webhooks o callbacks que llegan en ráfaga. |
| **Estrategia** | **NO tocar el middleware existente** que ya protege operaciones mutantes. En su lugar, identificar por qué baseline_evals marcó 500: probablemente el rate limiter anterior (o una versión previa) lanzaba excepciones no manejadas o usaba una implementación distinta.  
> **La implementación actual ya es correcta** (omite test, omite GET, devuelve 429 con JSON). El problema histórico fue probablemente en una iteración anterior.  
> **Acción:** Documentar que en producción con múltiples workers se necesita Redis como backend de rate limiting. No modificar el middleware actual para no repetir el incidente. |

**Pasos:**

1. **No modificar código** del rate limiter actual.
2. **Agregar comentario/documentación** en `rate_limit.py` y `CLAUDE.md`:
   ```
   # NOTA: Este rate limiter es en memoria (dict). Para producción con múltiples
   # workers, migrar a Redis backend para consistencia entre instancias.
   ```
3. Si se desea aumentar cobertura, hacerlo solo en endpoints específicos con decoradores, no en middleware global.

**Rollback:** No aplica (sin cambio de código).

---

## 🟡 MEDIOS (5)

---

### M-4. ComfyUI `download_image` sin sanitizar

| | |
|---|---|
| **Impacto** | Bajo |
| **Riesgo de ruptura** | Bajo |
| **Qué puede romper** | `_sanitize_filename` ya filtra caracteres peligrosos. Cambiarlo a algo más agresivo podría truncar nombres de archivo legítimos de ComfyUI. |
| **Estrategia** | La sanitización actual es suficiente para mitigar path traversal. No requiere acción inmediata. |

**Pasos:**
1. Marcar como aceptable. Sin cambios de código.

---

### M-8. AWS credenciales de test en `.env.example`

| | |
|---|---|
| **Impacto** | Bajo |
| **Riesgo de ruptura** | Ninguno |
| **Qué puede romper** | Nada; `.env.example` no es código ejecutado. |
| **Estrategia** | Agregar comentarios de advertencia en el archivo. |

**Pasos:**

1. En `.env.example`, cambiar:
   ```
   # ⚠️  NO usar estos valores en producción. Generar credenciales reales o dejar comentado.
   # AWS_ACCESS_KEY_ID=your-access-key
   # AWS_SECRET_ACCESS_KEY=your-secret-key
   ```
2. Agregar nota similar junto a `SECRET_KEY`.

---

### M-10. Logging sin redacción de PII

| | |
|---|---|
| **Impacto** | Medio |
| **Riesgo de ruptura** | Medio |
| **Qué puede romper** | Si se redactan emails/usernames en logs, el debugging de problemas de auth se vuelve más difícil. |
| **Estrategia** | Aplicar redacción **solo en entornos no locales**. En local mantener logs verbosos para debugging. |

**Pasos:**

1. Crear helper `app/core/logging.py`:
   ```python
   def redact_pii(text: str) -> str:
       if settings.environment == "local":
           return text
       # Regex simples para emails
       import re
       return re.sub(r"[\w.-]+@[\w.-]+\.\w+", "[REDACTED_EMAIL]", text)
   ```
2. Aplicar en `documents_service.py` y otros servicios donde se loguean filenames/inputs.

**Rollback:** Quitar las llamadas a `redact_pii`.

---

### M-13. Cleanup roto — `_delete_image_file` no resuelve bajo `media_root`

| | |
|---|---|
| **Impacto** | Medio |
| **Riesgo de ruptura** | Medio |
| **Qué puede romper** | • Si `storage_path` ya es una ruta absoluta, concatenar con `media_root` creará una ruta inválida.  <br>• Si se resuelve incorrectamente, podría intentar borrar archivos fuera de `media_root`. |
| **Estrategia** | Usar el mismo patrón que `save_file`: resolver bajo `media_root` con `is_relative_to`. |

**Pasos:**

1. Corregir `_delete_image_file` en `deletion_service.py`:
   ```python
   def _delete_image_file(storage_path: str | None) -> None:
       if not storage_path:
           return
       media_root_resolved = Path(settings.media_root).resolve()
       # storage_path es relativa (ej: "users/foo/img/...")
       file_path = (media_root_resolved / storage_path).resolve()
       if not file_path.is_relative_to(media_root_resolved):
           logger.warning("Attempted to delete file outside media_root: %s", storage_path)
           return
       if file_path.exists() and file_path.is_file():
           file_path.unlink()
           logger.info("Deleted file: %s", storage_path)
   ```

2. **Test:** Crear un archivo en media_root, invocar `_delete_image_file` con su ruta relativa, verificar que se borra. Probar con path traversal → no debe borrar nada fuera de media_root.

**Rollback:** Revertir `_delete_image_file`.

---

### M-18. Validación cliente-only de avatar — falta magic bytes para imágenes

| | |
|---|---|
| **Impacto** | Medio |
| **Riesgo de ruptura** | Medio |
| **Qué puede romper** | • Si se rechaza una imagen válida con headers inusuales, el usuario no podrá subir su avatar.  <br>• Si se usa una librería pesada (libmagic), aumenta dependencias. |
| **Estrategia** | Reutilizar la validación que ya existe: `Image.open()` en `_strip_exif` ya valida que el archivo sea una imagen válida. Convertir ese paso en una validación explícita con manejo de error claro. |

**Pasos:**

1. En `FileValidator.validate_image`, después de leer content:
   ```python
   # Validación de magic bytes / integridad de imagen
   try:
       Image.open(BytesIO(content)).verify()
   except Exception:
       raise ValueError("El archivo no es una imagen válida")
   ```
   > `verify()` es más rápido que `load()` y confirma que los headers de imagen son correctos.

2. **Test de regresión:** Subir imágenes válidas (jpg, png) → éxito. Subir un `.txt` renombrado a `.jpg` → rechazo con 400.

**Rollback:** Quitar el bloque `Image.open(...).verify()`.

---

## 🟢 BAJOS (4)

---

### L-1. `admin_delete_collection` sin audit log estructurado

| | |
|---|---|
| **Impacto** | Bajo |
| **Riesgo de ruptura** | Ninguno |
| **Qué puede romper** | Nada; solo cambia el formato del log. |
| **Estrategia** | Mejorar el log existente con más contexto estructurado (JSON-like). |

**Pasos:**
1. En `admin.py:84`:
   ```python
   logger.info(
       "audit action=admin_delete_collection collection_id=%s owner_id=%s admin_id=%s",
       collection_id, owner_id, current_admin["sub"]
   )
   ```

---

### L-2. `validate_image` sin cross-validación MIME ↔ extensión ↔ magic bytes

| | |
|---|---|
| **Impacto** | Bajo (ya se resuelve parcialmente en M-18) |
| **Riesgo de ruptura** | Ver M-18 |
| **Estrategia** | Resolver junto con M-18. Con `Image.verify()` y validación de extensión/MIME existente, queda cubierto. |

**Pasos:**
1. Aplicar M-18. Marcar L-2 como resuelto tras eso.

---

### L-8. `make_admin.py` sin audit log

| | |
|---|---|
| **Impacto** | Bajo |
| **Riesgo de ruptura** | Ninguno |
| **Qué puede romper** | Nada. |
| **Estrategia** | Agregar log estructurado al script. |

**Pasos:**
1. En `make_admin.py:53`:
   ```python
   logger.info("audit action=make_admin username=%s promoted_by=%s", username, os.environ.get("USER", "unknown"))
   ```

---

### L-12. Logger global a INFO sin estructura/redacción

| | |
|---|---|
| **Impacto** | Medio |
| **Riesgo de ruptura** | Medio |
| **Qué puede romper** | Si se cambia el formato de logging global, herramientas de parsing de logs (si las hay) podrían dejar de funcionar. |
| **Estrategia** | Aplicar en conjunto con M-10. No cambiar el formato global ahora; solo redactar PII en los mensajes que lo contienen. |

**Pasos:**
1. Aplicar M-10.
2. Marcar L-12 como resuelto tras M-10.

---

## Orden de ejecución recomendado

Para minimizar riesgos y dependencias entre cambios:

### Fase 1 — Seguridad estructural sin cambio de interfaz (bajo riesgo)
1. **C-3** (IDOR documentos) — solo cambia dependencias internas
2. **C-5** (shutil.rmtree) — refactor interno
3. **H-1** (is_admin en JWT) — un línea
4. **H-2** (email unicidad) — validación extra
5. **C-7** (alg-confusion) — validación extra en auth

### Fase 2 — Archivos y almacenamiento (medio riesgo)
6. **M-18 / L-2** (magic bytes imágenes) — validación extra
7. **M-13** (cleanup archivos) — corregir path resolution
8. **H-3** (admin delete limpia avatares) — depende de C-5

### Fase 3 — Media y configuración (riesgo variable)
9. **C-6** (media router) — lista blanca + headers, SIN auth para público
10. **C-8** (docker-compose prod) — archivo separado
11. **M-8** (.env.example) — solo documentación

### Fase 4 — Observabilidad (bajo riesgo)
12. **M-10 / L-12** (redacción PII)
13. **L-1 / L-8** (audit logs)
14. **M-4** (ya resuelto, marcar)

> **Regla de oro:** Después de cada fase, ejecutar `pytest` + `npm run test` + verificación visual del frontend (avatar, feed, imágenes).

---

## Checklist de validación post-cambio

- [ ] `pytest backend/` pasa al 100%
- [ ] `npm run test` en frontend pasa
- [ ] Login / registro funcionan
- [ ] Subir avatar → borrar avatar → subir nuevo avatar funciona
- [ ] Feed público carga imágenes correctamente
- [ ] Document upload / list / get / delete funcionan para el dueño
- [ ] Document get para otro usuario retorna 404 (no 500)
- [ ] Admin puede eliminar usuario y sus colecciones sin errores
- [ ] No hay errores 500 en logs durante baseline evaluation (si aplica)

---

*Generado el 2026-05-11 como guía de implementación para los 18 problemas parcialmente resueltos de la auditoría de seguridad.*
