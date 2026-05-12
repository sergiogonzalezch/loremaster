# Plan de Implementacion — Resolver Parciales Restantes

**Fecha:** 2026-05-11
**Referencia:** `docs/AUDIT-RESULTS-11-05-26.md`
**Estrategia:** Atacar los parciales que pueden resolverse completamente con cambios minimos. Los que requieren reescritura arquitectonica se mantienen como parciales documentados.

---

## Analisis de parciales restantes (6)

| ID | Severidad | Resoluble completo | Justificacion |
|---|---|---|---|
| **H-3** | Alto | **Si** | Se puede agregar despublicacion de imagenes generadas en `admin_delete_user` |
| **L-10** | Bajo | **Si** | Se puede crear `AdminRoute` que verifique `is_admin` en frontend |
| **M-1** | Medio | No | Requiere reemplazo por libreria ML o servicio externo; solo documentable |
| **M-2** | Medio | No | Requiere reescribir content_guard sin regex; el limite de 100KB es la mejor mitigacion |
| **M-4** | Medio | No | ComfyUI es endpoint externo; `_sanitize_filename` es la mejor defensa sin reestructurar |
| **M-12** | Medio | No | Cambiar default romperia DX; log WARNING es la mejor mitigacion |

**Decision:** Atacar H-3 y L-10. Mantener M-1, M-2, M-4, M-12 como parciales documentados.

---

## Fase 9 — AdminRoute para L-10

**Objetivo:** Evitar que usuarios no-admin vean la UI de admin en el frontend.

### 9.1 Crear componente AdminRoute
**Archivo:** `frontend/src/components/AdminRoute.tsx`
**Descripcion:**
- Similar a `ProtectedRoute` pero verifica `user?.is_admin === true`
- Si no es admin: redirige a `/` o muestra 403
- Si es admin: renderiza `<Outlet />`

### 9.2 Aplicar en App.tsx
**Archivo:** `frontend/src/App.tsx`
**Descripcion:**
- Reemplazar `<Route path="/admin" element={<AdminPage />} />` dentro de `ProtectedRoute`
- O crear ruta anidada: `<Route element={<AdminRoute />}>` que envuelva `/admin`

### 9.3 Tests
**Archivo:** `frontend/src/test/AdminRoute.test.tsx` (nuevo)
- Verificar que redirige cuando `is_admin=false`
- Verificar que permite acceso cuando `is_admin=true`

**Validacion:** `121 passed` en frontend.

---

## Fase 10 — Despublicar contenido generado en admin_delete_user (H-3)

**Objetivo:** Cuando un admin elimina un usuario, despublicar las imagenes generadas por ese usuario.

### 10.1 Marcar imagenes como no compartidas
**Archivo:** `backend/app/api/routes/admin/admin.py`
**Descripcion:**
- En `admin_delete_user`, despues de eliminar avatares y antes de soft-delete del usuario:
- Query para encontrar todas las `ImageRecord` donde la entidad pertenece a una coleccion del usuario
- Marcar `is_shared=False` en esas imagenes
- Esto previene que aparezcan en el feed publico (si el feed filtra por `is_shared`)

**Nota:** Si el media_router no verifica `is_shared`, las imagenes siguen siendo accesibles por URL directa. Pero al menos se remueven del feed publico.

### 10.2 Consideraciones
- No eliminar archivos fisicos (solo despublicar)
- Soft-delete de las entidades/colecciones ya se hace en cascada
- El cambio es aditivo: no afecta el flujo existente

**Validacion:** `175 passed` en backend.

---

## Criterios de exito

- [ ] L-10 completamente resuelto (AdminRoute funcional)
- [ ] H-3 mejorado (imagenes despublicadas en admin delete)
- [ ] Tests pasan en ambos frontend y backend
- [ ] AUDIT-RESULTS actualizado con nuevos estados

---

*Plan generado el 2026-05-11.*
