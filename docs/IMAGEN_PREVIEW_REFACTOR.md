# Plan de Refactor: Sistema de Preview de Imágenes

**Versión:** 1.0  
**Fecha:** 2026-04-29  
**Alcance:** Backend + Frontend — Opción C implementada, preparación para Opción B (siguiente sprint)

---

## Contexto y decisiones tomadas

| # | Decisión | Resolución |
|---|----------|------------|
| 1 | Ubicación del preview | Botón en `ContentCard` (confirmed) → pestaña/modal aparte con prompt base y prompt visual |
| 2 | Estrategia del prompt builder | **Opción C** (templates por categoría). Código preparado para **Opción B** (extracción LLM) en siguiente sprint |
| 3 | Persistencia | Efímero en frontend ahora. Backend almacena URL + metadatos. Imagen en `media/{collection_id}/{entity_id}/{image_id}.png` |
| 4 | Base de reglas | `domain/category_rules.py` + `domain/prompt_templates.py` como fuente de verdad |

---

## Análisis de categorías y estrategia visual

Basado en `prompt_templates.py` y `category_rules.py`:

### Por qué cada categoría necesita estrategia diferente

| Categoría | Qué genera el LLM | Problema para imagen | Estrategia visual |
|-----------|-------------------|---------------------|-------------------|
| `backstory` | Orígenes, motivaciones, eventos pasados en prosa narrativa | El texto describe *qué pasó*, no *cómo se ve* | `entity_only` — usar descripción de entidad + mood de origen |
| `extended_description` | Rasgos físicos, apariencia, características distintivas | **Es directamente útil** — ya describe lo visual | `direct` — extraer el texto, es un descriptor natural |
| `scene` | Ambientación, diálogo, acción con setting | Las primeras oraciones suelen tener el setting y los personajes | `first_sentences` — 2 primeras oraciones tienen contexto visual |
| `chapter` | Capítulo completo con inicio/desarrollo/cierre | Demasiado texto, solo el inicio es visualmente útil | `first_sentences` — 1-2 oraciones de apertura |

### Estrategia por entity type + category

```
character + backstory          → entity_only    (dramatic origin, atmospheric)
character + extended_desc      → direct         (portrait, appearance details)
character + scene              → first_sentences (action scene, setting)
character + chapter            → first_sentences (epic narrative scene)

creature  + backstory          → entity_only    (creature origin, wilderness)
creature  + extended_desc      → direct         (creature anatomy, detailed)
creature  + scene              → first_sentences (creature in action)

location  + extended_desc      → direct         (landscape, establishing shot)
location  + scene              → first_sentences (location with activity)

faction   + backstory          → entity_only    (faction symbol, heraldic)
faction   + extended_desc      → direct         (faction imagery, symbolic)
faction   + scene              → first_sentences (faction members, setting)

item      + backstory          → entity_only    (artifact with mystical aura)
item      + extended_desc      → direct         (item showcase, material detail)
```

---

## Archivos a crear y modificar

### Backend — nuevos
```
backend/app/domain/prompt_builder.py              ← REFACTOR COMPLETO
backend/app/models/image_generation.py            ← añadir ImageRecord
backend/app/services/image_generation_service.py  ← REFACTOR
backend/app/api/routes/image_generation.py        ← content_id obligatorio + category
backend/alembic/versions/xxxx_add_image_records.py ← nueva migración
backend/tests/test_prompt_builder.py              ← REFACTOR tests
backend/tests/test_image_generation.py            ← REFACTOR tests
```

### Backend — modificados
```
backend/app/core/config.py      ← añadir MEDIA_ROOT
backend/app/main.py             ← registrar router si no está
backend/.env.example            ← MEDIA_ROOT
backend/app/models/__init__.py  ← importar ImageRecord
```

### Frontend — nuevos
```
frontend/src/api/images.ts              ← wrapper endpoint
frontend/src/types/image.ts             ← tipos TypeScript
frontend/src/pages/ImagePreviewPage.tsx ← página dedicada al preview
```

### Frontend — modificados
```
frontend/src/components/ContentCard.tsx    ← botón "Preview imagen" en confirmed
frontend/src/App.tsx                       ← nueva ruta /collections/:id/entities/:eid/contents/:cid/image-preview
```

---

## Paso 1 — `config.py`

```python
# Añadir a Settings:

# Image generation
image_prompt_max_tokens: int = 150
image_prompt_target_tokens: int = 75
image_backend: str = "mock"          # mock | local | runpod
media_root: str = "media"            # carpeta raíz para imágenes generadas
```

---

## Paso 2 — `prompt_builder.py` (Opción C + preparación B)

```python
# backend/app/domain/prompt_builder.py

"""
Construcción de prompts visuales para generación de imágenes.

Estrategia actual: Opción C — templates por categoría (determinista, sin LLM).
Preparado para Opción B — extracción semántica vía LLM (próximo sprint).

La estrategia se selecciona con IMAGE_BACKEND y PROMPT_STRATEGY en config.
Cuando PROMPT_STRATEGY="llm" se usará invoke_prompt_extraction_pipeline()
que aún no está implementado — ver TODO marcados con [OPTION_B].
"""

from __future__ import annotations

from app.models.entities import EntityType
from app.models.enums import ContentCategory


# ── Prefijos visuales por entity type ────────────────────────────────────────

STYLE_PREFIX: dict[EntityType, str] = {
    EntityType.character: (
        "fantasy character portrait, detailed face, "
        "cinematic lighting, epic atmosphere,"
    ),
    EntityType.creature: (
        "fantasy creature illustration, dramatic pose, "
        "detailed anatomy, dark fantasy art,"
    ),
    EntityType.location: (
        "fantasy landscape, wide establishing shot, "
        "atmospheric perspective, detailed environment,"
    ),
    EntityType.faction: (
        "faction emblem design, heraldic composition, "
        "fantasy art, symbolic imagery,"
    ),
    EntityType.item: (
        "fantasy item showcase, neutral background, "
        "detailed textures, magical aura, product lighting,"
    ),
}

# ── Sufijo de calidad fijo ────────────────────────────────────────────────────

QUALITY_SUFFIX = (
    "high quality, masterpiece, sharp focus, professional digital art"
)

# ── Estrategia visual por categoría ──────────────────────────────────────────
# Derivada de prompt_templates.py:
#   backstory        → narrativa de orígenes, NO descriptores visuales
#   extended_desc    → rasgos físicos y apariencia, SÍ descriptores visuales
#   scene            → ambientación + acción, primeras oraciones útiles
#   chapter          → narrativa larga, solo apertura es visual

CATEGORY_VISUAL_STRATEGY: dict[ContentCategory, dict] = {
    ContentCategory.extended_description: {
        # El LLM genera: "rasgos, apariencia, características distintivas"
        # → texto directamente útil como descriptor visual
        "strategy": "direct",
        "prefix_addition": "detailed appearance,",
        # [OPTION_B] llm_instruction: "Extrae solo descriptores físicos y
        # visuales. Formato: adjetivo sustantivo separados por coma."
    },
    ContentCategory.backstory: {
        # El LLM genera: "orígenes, motivaciones, eventos formativos"
        # → narrativa en prosa, NO útil directo para imagen
        # → usar solo entidad + descripción + mood de origen
        "strategy": "entity_only",
        "prefix_addition": "dramatic origin scene, atmospheric,",
        # [OPTION_B] llm_instruction: "Del texto de trasfondo extrae solo
        # el ambiente visual del lugar de origen y rasgos físicos si los hay.
        # Máximo 10 palabras visuales."
    },
    ContentCategory.scene: {
        # El LLM genera: "ambientación, diálogo y acción"
        # → las primeras 1-2 oraciones tienen el setting y los actores
        "strategy": "first_sentences",
        "prefix_addition": "action scene, dynamic composition,",
        "sentences": 2,
        # [OPTION_B] llm_instruction: "Extrae el setting visual de la escena:
        # lugar, iluminación, postura de personajes. Máximo 12 palabras."
    },
    ContentCategory.chapter: {
        # El LLM genera: "capítulo con inicio, desarrollo y cierre"
        # → solo las primeras oraciones establecen el contexto visual
        "strategy": "first_sentences",
        "prefix_addition": "epic narrative scene, cinematic,",
        "sentences": 1,
        # [OPTION_B] llm_instruction: "Extrae solo la descripción visual
        # de la escena de apertura. Máximo 10 palabras descriptivas."
    },
}

# ── Utilidades de tokens ──────────────────────────────────────────────────────

def _estimate_tokens(text: str) -> int:
    """~4 chars por token. Consistente con estimateTokens() del frontend."""
    return max(0, len(text) // 4)


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Trunca a max_tokens preservando palabras completas."""
    if _estimate_tokens(text) <= max_tokens:
        return text
    words = text.split()
    result: list[str] = []
    for word in words:
        candidate = " ".join(result + [word])
        if _estimate_tokens(candidate) > max_tokens:
            break
        result.append(word)
    return " ".join(result)


def _extract_first_sentences(text: str, n: int = 2) -> str:
    """Extrae las primeras N oraciones de un texto."""
    import re
    # Separar por punto, signo de exclamación o interrogación seguido de espacio/fin
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(sentences[:n])


# ── Builder principal ─────────────────────────────────────────────────────────

def build_visual_prompt(
    entity_type: EntityType,
    entity_name: str,
    entity_description: str,
    confirmed_content: str,
    category: ContentCategory,
    max_tokens: int = 150,
    target_tokens: int = 75,
) -> dict[str, str | int | bool]:
    """
    Construye un prompt visual para generación de imagen.

    Estrategia: Opción C (templates deterministas por categoría).
    Ver CATEGORY_VISUAL_STRATEGY para la lógica por categoría.

    # [OPTION_B] Cuando se implemente extracción LLM:
    # - Añadir parámetro use_llm_extraction: bool = False
    # - Si use_llm_extraction=True, llamar a invoke_prompt_extraction_pipeline()
    #   pasando confirmed_content + strategy["llm_instruction"]
    # - El resultado reemplaza a `narrative` antes del ensamblado final

    Retorna:
        {
            "prompt": str,
            "token_count": int,
            "truncated": bool,
            "source": str,      # "content_direct" | "content_sentences" |
                                #  "entity_only" | "description" | "name_only"
            "strategy": str,    # estrategia aplicada
            "category": str,    # categoría del contenido base
        }
    """
    strategy_config = CATEGORY_VISUAL_STRATEGY.get(
        category,
        {"strategy": "entity_only", "prefix_addition": ""},
    )
    strategy = strategy_config["strategy"]
    prefix_addition = strategy_config.get("prefix_addition", "")

    prefix = STYLE_PREFIX.get(entity_type, "fantasy art,")
    if prefix_addition:
        prefix = f"{prefix} {prefix_addition}"

    # ── Calcular tokens disponibles para narrativa ────────────────────────────
    prefix_tokens = _estimate_tokens(prefix)
    suffix_tokens = _estimate_tokens(QUALITY_SUFFIX)
    name_tokens = _estimate_tokens(entity_name)
    overhead = prefix_tokens + suffix_tokens + name_tokens + 5
    available_tokens = max_tokens - overhead
    target_available = max(10, target_tokens - overhead)

    # ── Extraer narrativa según estrategia ────────────────────────────────────
    narrative = ""
    source = "name_only"
    truncated = False

    if strategy == "direct" and confirmed_content.strip():
        # extended_description: usar el texto directamente
        narrative = confirmed_content.strip()
        source = "content_direct"

    elif strategy == "first_sentences" and confirmed_content.strip():
        # scene / chapter: extraer primeras N oraciones
        n = strategy_config.get("sentences", 2)
        narrative = _extract_first_sentences(confirmed_content, n)
        source = "content_sentences"

    elif strategy == "entity_only":
        # backstory: el texto narrativo no es útil visualmente
        # usar descripción de la entidad si existe
        if entity_description.strip():
            narrative = entity_description.strip()
            source = "description"
        # si no hay descripción, source queda "name_only"

    # Fallback: si la estrategia no produjo narrativa, intentar descripción
    if not narrative and entity_description.strip():
        narrative = entity_description.strip()
        source = "description"

    # ── Truncar para respetar límite de tokens ────────────────────────────────
    if narrative:
        if _estimate_tokens(narrative) > target_available:
            narrative_at_target = _truncate_to_tokens(narrative, target_available)
            if narrative_at_target:
                narrative = narrative_at_target
                truncated = _estimate_tokens(confirmed_content) > target_available
            elif _estimate_tokens(narrative) <= available_tokens:
                # No cabe en target pero sí en max
                truncated = False
            else:
                narrative = _truncate_to_tokens(narrative, available_tokens)
                truncated = True

    # ── Ensamblar prompt final ────────────────────────────────────────────────
    parts = [prefix, entity_name]
    if narrative:
        parts.append(narrative)
    parts.append(QUALITY_SUFFIX)

    prompt = ", ".join(p.strip().rstrip(",") for p in parts if p.strip())
    token_count = _estimate_tokens(prompt)

    return {
        "prompt": prompt,
        "token_count": token_count,
        "truncated": truncated,
        "source": source,
        "strategy": strategy,
        "category": category.value,
    }
```

---

## Paso 3 — `image_generation.py` (modelo + schemas)

```python
# backend/app/models/image_generation.py

import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, ForeignKey, String
from sqlmodel import SQLModel, Field as SQLField


# ── Tabla DB ──────────────────────────────────────────────────────────────────

class ImageRecord(SQLModel, table=True):
    """
    Registro de imagen generada.
    La imagen física se almacena en: media/{collection_id}/{entity_id}/{id}.png
    Este modelo solo guarda los metadatos y la ruta relativa.
    """
    __tablename__ = "generated_images"

    id: str = SQLField(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        max_length=36,
    )
    entity_id: str = SQLField(
        sa_column=Column(String(36), ForeignKey("entities.id"),
                         nullable=False, index=True)
    )
    collection_id: str = SQLField(
        sa_column=Column(String(36), ForeignKey("collections.id"),
                         nullable=False, index=True)
    )
    content_id: Optional[str] = SQLField(
        sa_column=Column(String(36), ForeignKey("entity_contents.id"),
                         nullable=True, index=True)
    )
    category: str = SQLField(max_length=50)

    # Prompt
    visual_prompt: str = SQLField(max_length=1000)
    prompt_token_count: int = SQLField(default=0)
    prompt_source: str = SQLField(max_length=50)   # content_direct | content_sentences | entity_only | description | name_only
    prompt_strategy: str = SQLField(max_length=50)  # direct | first_sentences | entity_only
    truncated: bool = SQLField(default=False)

    # Imagen
    # Ruta relativa desde MEDIA_ROOT: {collection_id}/{entity_id}/{id}.png
    # Ejemplo: "abc-123/def-456/img-uuid.png"
    image_path: Optional[str] = SQLField(default=None, max_length=500)
    image_url: Optional[str] = SQLField(default=None, max_length=500)
    filename: Optional[str] = SQLField(default=None, max_length=255)
    extension: str = SQLField(default="png", max_length=10)
    width: int = SQLField(default=1024)
    height: int = SQLField(default=1024)

    # Generación
    backend: str = SQLField(default="mock", max_length=20)  # mock | local | runpod
    seed: int = SQLField(default=42)
    generation_ms: int = SQLField(default=0)

    # Ciclo de vida (igual que EntityContent)
    status: str = SQLField(default="pending", max_length=20)  # pending | confirmed | discarded
    created_at: datetime = SQLField(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    confirmed_at: Optional[datetime] = SQLField(default=None)
    updated_at: Optional[datetime] = SQLField(default=None)
    is_deleted: bool = SQLField(default=False)
    deleted_at: Optional[datetime] = SQLField(default=None)


# ── API Schemas ───────────────────────────────────────────────────────────────

class GenerateImageRequest(BaseModel):
    content_id: str = Field(
        ...,
        description="ID del EntityContent confirmado que sirve como base narrativa.",
    )


class GenerateImageResponse(BaseModel):
    id: str
    entity_id: str
    collection_id: str
    content_id: Optional[str]
    category: str

    # Prompt
    visual_prompt: str
    prompt_token_count: int
    prompt_source: str
    prompt_strategy: str
    truncated: bool

    # Imagen
    image_url: str
    image_path: Optional[str]
    filename: Optional[str]
    extension: str
    width: int
    height: int

    # Generación
    backend: str
    seed: int
    generation_ms: int

    # Estado
    status: str
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

---

## Paso 4 — `image_generation_service.py` (refactor)

```python
# backend/app/services/image_generation_service.py

import os
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.core.config import settings
from app.core.exceptions import (
    ContentNotAllowedError,
    DatabaseError,
    NoContextAvailableError,
)
from app.domain.content_guard import check_user_input
from app.domain.prompt_builder import build_visual_prompt
from app.models.entities import Entity
from app.models.entity_content import EntityContent
from app.models.enums import ContentStatus
from app.models.image_generation import ImageRecord, GenerateImageResponse


def generate_image_service(
    session: Session,
    entity: Entity,
    content_id: str,
) -> GenerateImageResponse:
    """
    Genera un preview de imagen para un EntityContent confirmado.

    Flujo:
    1. Verificar que content_id pertenece a esta entidad y está confirmed
    2. Guardrail sobre el contenido
    3. build_visual_prompt() con estrategia por categoría (Opción C)
    4. [MOCK] Generar URL placeholder — aquí irá ComfyUI en Opción B
    5. Persistir ImageRecord con metadatos
    6. Retornar response

    # [OPTION_B] Cuando se integre ComfyUI:
    # - Reemplazar el bloque MOCK con invoke_comfy_pipeline(visual_prompt, seed)
    # - La función retornará image_bytes
    # - Guardar image_bytes en MEDIA_ROOT/{collection_id}/{entity_id}/{id}.png
    # - Actualizar image_path e image_url en el ImageRecord
    """

    # 1. Resolver contenido confirmado
    content = session.exec(
        select(EntityContent).where(
            EntityContent.id == content_id,
            EntityContent.entity_id == entity.id,
            EntityContent.collection_id == entity.collection_id,
            EntityContent.status == ContentStatus.confirmed,
            EntityContent.is_deleted == False,
        )
    ).first()

    if not content:
        raise NoContextAvailableError()

    # 2. Guardrail
    if content.content:
        check_user_input(content.content[:500])

    # 3. Construir prompt visual
    build_result = build_visual_prompt(
        entity_type=entity.type,
        entity_name=entity.name,
        entity_description=entity.description,
        confirmed_content=content.content,
        category=content.category,
        max_tokens=settings.image_prompt_max_tokens,
        target_tokens=settings.image_prompt_target_tokens,
    )

    # 4. [MOCK] — reemplazar con ComfyUI en Opción B
    # [OPTION_B] image_bytes = await invoke_comfy_pipeline(
    #     prompt=build_result["prompt"],
    #     seed=seed,
    #     width=1024,
    #     height=1024,
    # )
    import uuid as _uuid
    image_id = str(_uuid.uuid4())
    seed = 42

    placeholder_url = (
        f"https://placehold.co/1024x1024/1a1a2e/9d6fe8"
        f"?text={entity.name.replace(' ', '+')}"
    )

    # Ruta relativa donde se guardaría la imagen real
    # [OPTION_B] Aquí se guardaría image_bytes en esta ruta
    relative_path = (
        f"{entity.collection_id}/{entity.id}/{image_id}.png"
    )
    filename = f"{image_id}.png"

    # 5. Persistir registro
    record = ImageRecord(
        id=image_id,
        entity_id=entity.id,
        collection_id=entity.collection_id,
        content_id=content_id,
        category=content.category.value,
        visual_prompt=build_result["prompt"],
        prompt_token_count=build_result["token_count"],
        prompt_source=build_result["source"],
        prompt_strategy=build_result["strategy"],
        truncated=build_result["truncated"],
        image_path=relative_path,
        image_url=placeholder_url,   # [OPTION_B] será la URL real de S3/local
        filename=filename,
        extension="png",
        width=1024,
        height=1024,
        backend=settings.image_backend,
        seed=seed,
        generation_ms=0,             # [OPTION_B] medir tiempo real
        status="pending",
    )

    session.add(record)
    try:
        session.commit()
        session.refresh(record)
    except SQLAlchemyError as e:
        session.rollback()
        raise DatabaseError() from e

    return GenerateImageResponse(
        id=record.id,
        entity_id=record.entity_id,
        collection_id=record.collection_id,
        content_id=record.content_id,
        category=record.category,
        visual_prompt=record.visual_prompt,
        prompt_token_count=record.prompt_token_count,
        prompt_source=record.prompt_source,
        prompt_strategy=record.prompt_strategy,
        truncated=record.truncated,
        image_url=record.image_url,
        image_path=record.image_path,
        filename=record.filename,
        extension=record.extension,
        width=record.width,
        height=record.height,
        backend=record.backend,
        seed=record.seed,
        generation_ms=record.generation_ms,
        status=record.status,
        created_at=record.created_at,
        confirmed_at=record.confirmed_at,
        updated_at=record.updated_at,
    )
```

---

## Paso 5 — Route (`image_generation.py`)

```python
# backend/app/api/routes/image_generation.py

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.deps import get_entity_or_404
from app.core.exceptions import (
    ContentNotAllowedError,
    DatabaseError,
    NoContextAvailableError,
)
from app.database import get_session
from app.models.entities import Entity
from app.models.image_generation import GenerateImageRequest, GenerateImageResponse
from app.services.image_generation_service import generate_image_service

router = APIRouter(prefix="/collections", tags=["image-generation"])


@router.post(
    "/{collection_id}/entities/{entity_id}/generate/image",
    response_model=GenerateImageResponse,
    status_code=201,
)
def generate_image(
    request: GenerateImageRequest,
    entity: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    try:
        return generate_image_service(session, entity, request.content_id)
    except NoContextAvailableError:
        raise HTTPException(
            status_code=422,
            detail=(
                "El contenido indicado no existe, no está confirmado "
                "o no pertenece a esta entidad."
            ),
        )
    except ContentNotAllowedError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Error interno del servidor.")
```

---

## Paso 6 — Migración Alembic

```python
# backend/alembic/versions/xxxx_add_generated_images.py

"""Add generated_images table

Revision ID: xxxx
Revises: 37e42a332ba5
Create Date: 2026-04-29
"""

from alembic import op
import sqlalchemy as sa
import sqlmodel


def upgrade() -> None:
    op.create_table(
        "generated_images",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(length=36), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("collection_id", sa.String(36), nullable=False),
        sa.Column("content_id", sa.String(36), nullable=True),
        sa.Column("category", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("visual_prompt", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=False),
        sa.Column("prompt_token_count", sa.Integer(), nullable=False),
        sa.Column("prompt_source", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("prompt_strategy", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("truncated", sa.Boolean(), nullable=False),
        sa.Column("image_path", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("image_url", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("filename", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("extension", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("backend", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("generation_ms", sa.Integer(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["collection_id"], ["collections.id"]),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"]),
        sa.ForeignKeyConstraint(["content_id"], ["entity_contents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("generated_images") as batch_op:
        batch_op.create_index("ix_generated_images_entity_id", ["entity_id"])
        batch_op.create_index("ix_generated_images_collection_id", ["collection_id"])
        batch_op.create_index("ix_generated_images_content_id", ["content_id"])


def downgrade() -> None:
    with op.batch_alter_table("generated_images") as batch_op:
        batch_op.drop_index("ix_generated_images_content_id")
        batch_op.drop_index("ix_generated_images_collection_id")
        batch_op.drop_index("ix_generated_images_entity_id")
    op.drop_table("generated_images")
```

---

## Paso 7 — Frontend: tipos

```typescript
// frontend/src/types/image.ts

export type ImageStatus = "pending" | "confirmed" | "discarded";
export type ImageBackend = "mock" | "local" | "runpod";
export type PromptSource =
  | "content_direct"
  | "content_sentences"
  | "description"
  | "name_only";
export type PromptStrategy = "direct" | "first_sentences" | "entity_only";

export interface GenerateImageResponse {
  id: string;
  entity_id: string;
  collection_id: string;
  content_id: string | null;
  category: string;

  // Prompt
  visual_prompt: string;
  prompt_token_count: number;
  prompt_source: PromptSource;
  prompt_strategy: PromptStrategy;
  truncated: boolean;

  // Imagen
  image_url: string;
  image_path: string | null;
  filename: string | null;
  extension: string;
  width: number;
  height: number;

  // Generación
  backend: ImageBackend;
  seed: number;
  generation_ms: number;

  // Estado
  status: ImageStatus;
  created_at: string;
  confirmed_at: string | null;
  updated_at: string | null;
}

export interface GenerateImageRequest {
  content_id: string;
}
```

---

## Paso 8 — Frontend: API client

```typescript
// frontend/src/api/images.ts

import { apiFetch } from "./apiClient";
import type { GenerateImageResponse, GenerateImageRequest } from "../types/image";

export function generateImage(
  collectionId: string,
  entityId: string,
  data: GenerateImageRequest,
  signal?: AbortSignal,
): Promise<GenerateImageResponse> {
  return apiFetch<GenerateImageResponse>(
    `/collections/${collectionId}/entities/${entityId}/generate/image`,
    {
      method: "POST",
      body: JSON.stringify(data),
      signal,
    },
  );
}
```

---

## Paso 9 — Frontend: `ImagePreviewPage.tsx`

Página dedicada accesible desde el botón en `ContentCard`.  
Muestra: prompt base del `EntityContent` + prompt visual generado + imagen placeholder.

```typescript
// frontend/src/pages/ImagePreviewPage.tsx

import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Alert,
  Badge,
  Breadcrumb,
  Button,
  Card,
  Col,
  Row,
  Spinner,
} from "react-bootstrap";
import { generateImage } from "../api/images";
import { getContents } from "../api/contents";
import { getEntity, getCollection } from "../api";
import LoadingSpinner from "../components/LoadingSpinner";
import type { GenerateImageResponse } from "../types/image";
import type { Entity, Collection, EntityContent } from "../types";
import { parseApiError } from "../utils/errors";
import { CATEGORY_LABELS } from "../utils/constants";

const PROMPT_SOURCE_LABEL: Record<string, string> = {
  content_direct: "Descripción extendida (texto completo)",
  content_sentences: "Escena/Capítulo (primeras oraciones)",
  description: "Descripción de entidad (fallback)",
  name_only: "Solo nombre (sin contexto)",
};

const STRATEGY_LABEL: Record<string, string> = {
  direct: "Directo — el texto RAG se usa como descriptor",
  first_sentences: "Primeras oraciones — extrae el setting visual",
  entity_only: "Solo entidad — la narrativa no es visual",
};

export default function ImagePreviewPage() {
  const { collectionId, entityId, contentId } = useParams<{
    collectionId: string;
    entityId: string;
    contentId: string;
  }>();

  const [collection, setCollection] = useState<Collection | null>(null);
  const [entity, setEntity] = useState<Entity | null>(null);
  const [content, setContent] = useState<EntityContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<GenerateImageResponse | null>(null);
  const [error, setError] = useState<{
    variant: "warning" | "danger";
    text: string;
  } | null>(null);

  useEffect(() => {
    if (!collectionId || !entityId || !contentId) return;
    Promise.all([
      getCollection(collectionId),
      getEntity(collectionId, entityId),
      getContents(collectionId, entityId, { status: "confirmed" }),
    ])
      .then(([col, ent, contents]) => {
        setCollection(col);
        setEntity(ent);
        const found = contents.data.find((c) => c.id === contentId);
        setContent(found ?? null);
      })
      .catch(() => setError({ variant: "danger", text: "Error al cargar datos" }))
      .finally(() => setLoading(false));
  }, [collectionId, entityId, contentId]);

  async function handleGenerate() {
    if (!collectionId || !entityId || !contentId) return;
    setGenerating(true);
    setError(null);
    try {
      const res = await generateImage(collectionId, entityId, {
        content_id: contentId,
      });
      setResult(res);
    } catch (e) {
      setError(parseApiError(e, "Error al generar preview"));
    } finally {
      setGenerating(false);
    }
  }

  if (loading) return <LoadingSpinner />;

  return (
    <div className="lm-page">
      <Breadcrumb>
        <Breadcrumb.Item linkAs={Link} linkProps={{ to: "/" }}>
          Colecciones
        </Breadcrumb.Item>
        <Breadcrumb.Item
          linkAs={Link}
          linkProps={{ to: `/collections/${collectionId}` }}
        >
          {collection?.name ?? collectionId}
        </Breadcrumb.Item>
        <Breadcrumb.Item
          linkAs={Link}
          linkProps={{
            to: `/collections/${collectionId}/entities/${entityId}`,
          }}
        >
          {entity?.name ?? entityId}
        </Breadcrumb.Item>
        <Breadcrumb.Item active>Preview imagen</Breadcrumb.Item>
      </Breadcrumb>

      <h2 className="mb-4">Preview de imagen</h2>

      {error && (
        <Alert variant={error.variant} onClose={() => setError(null)} dismissible>
          {error.text}
        </Alert>
      )}

      <Row className="g-4">
        {/* ── Panel izquierdo: contexto del contenido base ── */}
        <Col md={6}>
          <p className="lm-section-title">Contenido base</p>

          {content ? (
            <Card>
              <Card.Header className="d-flex gap-2 align-items-center">
                <Badge bg="dark">
                  {CATEGORY_LABELS[content.category as keyof typeof CATEGORY_LABELS]}
                </Badge>
                <Badge bg="success">Confirmado</Badge>
              </Card.Header>
              <Card.Body>
                <p
                  style={{
                    fontSize: "0.9rem",
                    color: "var(--lm-text-muted)",
                    fontStyle: "italic",
                    marginBottom: "0.75rem",
                  }}
                >
                  Query original: "{content.query}"
                </p>
                <div
                  style={{
                    maxHeight: 320,
                    overflowY: "auto",
                    fontSize: "0.9rem",
                    lineHeight: 1.7,
                    paddingRight: "0.5rem",
                  }}
                >
                  {content.content}
                </div>
              </Card.Body>
            </Card>
          ) : (
            <Alert variant="warning">
              No se encontró el contenido confirmado.
            </Alert>
          )}
        </Col>

        {/* ── Panel derecho: preview generado ── */}
        <Col md={6}>
          <p className="lm-section-title">Preview generado</p>

          {/* Imagen */}
          <div className="text-center mb-3">
            {result ? (
              <img
                src={result.image_url}
                alt={`Preview de ${entity?.name}`}
                style={{
                  width: "100%",
                  maxWidth: 340,
                  aspectRatio: "1/1",
                  borderRadius: "var(--lm-radius-lg)",
                  border: "1px solid var(--lm-border)",
                  objectFit: "cover",
                }}
              />
            ) : (
              <div
                style={{
                  width: "100%",
                  maxWidth: 340,
                  margin: "0 auto",
                  aspectRatio: "1/1",
                  border: "1px dashed var(--lm-border)",
                  borderRadius: "var(--lm-radius-lg)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <span className="text-muted" style={{ fontSize: "0.85rem" }}>
                  Sin preview todavía
                </span>
              </div>
            )}
          </div>

          {/* Botón generar */}
          <div className="d-flex justify-content-center mb-3">
            <Button
              variant="warning"
              onClick={handleGenerate}
              disabled={generating || !content}
            >
              {generating ? (
                <>
                  <Spinner animation="border" size="sm" className="me-2" />
                  Generando...
                </>
              ) : result ? (
                "↻ Regenerar preview"
              ) : (
                "✦ Generar preview"
              )}
            </Button>
          </div>

          {/* Metadatos del prompt */}
          {result && (
            <Card>
              <Card.Header>
                <div className="d-flex gap-2 flex-wrap">
                  <Badge bg="secondary">{result.backend.toUpperCase()}</Badge>
                  {result.truncated && (
                    <Badge bg="warning" text="dark">
                      prompt truncado
                    </Badge>
                  )}
                  <Badge
                    style={{
                      background: "var(--lm-accent-glow)",
                      color: "var(--lm-accent)",
                      border: "1px solid var(--lm-border-accent)",
                    }}
                  >
                    ~{result.prompt_token_count} tokens
                  </Badge>
                </div>
              </Card.Header>
              <Card.Body>
                {/* Estrategia aplicada */}
                <div className="mb-3">
                  <small className="text-muted d-block mb-1">
                    Estrategia de extracción
                  </small>
                  <small>
                    {STRATEGY_LABEL[result.prompt_strategy] ?? result.prompt_strategy}
                  </small>
                </div>

                {/* Fuente del contexto */}
                <div className="mb-3">
                  <small className="text-muted d-block mb-1">
                    Contexto utilizado
                  </small>
                  <small>
                    {PROMPT_SOURCE_LABEL[result.prompt_source] ?? result.prompt_source}
                  </small>
                </div>

                {/* Prompt visual generado */}
                <div>
                  <small className="text-muted d-block mb-1">
                    Prompt visual generado
                  </small>
                  <code
                    style={{
                      display: "block",
                      fontSize: "0.78rem",
                      background: "rgba(255,255,255,0.03)",
                      border: "1px solid var(--lm-border)",
                      borderRadius: "var(--lm-radius)",
                      padding: "0.65rem",
                      lineHeight: 1.6,
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                      color: "var(--lm-text-muted)",
                    }}
                  >
                    {result.visual_prompt}
                  </code>
                </div>
              </Card.Body>
            </Card>
          )}
        </Col>
      </Row>
    </div>
  );
}
```

---

## Paso 10 — Botón en `ContentCard.tsx`

Añadir solo en el bloque `isConfirmed`. El botón navega a la página de preview:

```tsx
// En ContentCard.tsx — dentro del bloque isConfirmed del Card.Footer
// Añadir después del botón "Editar":

import { useNavigate } from "react-router-dom";

// En el componente:
const navigate = useNavigate();

// En el JSX del footer confirmed:
<Button
  variant="outline-secondary"
  size="sm"
  onClick={() =>
    navigate(
      `/collections/${collectionId}/entities/${entityId}/contents/${content.id}/image-preview`
    )
  }
  disabled={busy}
  title="Generar preview de imagen basado en este contenido"
>
  ✦ Preview imagen
</Button>
```

---

## Paso 11 — Nueva ruta en `App.tsx`

```tsx
// En App.tsx — dentro del bloque <Route element={<Layout />}>

import ImagePreviewPage from "./pages/ImagePreviewPage";

<Route
  path="/collections/:collectionId/entities/:entityId/contents/:contentId/image-preview"
  element={<ImagePreviewPage />}
/>
```

---

## Resumen de tokens por tipo de contenido

```
extended_description  → strategy: direct
  [PREFIX: portrait]  ~14t  +  [nombre]  ~3t  +  [texto RAG directo]  ~35t  +  [SUFFIX]  ~10t
  = ~62 tokens  ✓ dentro del objetivo ≤75

backstory             → strategy: entity_only
  [PREFIX: dramatic]  ~15t  +  [nombre]  ~3t  +  [descripción entidad]  ~20t  +  [SUFFIX]  ~10t
  = ~48 tokens  ✓ bien por debajo del objetivo

scene                 → strategy: first_sentences (2 oraciones)
  [PREFIX: action]    ~14t  +  [nombre]  ~3t  +  [2 oraciones]  ~25t  +  [SUFFIX]  ~10t
  = ~52 tokens  ✓ dentro del objetivo

chapter               → strategy: first_sentences (1 oración)
  [PREFIX: epic]      ~13t  +  [nombre]  ~3t  +  [1 oración]   ~15t  +  [SUFFIX]  ~10t
  = ~41 tokens  ✓ muy por debajo del objetivo
```

---

## Preparación para Opción B (próximo sprint)

Los comentarios `# [OPTION_B]` en el código marcan exactamente dónde intervenir:

| Archivo | Línea marcada | Qué hacer en sprint siguiente |
|---------|--------------|-------------------------------|
| `prompt_builder.py` | `# [OPTION_B] llm_instruction:` en cada categoría | Implementar `invoke_prompt_extraction_pipeline()` que recibe texto + instrucción y retorna descriptores visuales |
| `prompt_builder.py` | `# [OPTION_B] parámetro use_llm_extraction` | Añadir flag al `build_visual_prompt()` |
| `image_generation_service.py` | `# [OPTION_B] image_bytes = await invoke_comfy_pipeline(...)` | Conectar cliente ComfyUI local o RunPod |
| `image_generation_service.py` | `# [OPTION_B] medir tiempo real` | Capturar `generation_ms` real |
| `config.py` | `image_backend: str = "mock"` | Cambiar a `"local"` o `"runpod"` según entorno |

---

## Archivos finales a tocar

### Backend
```
backend/app/core/config.py
backend/app/domain/prompt_builder.py          ← NUEVO (reemplaza versión anterior)
backend/app/models/image_generation.py        ← NUEVO (reemplaza versión anterior)
backend/app/models/__init__.py                ← añadir ImageRecord
backend/app/services/image_generation_service.py  ← NUEVO (reemplaza)
backend/app/api/routes/image_generation.py    ← NUEVO (reemplaza)
backend/app/main.py                           ← registrar router
backend/alembic/versions/xxxx_add_generated_images.py  ← NUEVO
backend/.env.example                          ← MEDIA_ROOT
backend/tests/test_prompt_builder.py          ← REFACTOR
backend/tests/test_image_generation.py        ← REFACTOR
```

### Frontend
```
frontend/src/types/image.ts                   ← NUEVO (reemplaza)
frontend/src/api/images.ts                    ← NUEVO (reemplaza)
frontend/src/pages/ImagePreviewPage.tsx        ← NUEVO
frontend/src/components/ContentCard.tsx        ← añadir botón en confirmed
frontend/src/App.tsx                           ← nueva ruta
frontend/src/types/index.ts                    ← exportar image.ts
frontend/src/api/index.ts                      ← exportar images.ts
```

---

## Tiempo estimado

| Tarea | Tiempo |
|-------|--------|
| `prompt_builder.py` refactor | 40 min |
| `image_generation.py` modelo + schemas | 20 min |
| `image_generation_service.py` | 30 min |
| Route + main | 10 min |
| Migración Alembic | 15 min |
| Tests backend refactor | 40 min |
| `ImagePreviewPage.tsx` | 50 min |
| `ContentCard.tsx` botón | 10 min |
| `App.tsx` ruta | 5 min |
| Tipos + API client frontend | 10 min |
| **Total** | **~3.5 horas** |
