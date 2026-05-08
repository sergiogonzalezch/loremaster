# REFACTOR-USERS — Plan de refactor de users.py

Fecha: 2026-05-08  
Branch: `feature/user-profile`  
Estado: **Pendiente de implementación**

---

## Problemas identificados

### DRY — 4 violaciones

**1. Fetch del usuario propio repetido 5 veces**

```python
# Líneas 207-209, 219-221, 241-243, 253-255, 269-271 — idénticas
user = session.get(User, current_user["sub"])
if not user or user.is_deleted:
    raise HTTPException(status_code=404, detail="Usuario no encontrado.")
```

Mismo bloque en `get_my_profile`, `update_my_profile`, `get_my_avatar`, `upload_my_avatar` y `delete_my_avatar`.

**2. `_CONTENT_CONDITIONS` y `_IMAGE_CONDITIONS` no se reusan en `get_public_profile`**

Las constantes se definieron (líneas 95-111) pero `get_public_profile` (líneas 291-317) las duplica inline añadiendo solo `Collection.owner_id == user.id`. Si se añade una condición a las constantes no se refleja en el perfil público.

**3. Patrón count+paginación duplicado**

`get_public_feed` y `get_public_images` repiten el mismo bloque:
```python
total = session.exec(select(func.count()).select_from(base.subquery())).one()
skip  = (pagination.page - 1) * pagination.page_size
rows  = session.exec(query.offset(skip).limit(pagination.page_size)).all()
return PaginatedResponse.build(...)
```

### SRP — 3 violaciones

**1. El archivo tiene 4 responsabilidades distintas**
- Gestión del perfil propio (`/me`, `/me/avatar`)
- Feed público global (`/public/feed`)
- Imágenes públicas globales (`/public/images`)
- Perfil público de cualquier usuario (`/{username}/profile`)

**2. `public_router` vive dentro de `users.py`**

Rutas sin autenticación de contenido global mezcladas con rutas autenticadas de gestión de perfil en el mismo módulo.

**3. 6 modelos Pydantic definidos en el route**

`AvatarResponse`, `SharedContentSummary`, `SharedImageSummary`, `PublicProfileResponse`, `PublicFeedItem` y `PublicImageItem` están en la capa HTTP en lugar de en `models/`.

### Capa — 2 violaciones

**1. Queries SQL complejas directamente en handlers**

`get_public_feed`, `get_public_images` y `get_public_profile` hacen multi-join queries de 4-5 tablas sin capa de servicio.

**2. Lógica de negocio inline**

- `ec.content[:300]` — regla de negocio incrustada en un list comprehension
- `get_avatar_info(user)["avatar_url"]` — acceso por clave string en lugar de tipado
- `skip = (pagination.page - 1) * pagination.page_size` repetido en cada handler

---

## Estructura objetivo

```
models/users.py              ← + 6 modelos Pydantic (hoy en el route)
core/deps.py                 ← + get_current_db_user (elimina el bloque 5×)
services/public_service.py   ← NUEVO: las 3 queries complejas + condiciones compartidas
api/routes/public.py         ← NUEVO: public_router con handlers finos
api/routes/users.py          ← solo perfil propio, handlers de 3-5 líneas
app/main.py                  ← cambiar import de public_router
```

---

## Pasos de implementación

### Paso 1 — Mover los 6 modelos a `models/users.py`

Los 6 tipos de respuesta que hoy viven en el route pasan al modelo. Solo reubicación, sin nueva lógica:

```
AvatarResponse
SharedContentSummary
SharedImageSummary
PublicProfileResponse
PublicFeedItem
PublicImageItem
```

---

### Paso 2 — Añadir `get_current_db_user` a `core/deps.py`

Sigue el patrón ya establecido en `deps.py` (`get_collection_or_404_owned`, etc.):

```python
def get_current_db_user(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> User:
    user = session.get(User, current_user["sub"])
    if not user or user.is_deleted:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return user
```

Reemplaza las 5 copias del mismo bloque en `users.py`. No hay cambios en `conftest.py` porque el fixture ya crea el `test_user` con `id="test-user-id"` y la cadena de dependencias (`get_current_user` → stub → `get_current_db_user` → DB lookup) funciona igual.

---

### Paso 3 — Crear `services/public_service.py`

Las constantes `_CONTENT_CONDITIONS` e `_IMAGE_CONDITIONS` se mueven aquí. `get_user_public_profile` las reutiliza añadiendo el filtro de owner (DRY fix):

```python
_CONTENT_CONDITIONS = [
    EntityContent.is_shared == True,
    EntityContent.is_deleted == False,
    EntityContent.status == ContentStatus.confirmed,
    Entity.is_deleted == False,
    Collection.is_deleted == False,
    User.is_deleted == False,
]

_IMAGE_CONDITIONS = [
    ImageRecord.is_shared == True,
    ImageRecord.is_deleted == False,
    ImageGeneration.is_deleted == False,
    Entity.is_deleted == False,
    Collection.is_deleted == False,
    User.is_deleted == False,
]

def get_public_feed_page(session, pagination) -> tuple[list[PublicFeedItem], int]:
    ...

def get_public_images_page(session, pagination) -> tuple[list[PublicImageItem], int]:
    ...

def get_user_public_profile(session, username) -> PublicProfileResponse:
    # usa _CONTENT_CONDITIONS + _IMAGE_CONDITIONS con filtro owner_id adicional
    ...
```

Una sola fuente de verdad para "qué es contenido público visible".

---

### Paso 4 — Crear `api/routes/public.py`

`public_router` se mueve aquí. Handlers finos que solo delegan al servicio:

```python
public_router = APIRouter(prefix="/public", tags=["public"])

@public_router.get("/feed", response_model=PaginatedResponse[PublicFeedItem])
def get_public_feed(pagination, session):
    items, total = get_public_feed_page(session, pagination)
    return PaginatedResponse.build(items, total, pagination.page, pagination.page_size)

@public_router.get("/images", response_model=PaginatedResponse[PublicImageItem])
def get_public_images(pagination, session):
    items, total = get_public_images_page(session, pagination)
    return PaginatedResponse.build(items, total, pagination.page, pagination.page_size)
```

---

### Paso 5 — Limpiar `api/routes/users.py`

Queda solo la gestión del perfil propio. Los handlers usan `get_current_db_user`:

```python
@router.get("/me", ...)
def get_my_profile(user: User = Depends(get_current_db_user)):
    return user

@router.patch("/me", ...)
def update_my_profile(request, user: User = Depends(get_current_db_user), session):
    # aplicar campos, commit, return

@router.get("/{username}/profile", ...)
def get_public_profile(username, session):
    return get_user_public_profile(session, username)
```

El archivo pasa de ~353 líneas a ~80.

---

### Paso 6 — Actualizar `main.py`

```python
# Antes
from app.api.routes import users
app.include_router(users.public_router, prefix="/api/v1")

# Después
from app.api.routes import public
app.include_router(public.public_router, prefix="/api/v1")
```

---

## Qué NO cambia

| Elemento | Por qué |
|---|---|
| `services/user_image.py` | Ya está bien estructurado |
| `core/auth_deps.py` | Sin tocar |
| URLs de todos los endpoints | Ninguna cambia → frontend sin cambios |
| Tests | Sin cambios: `conftest.py` ya crea `test_user` con el id correcto para que `get_current_db_user` funcione a través de la cadena de dependencias |

---

## Orden de ejecución

```
1. models/users.py           → añadir modelos
2. core/deps.py              → añadir get_current_db_user
3. services/public_service.py → nuevo (depende de los modelos)
4. api/routes/public.py      → nuevo (depende del servicio)
5. api/routes/users.py       → limpiar (depende de todo lo anterior)
6. app/main.py               → 1 línea de import
7. pytest                    → verificar 175 tests verdes
```

---

## Archivos a modificar/crear

| Archivo | Acción | Cambio principal |
|---------|--------|-----------------|
| `backend/app/models/users.py` | Modificar | + 6 modelos Pydantic |
| `backend/app/core/deps.py` | Modificar | + `get_current_db_user` |
| `backend/app/services/public_service.py` | Crear | Query logic + condiciones compartidas |
| `backend/app/api/routes/public.py` | Crear | `public_router` con handlers finos |
| `backend/app/api/routes/users.py` | Modificar | Eliminar todo excepto perfil propio |
| `backend/app/main.py` | Modificar | Cambiar import de `public_router` |
