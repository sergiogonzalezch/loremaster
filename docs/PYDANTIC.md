## Comparación DB ↔ Schemas: Entity + EntityContent

### 1. Campos de DB no expuestos en la API

| Campo | Modelo DB | En Response | Veredicto |
|---|---|---|---|
| `updated_by` | Entity, EntityContent | No | Correcto — campo de audit interno |
| `is_deleted` | ambos (SoftDeleteMixin) | No | Correcto — nunca debe exponerse |
| `deleted_at` | ambos (SoftDeleteMixin) | No | Correcto — nunca debe exponerse |

Los tres están correctamente ocultos. El filtrado ocurre por el mecanismo de `response_model` de FastAPI, no por diseño explícito del schema.

---

### 2. Bug real: `model_used` nunca se popula

`EntityContentResponse` declara `model_used: str | None = None` y `GeneratedText` tiene `model_used: str | None`. Pero `_to_response()` en `content_service.py:303` nunca lo mapea:

```python
# content_service.py — _to_response() — FALTA esta línea:
model_used=gt.model_used if gt else None,
```

**Consecuencia:** `model_used` siempre devuelve `None` en la API, aunque el campo esté guardado en `generated_texts`.

---

### 3. Discrepancia de tipos: `source_doc_ids`

| Nivel | Tipo declarado |
|---|---|
| `GeneratedText.source_doc_ids` (DB) | `list` (JSON column sin tipo) |
| `EntityContentResponse.source_doc_ids` | `list[str]` |

No hay ningún coercionador ni validador que garantice que el JSON almacenado contenga solo strings. Si la columna DB contiene enteros u otros tipos, Pydantic los aceptaría sin error en modo output (no valida al serializar).

---

### 4. Inconsistencia de tipos entre modelos DB hermanos

`EntityContent.category: ContentCategory` (enum tipado) vs `GeneratedText.category: str` (sin enum). Son modelos estrechamente relacionados que representan el mismo campo de dominio con tipos diferentes. No produce bugs en la respuesta API porque `_to_response()` usa `content.category` (el tipado), pero es una fuente de inconsistencia si se añaden queries directas sobre `GeneratedText`.

---

### 5. Semántica inesperada: `confirm_content` devuelve `EntityResponse`

```python
# content.py:147
@router.post(".../contents/{content_id}/confirm", response_model=EntityResponse)
def confirm_content(...):
    ...
    return entity   # ← devuelve la Entity padre, no el EntityContent
```

El endpoint vive bajo `/contents/{id}` pero devuelve `EntityResponse` (la entidad) en lugar de `EntityContentResponse`. `content_service.confirm_content()` retorna `EntityContent`, pero la ruta lo descarta y devuelve `entity`. El consumidor que llame a "confirmar un contenido" recibirá la entidad padre, no el contenido confirmado.

---

### 6. Validaciones faltantes en schemas de request

| Schema | Campo | DB constraint | En schema |
|---|---|---|---|
| `EntityRequest.type` | `type` | `index=True`, enum | Validado (enum) |
| `GenerateContentRequest.query` | `query` | `max_length=2000` | `min_length=10, max_length=2000` |
| `UpdateContentRequest.content` | `content` | `max_length=10000` | `min_length=1, max_length=10000` |

Todos los request schemas están bien. Los response schemas no tienen Field constraints, lo cual es correcto (son de salida, no de entrada).

---

### 7. Falta `model_config = ConfigDict(from_attributes=True)` en `EntityResponse`

Las rutas `create_entity`, `get_entity`, y `update_entity` devuelven instancias `Entity` (ORM) directamente. FastAPI resuelve esto internamente al serializar a `EntityResponse` usando `from_attributes=True` implícitamente, pero el schema no lo declara:

```python
class EntityResponse(BaseModel):
    # Falta: model_config = ConfigDict(from_attributes=True)
```

Funciona en producción gracias a FastAPI, pero cualquier uso directo de `EntityResponse.model_validate(entity)` fuera de FastAPI fallará.

---

### Resumen de prioridades

| # | Severidad | Problema | Archivo |
|---|---|---|---|
| 1 | **Bug** | `model_used` no se popula en `_to_response()` | `content_service.py:303` |
| 2 | Riesgo | `source_doc_ids`: `list` en DB vs `list[str]` en schema | `generated_text.py:57`, `entity_content.py:44` |
| 3 | Diseño | `confirm_content` devuelve `EntityResponse` en lugar de `EntityContentResponse` | `content.py:147` |
| 4 | Menor | `EntityResponse` sin `from_attributes=True` | `schemas/entity.py:43` |
| 5 | Menor | `GeneratedText.category` es `str` en vez de `ContentCategory` | `generated_text.py:53` |

¿Quieres que corrija el bug del `model_used` (#1) ahora?