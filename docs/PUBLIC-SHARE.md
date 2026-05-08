# Plan: Compartición granular de contenido público

## Contexto y problema

El modelo actual usa `Collection.is_public = True` para exponer una colección entera en el feed público. Esto tiene dos problemas:

1. **Riesgo de autoría:** expone documentos de origen, contenidos pendientes y todo el trabajo en progreso.
2. **Sin granularidad:** el autor no puede elegir qué mostrar — es todo o nada.

**Nuevo modelo:** la unidad de compartición es el ítem individual confirmado (texto o imagen), no la colección entera.

---

## Cambios de modelo de datos

### Eliminar

- `Collection.is_public` — obsoleto. Una colección aparece en el feed de forma implícita si tiene al menos un ítem compartido. Sin ítems compartidos = invisible en el feed.

### Añadir

| Modelo | Campo nuevo | Valor por defecto | Restricción |
|--------|-------------|-------------------|-------------|
| `EntityContent` | `is_shared: bool` | `False` | Solo activable si `status == confirmed` |
| `ImageRecord` | `is_shared: bool` | `False` | Ninguna (se puede compartir cualquier imagen existente) |

---

## Reglas de negocio

- `EntityContent.is_shared` solo puede ponerse a `True` si `status == confirmed`. El backend valida esto en el endpoint de share.
- Si un `EntityContent` confirmado es soft-deleted, `is_shared` se pone a `False` automáticamente.
- Mismo comportamiento para `ImageRecord`.
- El autor puede des-compartir en cualquier momento (el campo es un toggle).
- Los documentos de origen **nunca** son compartibles — no están en el modelo de sharing.

---

## Lógica del feed público

El endpoint actual hace `WHERE is_public = True` sobre `collections`. Cambia a:

```sql
SELECT DISTINCT c.*
FROM collections c
LEFT JOIN entity_contents ec
  ON ec.collection_id = c.id
  AND ec.is_shared = true
  AND ec.is_deleted = false
LEFT JOIN image_records ir
  ON ir.collection_id = c.id
  AND ir.is_shared = true
  AND ir.is_deleted = false
WHERE (ec.id IS NOT NULL OR ir.id IS NOT NULL)
  AND c.is_deleted = false
```

Una colección solo aparece en el feed si tiene al menos un texto o imagen compartida.

---

## Vista pública de una colección

Cuando un visitante hace click en "Explorar →" en el feed, ve:

- Solo las entidades que tienen al menos un `EntityContent.is_shared = True`
- Solo las imágenes con `ImageRecord.is_shared = True`
- Documentos fuente, contenidos pending, imágenes no seleccionadas → invisibles

El propietario, dentro de su vista privada, sigue viendo todo.

---

## Cambios por capa

### Backend

1. **Migración Alembic:**
   - Quitar columna `is_public` de `collections`
   - Añadir columna `is_shared: bool DEFAULT false` a `entity_contents`
   - Añadir columna `is_shared: bool DEFAULT false` a `image_records`

2. **Modelos** (`app/models/`):
   - `collections.py`: eliminar `is_public` de `Collection`, `UpdateCollectionRequest`, `CollectionResponse`
   - `entity_content.py`: añadir `is_shared: bool = False` a `EntityContent` y `EntityContentResponse`
   - `image_generation.py`: añadir `is_shared: bool = False` a `ImageRecord` e `ImageRecordResponse`

3. **Nuevos endpoints:**
   - `PATCH /collections/{id}/entities/{eid}/contents/{cid}/share` — toggle `is_shared` en `EntityContent` (valida que `status == confirmed`)
   - `PATCH /collections/{id}/image-generation/images/{image_id}/share` — toggle `is_shared` en `ImageRecord`

4. **Endpoint público de colecciones** (`GET /public/collections`):
   - Reemplazar filtro `is_public = True` por la query con JOIN descrita arriba

5. **Endpoint público de detalle** (`GET /public/collections/{id}`):
   - Devuelve solo entidades con al menos un `EntityContent.is_shared = True`
   - Filtra imágenes a `ImageRecord.is_shared = True`

6. **Servicios existentes:**
   - Al soft-delete de `EntityContent`: forzar `is_shared = False`
   - Al soft-delete de `ImageRecord`: forzar `is_shared = False`

### Frontend

1. **`EntityDetailPage`:** botón "Compartir / Dejar de compartir" junto a cada `EntityContent` con `status == confirmed`
2. **`GeneratePage`:** toggle "Compartir" junto a cada imagen en el resultado de generación
3. **`CollectionsPage` / settings de colección:** quitar cualquier toggle de `is_public`
4. **`PublicFeedPage`:** sin cambios de UI (el feed sigue mostrando tarjetas de colección)
5. **Vista pública de colección** (nueva page o ruta): muestra solo ítems `is_shared = True`

---

## Lo que NO cambia

- Flujo confirmar → descartar otros pendientes de la misma categoría
- Endpoint `/users/:username` de perfil público
- Vista privada del propietario (sigue viendo todo su contenido)
- Estructura de colecciones/entidades/documentos del propietario
- Namespace de Qdrant (sigue siendo `collection.id`)
