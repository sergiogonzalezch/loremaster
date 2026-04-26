# Estandarización de Filtros, Búsqueda y Ordenamiento

## Observación

Los parámetros de paginación, filtro y orden se declaran de forma independiente en cada route, sin ninguna abstracción compartida.

**Archivos afectados y repeticiones detectadas:**

| Archivo | Ocurrencias |
|---|---|
| `app/api/routes/collections.py` | 4 |
| `app/api/routes/entities.py` | 4 |
| `app/api/routes/documents.py` | 4 |
| `app/api/routes/entity_content.py` | 3 |

**Total:** 15 declaraciones `Query(...)` duplicadas.

**Ejemplo del patrón repetido** (presente en casi todos los list endpoints):

```python
page: int = Query(default=1, ge=1),
page_size: int = Query(default=20, ge=1, le=100),
name: Optional[str] = Query(default=None),
created_after: Optional[datetime] = Query(default=None),
created_before: Optional[datetime] = Query(default=None),
order: Literal["asc", "desc"] = Query(default="desc"),
```

---

## Plan de Acción

### Opción propuesta: clases de parámetros con `Annotated` + `Depends`

FastAPI permite agrupar query params en una clase y exponerlos como dependencia:

```python
# app/api/deps/query_params.py

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Literal, Optional
from fastapi import Depends, Query

@dataclass
class PaginationParams:
    page: int = Query(default=1, ge=1)
    page_size: int = Query(default=20, ge=1, le=100)
    order: Literal["asc", "desc"] = Query(default="desc")

@dataclass
class DateRangeParams:
    created_after: Optional[datetime] = Query(default=None)
    created_before: Optional[datetime] = Query(default=None)
```

Los routes los consumen así:

```python
@router.get("/")
def list_collections(
    pagination: Annotated[PaginationParams, Depends()],
    dates: Annotated[DateRangeParams, Depends()],
    name: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
):
    ...
```

### Alcance del cambio

1. Crear `app/api/deps/query_params.py` con `PaginationParams` y `DateRangeParams`.
2. Refactorizar los 4 routes afectados para usar las nuevas dependencias.
3. Verificar que los servicios reciban los mismos tipos que antes (sin cambios en la capa de servicio).
4. Ejecutar la suite de tests tras el refactor.

### Criterio de aceptación

- Cero repeticiones de `page.*Query` / `order.*Query` / `created_after.*Query` en los routes.
- Todos los tests existentes pasan sin modificación.
- La documentación OpenAPI (`/docs`) sigue mostrando los parámetros correctamente.