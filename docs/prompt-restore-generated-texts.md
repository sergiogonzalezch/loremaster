# Prompt — Restaurar `generated_texts` y refactorizar `entity_contents`

## Contexto del proyecto

**Lore Master** — plataforma RAG para escritores.  
**Stack:** FastAPI + SQLModel + Alembic (backend), React 19 + TypeScript (frontend).

---

## Problema

El diseño original del ERD tenía dos tablas separadas:

- `generated_texts` — registro inmutable del output del LLM (auditoría)
- `entity_contents` — ciclo de vida editable del contenido (pending / confirmed / discarded)

En una refactorización previa se colapsaron en una sola tabla `entity_contents`, perdiendo la separación de responsabilidades y la trazabilidad de auditoría. Hay que restaurar el diseño original de forma limpia.

---

## Estado actual de `entity_contents`

```python
class EntityContent(SQLModel, table=True):
    __tablename__ = "entity_contents"
    id: str           # PK UUID
    entity_id: str    # FK entities
    collection_id: str  # FK collections
    query: str        # max 2000
    sources_count: int
    token_count: int
    category: ContentCategory  # backstory|extended_description|scene|chapter
    content: str      # max 10000 — editable
    status: ContentStatus  # pending|confirmed|discarded
    created_at: datetime
    confirmed_at: Optional[datetime]
    updated_at: Optional[datetime]
    is_deleted: bool
    deleted_at: Optional[datetime]
```

---

## Diseño objetivo

### Tabla nueva `generated_texts` — inmutable, sin soft-delete

| Tipo | Campo | Notas |
|------|-------|-------|
| UUID | id | PK |
| UUID | entity_id | FK entities, index |
| UUID | collection_id | FK collections, index |
| ENUM | category | backstory \| extended_description \| scene \| chapter |
| string | query | max 2000 |
| text | raw_content | max 10000 — output exacto del LLM, **NUNCA se modifica** |
| int | sources_count | |
| int | token_count | |
| datetime | created_at | |

> Sin `updated_at`, sin `is_deleted`, sin `deleted_at`. Es inmutable por diseño.

### Tabla `entity_contents` modificada

| Tipo | Campo | Notas |
|------|-------|-------|
| UUID | id | PK |
| UUID | entity_id | FK entities, index |
| UUID | collection_id | FK collections, index |
| UUID | generated_text_id | FK generated_texts, index — **NUEVO** |
| ENUM | category | ContentCategory |
| text | content | max 10000 — editable por el usuario |
| ENUM | status | ContentStatus |
| datetime | created_at | |
| datetime | confirmed_at | Optional |
| datetime | updated_at | Optional |
| bool | is_deleted | |
| datetime | deleted_at | Optional |

> `query`, `sources_count` y `token_count` se quitan de aquí — viven en `generated_texts`.

---

## Archivos a crear / modificar

### Backend

#### 1. `backend/app/models/generated_texts.py` — CREAR

Modelo SQLModel `GeneratedText` con la estructura definida arriba.  
Schema `GeneratedTextResponse` (BaseModel).  
Sin soft-delete, sin `updated_at`.

#### 2. `backend/app/models/entity_content.py` — MODIFICAR

- Agregar campo `generated_text_id: str` (FK a `generated_texts`)
- Quitar campos: `query`, `sources_count`, `token_count`
- Actualizar `EntityContentResponse`:

```python
class EntityContentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    entity_id: str
    collection_id: str
    generated_text_id: str          # NUEVO
    category: ContentCategory
    content: str                    # editable
    raw_content: Optional[str] = None   # NUEVO — poblado via join
    was_edited: bool = False            # NUEVO — computed: content != raw_content
    query: Optional[str] = None         # poblado via join (compatibilidad)
    sources_count: int = 0              # poblado via join (compatibilidad)
    token_count: int = 0                # poblado via join (compatibilidad)
    status: ContentStatus
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @model_validator(mode="after")
    def compute_was_edited(self) -> "EntityContentResponse":
        if self.raw_content is not None:
            object.__setattr__(
                self,
                "was_edited",
                self.content != self.raw_content
            )
        return self
```

#### 3. `backend/app/models/__init__.py` — MODIFICAR

Importar `GeneratedText` junto a los otros modelos existentes.

#### 4. `backend/app/services/generation_service.py` — MODIFICAR

En `generate()`, reemplazar la creación del `EntityContent` por este flujo:

```python
# 1. Guardar el raw — registro de auditoría inmutable
generated_text = GeneratedText(
    entity_id=entity.id,
    collection_id=entity.collection_id,
    category=category,
    query=query.strip(),
    raw_content=answer,
    sources_count=sources_count,
    token_count=max(1, len(answer) // 4),
)
session.add(generated_text)
session.flush()  # necesitamos el ID antes del commit

# 2. Crear el contenido editable apuntando al raw
content = EntityContent(
    entity_id=entity.id,
    collection_id=entity.collection_id,
    generated_text_id=generated_text.id,
    category=category,
    content=answer,          # copia inicial del raw
    status=ContentStatus.pending,
)
session.add(content)
```

#### 5. `backend/app/services/content_management_service.py` — MODIFICAR

- En `edit_content()`: **NO tocar `generated_text` nunca**, solo modificar `content`
- En `list_contents()`: hacer JOIN con `generated_texts` para poblar `raw_content`, `query`, `sources_count`, `token_count` en el response

```python
# El join es:
EntityContent.generated_text_id == GeneratedText.id
```

#### 6. `backend/app/api/routes/entity_content.py` — REVISAR

Verificar que ningún endpoint referencie campos que se movieron.  
El contrato externo no cambia: los consumers siguen recibiendo `query`, `sources_count`, `token_count` en el response (vienen del join).

#### 7. `backend/alembic/versions/xxxx_restore_generated_texts.py` — CREAR

Migración en este orden **exacto**:

```python
def upgrade() -> None:
    # a) Crear tabla generated_texts
    op.create_table(
        "generated_texts",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(length=36), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("collection_id", sa.String(36), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("query", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=False),
        sa.Column("raw_content", sqlmodel.sql.sqltypes.AutoString(length=10000), nullable=False),
        sa.Column("sources_count", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["collection_id"], ["collections.id"]),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("generated_texts") as batch_op:
        batch_op.create_index("ix_generated_texts_entity_id", ["entity_id"])
        batch_op.create_index("ix_generated_texts_collection_id", ["collection_id"])

    # b) Poblar generated_texts desde entity_contents existentes
    op.execute("""
        INSERT INTO generated_texts
            (id, entity_id, collection_id, category, query,
             raw_content, sources_count, token_count, created_at)
        SELECT
            lower(hex(randomblob(4))) || '-' ||
            lower(hex(randomblob(2))) || '-4' ||
            substr(lower(hex(randomblob(2))),2) || '-' ||
            substr('89ab', abs(random()) % 4 + 1, 1) ||
            substr(lower(hex(randomblob(2))),2) || '-' ||
            lower(hex(randomblob(6))),
            entity_id, collection_id, category, query,
            content, sources_count, token_count, created_at
        FROM entity_contents
        WHERE is_deleted = 0
    """)

    # c) Agregar columna generated_text_id (nullable primero)
    with op.batch_alter_table("entity_contents") as batch_op:
        batch_op.add_column(
            sa.Column("generated_text_id",
                      sqlmodel.sql.sqltypes.AutoString(length=36),
                      nullable=True)
        )

    # d) Vincular registros existentes
    op.execute("""
        UPDATE entity_contents
        SET generated_text_id = (
            SELECT gt.id FROM generated_texts gt
            WHERE gt.entity_id = entity_contents.entity_id
              AND gt.collection_id = entity_contents.collection_id
              AND gt.category = entity_contents.category
              AND gt.created_at = entity_contents.created_at
        )
        WHERE is_deleted = 0
    """)

    # e) Hacer NOT NULL y crear FK
    with op.batch_alter_table("entity_contents") as batch_op:
        batch_op.alter_column("generated_text_id", nullable=False)
        batch_op.create_foreign_key(
            "fk_entity_contents_generated_text_id",
            "generated_texts", ["generated_text_id"], ["id"]
        )

    # f) Quitar columnas que se movieron a generated_texts
    with op.batch_alter_table("entity_contents") as batch_op:
        batch_op.drop_column("query")
        batch_op.drop_column("sources_count")
        batch_op.drop_column("token_count")


def downgrade() -> None:
    # Restaurar columnas en entity_contents
    with op.batch_alter_table("entity_contents") as batch_op:
        batch_op.add_column(sa.Column("query", sa.String(2000), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("sources_count", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"))
        batch_op.drop_constraint("fk_entity_contents_generated_text_id", type_="foreignkey")
        batch_op.drop_column("generated_text_id")

    op.drop_table("generated_texts")
```

> **Nota:** `render_as_batch=True` ya está configurado en `alembic/env.py`.  
> Si aparece conflicto con el Enum `contentcategory`, usar `sa.String(50)` en lugar de `sa.Enum(...)` para la nueva tabla.

#### 8. `backend/tests/test_entity_content.py` — MODIFICAR

Actualizar fixtures que construyen `EntityContent` directamente: deben crear primero un `GeneratedText` y pasar `generated_text_id`.

Agregar estos tests nuevos:

```python
@pytest.mark.anyio
async def test_raw_content_never_changes_after_edit(
    client, db_session, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """El raw_content de generated_texts NO cambia al editar el content."""
    created = await _create_content(client, sample_collection.id, sample_entity.id)
    content_id = created.json()["id"]
    generated_text_id = created.json()["generated_text_id"]
    original_raw = db_session.get(GeneratedText, generated_text_id).raw_content

    await client.patch(
        f"/api/v1/collections/{sample_collection.id}/entities/"
        f"{sample_entity.id}/contents/{content_id}",
        json={"content": "Texto completamente diferente"},
    )

    gt = db_session.get(GeneratedText, generated_text_id)
    assert gt.raw_content == original_raw


@pytest.mark.anyio
async def test_was_edited_false_on_creation(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """was_edited es False cuando el content no ha sido modificado."""
    resp = await _create_content(client, sample_collection.id, sample_entity.id)
    assert resp.json()["was_edited"] is False


@pytest.mark.anyio
async def test_was_edited_true_after_edit(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """was_edited es True después de editar el content."""
    created = await _create_content(client, sample_collection.id, sample_entity.id)
    content_id = created.json()["id"]

    edited = await client.patch(
        f"/api/v1/collections/{sample_collection.id}/entities/"
        f"{sample_entity.id}/contents/{content_id}",
        json={"content": "Texto editado manualmente"},
    )
    assert edited.json()["was_edited"] is True


@pytest.mark.anyio
async def test_content_equals_raw_on_creation(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """Al crear, content y raw_content son idénticos."""
    resp = await _create_content(client, sample_collection.id, sample_entity.id)
    data = resp.json()
    assert data["content"] == data["raw_content"]
```

#### 9. `backend/tests/conftest.py` — MODIFICAR

El fixture `sample_entity_content` (si existe) debe crear primero un `GeneratedText` y luego el `EntityContent` con `generated_text_id`.

---

### Frontend

#### 10. `frontend/src/types/content.ts` — MODIFICAR

```typescript
export interface EntityContent {
  id: string;
  entity_id: string;
  collection_id: string;
  generated_text_id: string;    // NUEVO
  category: ContentCategory;
  content: string;              // editable
  raw_content: string | null;   // NUEVO — output original del LLM
  was_edited: boolean;          // NUEVO — computed por backend
  query: string;                // viene del join
  sources_count: number;        // viene del join
  token_count: number;          // viene del join
  status: ContentStatus;
  created_at: string;
  confirmed_at: string | null;
  updated_at: string | null;
}
```

#### 11. `frontend/src/components/ContentCard.tsx` — MODIFICAR

**a) Badge de auditoría** — agregar junto a los otros badges en `Accordion.Header`:

```tsx
{content.was_edited && (
  <Badge
    style={{
      background: "rgba(201,162,39,0.1)",
      color: "#c9a227",
      border: "1px solid rgba(201,162,39,0.3)",
      fontSize: "0.6rem",
    }}
    title="Editado por el usuario. Output original del LLM preservado para auditoría."
  >
    ✎ editado
  </Badge>
)}
```

**b) Sección colapsable** — agregar al final del `Accordion.Body`, solo cuando `was_edited === true` y `raw_content !== null`:

```tsx
{content.was_edited && content.raw_content && (
  <details className="mt-3">
    <summary
      style={{
        fontSize: "0.75rem",
        color: "var(--lm-text-muted)",
        cursor: "pointer",
        userSelect: "none",
      }}
    >
      Ver output original del LLM
    </summary>
    <div
      className="mt-2 p-2"
      style={{
        borderLeft: "2px solid rgba(201,162,39,0.3)",
        fontSize: "0.88rem",
        color: "var(--lm-text-muted)",
        fontStyle: "italic",
      }}
    >
      <MarkdownContent>{content.raw_content}</MarkdownContent>
    </div>
  </details>
)}
```

> Se usa `<details>` nativo del navegador — sin estado React, sin dependencias, colapsado por defecto.

---

## Invariantes que DEBEN mantenerse

1. `generated_texts.raw_content` se escribe **una sola vez** en `generation_service.generate()` y **nunca se modifica** por ningún otro código
2. `generated_texts` **no tiene soft-delete** — es el registro permanente de auditoría
3. El contrato externo de los endpoints **no cambia**: los responses siguen incluyendo `query`, `sources_count`, `token_count` (se obtienen via join)
4. Los tests existentes de `entity_content` deben seguir pasando
5. `alembic upgrade head` debe correr sin errores sobre una DB con datos existentes
6. `alembic downgrade -1` debe revertir el cambio limpiamente

---

## Qué NO hacer

- No cambiar el contrato de ningún otro endpoint (`collections`, `entities`, `documents`)
- No modificar los servicios de deletion — el cascade delete de `entity_contents` ya funciona; `generated_texts` **no se borra en cascade**, es auditoría
- No agregar endpoints nuevos para `generated_texts` en este cambio (se expone solo via el response de `entity_contents`)
- No tocar `frontend/src/pages/` excepto si hay un import roto por el cambio de tipos

---

## Verificación final esperada

| Check | Comando / Criterio |
|-------|--------------------|
| Tests backend | `pytest` pasa completo |
| Migración up | `alembic upgrade head` sin errores |
| Migración down | `alembic downgrade -1` sin errores |
| Endpoint contents | `GET /api/v1/collections/{id}/entities/{eid}/contents` devuelve `was_edited`, `raw_content`, `generated_text_id` en cada item |
| UI auditoría | Un `EntityContent` editado muestra badge "✎ editado" y sección colapsable con el output original |
| Inmutabilidad | Editar un content no modifica `generated_texts.raw_content` en DB |
