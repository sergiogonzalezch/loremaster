# Sistema de Usuarios, Perfiles y Multi-Tenancy

## Estado actual y contexto

El backend ya tiene JWT auth funcional (`/auth/login`, `/auth/register`) y el `get_current_user` dependency resuelve el usuario. El problema es que ese usuario se descarta en todas las rutas (`_: dict = Depends(get_current_user)`). Las colecciones son globales: cualquier usuario autenticado ve y puede modificar cualquier colección.

El plan anterior tenía cuatro problemas críticos:
1. Un cambio monolítico sin fases independientes entregables.
2. Roles/permisos granulares (YAGNI) — el proyecto no tiene esa necesidad hoy.
3. Sin estrategia de migración para datos existentes (collections sin owner).
4. Sin mención del constraint único `(name, owner_id)` ni del frontend.

Este documento reemplaza ese plan con cuatro fases ordenadas por impacto y dependencia, cada una independientemente desplegable y testeable.

---

## Fase 1 — Multi-Tenancy base (DB + service layer + auth wiring)

**Complejidad:** M  
**Prerequisito:** ninguno  
**Resultado:** las colecciones pertenecen a un usuario; el acceso está aislado por owner.

### Por qué esta fase primero

Sin `owner_id` en `Collection`, toda mejora de perfil o visibilidad pública carece de significado. Esta es la base mínima que hace el sistema multi-tenant. Es también el cambio más riesgoso porque toca el modelo de datos y la capa de servicio, por eso se hace aislado antes de añadir más features.

### 1.1 Modelo Collection — `backend/app/models/collections.py`

Agregar `owner_id` como FK nullable hacia `users.id`. La razón de nullable: al ejecutar la migración puede haber filas existentes sin owner, y un FK NOT NULL rompería la migración. La estrategia de datos explica cómo cerrar esto.

```python
owner_id: Optional[str] = SQLField(
    sa_column=Column(
        String(36),
        ForeignKey("users.id"),
        nullable=True,   # nullable durante la migración; ver 1.2
        index=True,
    )
)
```

Cambiar el constraint único en `__table_args__`:

```python
__table_args__ = (
    UniqueConstraint("name", "owner_id", name="uq_collection_name_owner"),
)
```

El índice único global `ix_collections_name` debe eliminarse. Lo gestiona la migración Alembic.

Agregar `owner_id` al `CollectionResponse`:

```python
class CollectionResponse(BaseModel):
    ...
    owner_id: Optional[str] = None
```

### 1.2 Migración Alembic — nueva revisión post-checkpoint

Crear `backend/alembic/versions/<hash>_add_owner_id_to_collections.py`.

Estrategia en tres pasos dentro del mismo `upgrade()`:

1. Añadir columna `owner_id` nullable, drop del índice único global en `name`, crear índice en `owner_id`.
2. Back-fill: asignar las colecciones huérfanas al primer usuario registrado. Si no hay usuarios, dejar `NULL` (colecciones legacy serán invisibles hasta que se asigne owner). Esta decisión es consciente: es un entorno de desarrollo; en producción se haría una asignación manual o un script interactivo.
3. Crear el `UniqueConstraint("name", "owner_id")`.

La columna se deja nullable indefinidamente para no romper el seed de tests. El servicio maneja `owner_id=None` como "colección sin dueño" (no visible en la lista normal).

```python
def upgrade():
    with op.batch_alter_table("collections") as batch_op:
        batch_op.add_column(sa.Column("owner_id", sa.String(36), nullable=True))
        batch_op.drop_index("ix_collections_name")
        batch_op.create_index("ix_collections_owner_id", ["owner_id"])
        batch_op.create_unique_constraint(
            "uq_collection_name_owner", ["name", "owner_id"]
        )

def downgrade():
    with op.batch_alter_table("collections") as batch_op:
        batch_op.drop_constraint("uq_collection_name_owner", type_="unique")
        batch_op.drop_index("ix_collections_owner_id")
        batch_op.create_index("ix_collections_name", ["name"], unique=True)
        batch_op.drop_column("owner_id")
```

### 1.3 Capa de servicio — `backend/app/services/collection_service.py`

Todas las funciones reciben `owner_id: str` como parámetro explícito.

- `create_collection_service(session, owner_id, name, description)`: el check de duplicado pasa a `WHERE name = ? AND owner_id = ?`. Se crea la colección con `owner_id`.
- `list_collections_service(session, owner_id, ...)`: agrega `Collection.owner_id == owner_id` a las condiciones base.
- `update_collection_service` y `delete_collection_service`: no necesitan `owner_id` aquí porque la verificación de propiedad ya habrá ocurrido en la dependency de ruta.

### 1.4 Dependency de ownership — `backend/app/core/deps.py`

Agregar `get_collection_or_404_owned` que verifica que `collection.owner_id == current_user["sub"]` y lanza 403 si no coincide. Mantener el `get_collection_or_404` original para uso sin auth (futura API pública, fase 3).

```python
def get_collection_or_404_owned(
    collection_id: str,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Collection:
    collection = session.get(Collection, collection_id)
    if not collection or collection.is_deleted:
        raise HTTPException(status_code=404, detail="Colección no encontrada.")
    if collection.owner_id != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    return collection
```

### 1.5 Rutas — `backend/app/api/routes/collections.py`

Dejar de descartar `current_user`:

```python
@router.post("/", response_model=CollectionResponse, status_code=201)
def create_collection(
    request: CreateCollectionRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return create_collection_service(
        session, current_user["sub"], request.name, request.description
    )

@router.get("/", ...)
def get_collections(
    ...,
    current_user: dict = Depends(get_current_user),
    ...
):
    items, total = list_collections_service(session, current_user["sub"], ...)
```

Las rutas de PATCH y DELETE pasan a usar `get_collection_or_404_owned`.

### 1.6 Qdrant namespace — sin cambio requerido

El engine RAG ya usa `collection.id` (UUID) como nombre de colección en Qdrant, no `collection.name`. El namespace ya es globalmente único por diseño. No hay riesgo de colisión entre usuarios.

### 1.7 Frontend — `frontend/src/types/collection.ts`

Agregar `owner_id` al tipo `Collection`:

```typescript
export interface Collection {
  ...
  owner_id: string | null;
}
```

No requiere cambios funcionales en los componentes en esta fase.

### 1.8 Verificación

**Smoke test manual:**
1. Registrar dos usuarios (userA, userB).
2. Con userA: crear colección "Mundo de Tolkien" → 201.
3. Con userB: crear colección "Mundo de Tolkien" → 201 (mismo nombre, distinto owner — constraint compuesto).
4. Con userB: `GET /collections/` → solo ve su colección.
5. Con userB: `PATCH /collections/{id_colección_A}` → 403.

**Tests — `backend/tests/test_collections.py`:**
- Tests `COL-01..COL-16` deben pasar; actualizar fixture `sample_collection` en `conftest.py` para incluir `owner_id="test-user-id"`.
- Nuevo `COL-17`: dos users crean colección con mismo nombre → ambos 201.
- Nuevo `COL-18`: PATCH colección ajena → 403.

---

## Fase 2 — Perfil de usuario + AuthContext en frontend

**Complejidad:** S  
**Prerequisito:** Fase 1  
**Resultado:** usuario puede ver y editar su perfil; frontend tiene estado global de usuario.

### Por qué esta fase antes de visibilidad pública

El perfil del usuario es un prereq para que el frontend pueda mostrar "mis colecciones" y el nombre del owner en la UI. El `AuthContext` desbloquea mostrar el username en el Navbar sin refetching manual.

### 2.1 Modelo User — `backend/app/models/users.py`

Añadir campos opcionales al modelo existente:

```python
class User(SQLModel, table=True):
    ...
    email: Optional[str] = Field(default=None, max_length=255, unique=True, index=True)
    display_name: Optional[str] = Field(default=None, max_length=100)
    bio: Optional[str] = Field(default=None, max_length=500)
    avatar_url: Optional[str] = Field(default=None, max_length=500)
```

`email` es opcional pero único si se provee. `display_name` es lo que se muestra en el feed público (fase 3); si es `None`, se usa `username`.

Nuevos schemas:

```python
class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    username: str
    display_name: Optional[str]
    bio: Optional[str]
    avatar_url: Optional[str]
    created_at: datetime

class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=100)
    bio: Optional[str] = Field(default=None, max_length=500)
    avatar_url: Optional[str] = Field(default=None, max_length=500)
    email: Optional[str] = Field(default=None, max_length=255)
```

### 2.2 Migración Alembic

```python
def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("email", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("display_name", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("bio", sa.String(500), nullable=True))
        batch_op.add_column(sa.Column("avatar_url", sa.String(500), nullable=True))
        batch_op.create_index("ix_users_email", ["email"], unique=True)
```

### 2.3 Rutas — nuevo `backend/app/api/routes/users.py`

```python
router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserProfileResponse)
def get_my_profile(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
): ...

@router.patch("/me", response_model=UserProfileResponse)
def update_my_profile(
    request: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
): ...
```

Registrar en `backend/app/main.py`:
```python
from app.api.routes import users
app.include_router(users.router, prefix="/api/v1")
```

### 2.4 Frontend: AuthContext + useAuth

**Nuevo `frontend/src/contexts/AuthContext.tsx`:**

```typescript
interface AuthUser { id: string; username: string; }
interface AuthContextValue { user: AuthUser | null; logout: () => void; }

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => {
    const token = getToken();
    if (!token) return null;
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      return { id: payload.sub, username: payload.username };
    } catch { return null; }
  });

  function logout() { removeToken(); setUser(null); }

  return <AuthContext.Provider value={{ user, logout }}>{children}</AuthContext.Provider>;
}
```

**Nuevo `frontend/src/hooks/useAuth.ts`:**

```typescript
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
```

**Nuevo `frontend/src/types/user.ts`:**

```typescript
export interface UserProfile {
  id: string;
  username: string;
  display_name: string | null;
  bio: string | null;
  avatar_url: string | null;
  created_at: string;
}
```

**Nuevo `frontend/src/api/users.ts`:**

```typescript
export function getMyProfile(): Promise<UserProfile> { ... }
export function updateMyProfile(data: UpdateProfileRequest): Promise<UserProfile> { ... }
```

**Modificaciones:**
- `frontend/src/App.tsx`: envolver `BrowserRouter` con `<AuthProvider>`.
- `frontend/src/components/ProtectedRoute.tsx`: usar `useAuth().user` en lugar de `isAuthenticated()`.
- `frontend/src/components/Layout.tsx`: usar `useAuth()` para mostrar `username` y gestionar logout.

### 2.5 Verificación

**Smoke test manual:**
1. Login → el Navbar muestra el username.
2. `GET /api/v1/users/me` → `{ id, username, display_name: null, bio: null, ... }`.
3. `PATCH /api/v1/users/me {"bio": "Escritora de mundos"}` → 200 con bio actualizada.
4. Sin token → `GET /users/me` → 401.

**Tests — nuevo `backend/tests/test_users.py`:**
- `USR-01`: GET /users/me autenticado → 200.
- `USR-02`: PATCH /users/me con bio válida → 200.
- `USR-03`: GET /users/me sin token → 401.

**Tests frontend — `frontend/src/test/useAuth.test.ts`:**
- `useAuth()` lanza fuera de `AuthProvider`.
- `user` es `null` cuando no hay token en localStorage.
- `logout()` llama `removeToken()`.

---

## Fase 3 — Visibilidad pública y feed

**Complejidad:** M  
**Prerequisito:** Fase 1 + Fase 2  
**Resultado:** colecciones pueden hacerse públicas; perfiles de usuario accesibles sin auth.

### Por qué esta fase después del perfil

Para mostrar un perfil público necesitamos saber quién es el owner (fase 1) y qué muestra en su perfil (fase 2). El feed público sin esas bases no puede ser contextual.

### 3.1 Campo `is_public` en Collection — `backend/app/models/collections.py`

```python
is_public: bool = SQLField(default=False)
```

Migración: `add_column("collections", "is_public", Boolean, nullable=False, server_default="0")`.

Agregar al `CollectionResponse` y al `UpdateCollectionRequest`.

### 3.2 Endpoint público de colecciones — `backend/app/api/routes/collections.py`

```python
@router.get("/public", response_model=PaginatedResponse[CollectionResponse])
def list_public_collections(
    pagination: Annotated[PaginationParams, Depends()],
    session: Session = Depends(get_session),
    # Sin auth — no requiere Depends(get_current_user)
):
    ...
```

Nueva función `list_public_collections_service(session, page, page_size)` en el servicio que filtra `Collection.is_public == True`.

**Importante:** `/public` debe registrarse **antes** de `/{collection_id}` en el router para que FastAPI no interprete "public" como un `collection_id`.

### 3.3 Acceso a colección individual si es pública — `backend/app/core/deps.py`

Nueva dependency `get_collection_or_404_public_or_owned`: si hay token y el owner coincide → OK. Si la colección es pública → OK. En cualquier otro caso → 403/404.

```python
def get_collection_or_404_public_or_owned(
    collection_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
) -> Collection:
    collection = session.get(Collection, collection_id)
    if not collection or collection.is_deleted:
        raise HTTPException(status_code=404, detail="Colección no encontrada.")
    if collection.is_public:
        return collection
    if credentials:
        payload = verify_token(credentials.credentials)
        if collection.owner_id == payload.get("sub"):
            return collection
    raise HTTPException(status_code=403, detail="Acceso denegado.")
```

### 3.4 Perfil público de usuario — `backend/app/api/routes/users.py`

```python
@router.get("/{username}/profile", response_model=PublicProfileResponse)
def get_public_profile(
    username: str,
    session: Session = Depends(get_session),
    # Sin auth — acceso público
):
    ...
```

Nuevo schema:

```python
class CollectionSummary(BaseModel):
    id: str; name: str; description: str

class PublicProfileResponse(BaseModel):
    username: str
    display_name: Optional[str]
    bio: Optional[str]
    avatar_url: Optional[str]
    public_collections: list[CollectionSummary]
```

### 3.5 Frontend

- `frontend/src/types/collection.ts`: añadir `is_public: boolean`.
- `frontend/src/App.tsx`: añadir rutas `/public` y `/users/:username` fuera de `ProtectedRoute`.
- Nuevas páginas: `PublicFeedPage.tsx` y `PublicProfilePage.tsx`.
- `CollectionEditModal` o equivalente: mostrar toggle "Hacer pública" solo si el user es el owner.

### 3.6 Verificación

**Smoke test manual:**
1. Login como userA, crear colección, hacer `PATCH {"is_public": true}`.
2. Sin token: `GET /api/v1/collections/public` → 200 con la colección de userA.
3. Sin token: `GET /api/v1/users/userA/profile` → 200 con colecciones públicas.
4. Sin token: `GET /api/v1/collections/{id_colección_privada}` → 403.
5. Con token de userB: `GET /api/v1/collections/{id_colección_pública_A}` → 200.

**Tests — nuevo `backend/tests/test_public_feed.py`:**
- `PUB-01`: GET /collections/public sin auth → 200.
- `PUB-02`: Colección privada no aparece en /public.
- `PUB-03`: GET /users/{username}/profile → 200 con colecciones públicas.
- `PUB-04`: GET /users/noexiste/profile → 404.
- `PUB-05`: GET /collections/{id_privada} sin token → 403.
- `PUB-06`: GET /collections/{id_publica} sin token → 200.

---

## Fase 4 — Rol admin (YAGNI-aware)

**Complejidad:** S  
**Prerequisito:** Fase 2  
**Resultado:** un usuario marcado `is_admin=True` puede listar todos los usuarios y hacer soft-delete de contenido ajeno.

### Por qué un flag simple en lugar de RBAC

El proyecto tiene escala de equipo pequeño. Un sistema de roles con permisos granulares requiere tablas adicionales, middleware de permisos, y tests de matrix. Un `is_admin: bool` en User cubre el 100% de las necesidades reales hoy con el 10% de la complejidad. Si en el futuro se necesita un rol moderador con acceso parcial, se puede extender entonces.

### 4.1 Modelo User — `backend/app/models/users.py`

```python
is_admin: bool = Field(default=False)
```

Migración: `add_column("users", "is_admin", Boolean, nullable=False, server_default="0")`.

### 4.2 Dependency admin — `backend/app/core/auth_deps.py`

```python
def get_admin_user(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    user = session.get(User, current_user["sub"])
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    return current_user
```

### 4.3 Rutas admin — nuevo `backend/app/api/routes/admin.py`

```python
router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/users", response_model=PaginatedResponse[UserAdminResponse])
def list_all_users(
    pagination: Annotated[PaginationParams, Depends()],
    _: dict = Depends(get_admin_user),
    session: Session = Depends(get_session),
): ...

@router.delete("/collections/{collection_id}", status_code=204)
def admin_delete_collection(...): ...

@router.delete("/users/{user_id}", status_code=204)
def admin_delete_user(...): ...
```

`UserAdminResponse` extiende `UserProfileResponse` con `is_admin`, `is_deleted`. Nunca expone `hashed_password`.

### 4.4 Activar admin manualmente

Sin endpoint de "self-promote". El primer admin se activa mediante un script de seed en `backend/scripts/make_admin.py`:

```python
# Usage: python scripts/make_admin.py <username>
```

### 4.5 Verificación

**Smoke test manual:**
1. Ejecutar `python scripts/make_admin.py userA`.
2. Con token de userA: `GET /admin/users` → 200.
3. Con token de userB (no admin): `GET /admin/users` → 403.

**Tests — nuevo `backend/tests/test_admin.py`:**
- `ADM-01`: GET /admin/users como admin → 200.
- `ADM-02`: GET /admin/users como user normal → 403.
- `ADM-03`: DELETE /admin/collections/{id} como admin → 204.
- `ADM-04`: DELETE /admin/users/{id} como admin → 204; usuario marcado `is_deleted=True`.

---

## Mapa de archivos completo

### Backend — modificar

| Archivo | Fase | Cambio |
|--------|------|--------|
| `app/models/collections.py` | 1, 3 | Añadir `owner_id`, constraint compuesto, `is_public`, actualizar `CollectionResponse` |
| `app/models/users.py` | 2, 4 | Añadir `email`, `display_name`, `bio`, `avatar_url`, `is_admin` |
| `app/services/collection_service.py` | 1, 3 | Todos los métodos reciben `owner_id`; nueva función pública |
| `app/api/routes/collections.py` | 1, 3 | Usar `current_user["sub"]`; nueva ruta `/public` |
| `app/core/deps.py` | 1, 3 | Añadir `get_collection_or_404_owned`, `get_collection_or_404_public_or_owned` |
| `app/core/auth_deps.py` | 4 | Añadir `get_admin_user` |
| `app/main.py` | 2, 4 | Registrar `users.router`, `admin.router` |
| `tests/conftest.py` | 1 | Actualizar `sample_collection` fixture con `owner_id="test-user-id"` |

### Backend — crear

| Archivo | Fase | Descripción |
|--------|------|-------------|
| `alembic/versions/<hash>_add_owner_id_to_collections.py` | 1 | owner_id nullable + constraint compuesto |
| `alembic/versions/<hash>_user_profile_fields.py` | 2 | email, display_name, bio, avatar_url |
| `alembic/versions/<hash>_add_is_public_to_collections.py` | 3 | is_public en collections |
| `alembic/versions/<hash>_add_is_admin_to_users.py` | 4 | is_admin en users |
| `app/api/routes/users.py` | 2, 3 | GET/PATCH /users/me, GET /users/{username}/profile |
| `app/api/routes/admin.py` | 4 | Endpoints admin |
| `tests/test_users.py` | 2 | Tests de perfil |
| `tests/test_public_feed.py` | 3 | Tests de visibilidad pública |
| `tests/test_admin.py` | 4 | Tests de admin |
| `scripts/make_admin.py` | 4 | Script CLI para promover admin |

### Frontend — modificar

| Archivo | Fase | Cambio |
|--------|------|--------|
| `src/types/collection.ts` | 1, 3 | Añadir `owner_id`, `is_public` |
| `src/components/ProtectedRoute.tsx` | 2 | Usar `useAuth().user` |
| `src/components/Layout.tsx` | 2 | Mostrar username del contexto; logout via `useAuth().logout` |
| `src/pages/LoginPage.tsx` | 2 | Navegar post-auth; contexto se inicializa desde token |
| `src/App.tsx` | 2, 3 | Envolver con `AuthProvider`; añadir rutas públicas |

### Frontend — crear

| Archivo | Fase | Descripción |
|--------|------|-------------|
| `src/contexts/AuthContext.tsx` | 2 | Provider con `user` y `logout` |
| `src/hooks/useAuth.ts` | 2 | Hook que consume `AuthContext` |
| `src/api/users.ts` | 2 | `getMyProfile`, `updateMyProfile` |
| `src/types/user.ts` | 2 | `UserProfile`, `UpdateProfileRequest` |
| `src/pages/PublicFeedPage.tsx` | 3 | Feed público sin auth |
| `src/pages/PublicProfilePage.tsx` | 3 | Perfil público de usuario |

---

## Decisiones de diseño

**`owner_id` nullable vs NOT NULL**: nullable en la DB para migración segura. El servicio trata `owner_id=None` como "colección sin owner" (invisible en el listado normal). Cuando el equipo confirme que no hay datos legacy, se puede hacer una segunda migración a NOT NULL.

**Qdrant ya usa `collection.id`**: el engine RAG usa `lm_{collection_id}` como nombre en Qdrant. No hay riesgo de colisión de namespaces entre usuarios. No requiere cambio.

**JWT payload ya incluye username**: el token ya tiene `{ "sub": user.id, "username": user.username }`. `AuthContext` decodifica el payload (base64) sin hacer un request adicional.

**No hay `role` enum**: reemplazado por `is_admin: bool`. Si en el futuro se necesita un rol "moderador", se añade `is_moderator: bool` con el mismo patrón antes de invertir en RBAC.

**Orden de rutas en collections**: `/public` debe estar antes de `/{collection_id}` en el router para que FastAPI no interprete "public" como un `collection_id`.

**Tests existentes**: el stub de `get_current_user` en `conftest.py` ya retorna `{"sub": "test-user-id"}`. La única fixture que necesita actualización es `sample_collection` para incluir `owner_id="test-user-id"`. Los tests `COL-01..COL-16` deben pasar sin cambios funcionales.

---

## Historial

| Fecha | Descripción |
|-------|-------------|
| 2026-05-07 | Plan reescrito: 4 fases independientes, sin RBAC, migración segura, AuthContext frontend, Qdrant clarificado |