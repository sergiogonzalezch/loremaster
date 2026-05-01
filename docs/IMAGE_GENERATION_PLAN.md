# Plan: Sistema de Generación de Imágenes

**Versión:** 2.0  
**Fecha:** 2026-04-30  
**Estado:** Listo para implementación  

---

## Decisiones de diseño

| Decisión | Resolución |
|----------|------------|
| Nomenclatura | Todo se llama `image_generation`, eliminar "preview" |
| Construcción del prompt | Opción A — endpoint separado en backend, lógica solo en Python |
| Persistencia mock | El backend `mock` NO persiste nada — respuesta efímera |
| Persistencia real | Solo se guarda `ImageRecord` cuando hay imagen real (ComfyUI) |
| Auditoría del prompt | Se guardan `auto_prompt` y `final_prompt` por separado |
| Almacenamiento de imagen | Campo `storage_path` con ruta relativa — URL se construye en runtime |
| Ciclo de vida imágenes | Sin confirmar — el usuario borra directamente las que no quiere |
| Batch de generación | 1 a 4 imágenes por llamada, default 4, seeds diferentes |
| `prompt_strategy` | Solo en response del `build-prompt`, no se persiste en DB |
| `prompt_source` | Se persiste como código corto, el frontend muestra texto descriptivo |
| Página de generación | Su propia ruta — `ImageGenerationPage.tsx` |

---

## Modelos de datos

### Tabla `image_generations` — una por batch

```
id               PK UUID
entity_id        FK entities, index
collection_id    FK collections, index
content_id       FK entity_contents, index

category         str(50)         — categoría del EntityContent base

auto_prompt      str(1000)       — lo que construyó prompt_builder
final_prompt     str(1000)       — lo que aprobó/editó el usuario
prompt_token_count  int
prompt_source    str(50)         — extended | scene | entity_desc | name_only
truncated        bool

batch_size       int             — 1 a 4, lo que pidió el usuario
backend          str(20)         — mock | local | runpod

created_at       datetime
is_deleted       bool
deleted_at       datetime nullable
```

### Tabla `image_records` — una por imagen dentro del batch

```
id               PK UUID
generation_id    FK image_generations, index
entity_id        FK entities, index       — desnormalizado para queries
collection_id    FK collections, index    — desnormalizado para queries

seed             int             — diferente por imagen dentro del batch
storage_path     str(500)        — ruta relativa: {collection_id}/{entity_id}/{generation_id}/{id}.png
filename         str(255)
extension        str(10)         — png
width            int             — 1024
height           int             — 1024
generation_ms    int

created_at       datetime
is_deleted       bool
deleted_at       datetime nullable
```

### Relación entre tablas

```
collections
    └── entities
            └── entity_contents (confirmed)
                        └── image_generations   ← un registro por batch
                                    └── image_records  ← 1 a 4 por generación
```

### Storage path y construcción de URL

```
DB guarda:
  storage_path = "{collection_id}/{entity_id}/{generation_id}/{image_id}.png"

config.py tiene:
  storage_backend  = "local"     # local | s3 | r2
  storage_base_url = "http://localhost:8000/media"

Response construye dinámicamente:
  image_url = f"{settings.storage_base_url}/{record.storage_path}"
```

Cuando se migre a S3 o R2 solo cambia `STORAGE_BASE_URL` en `.env`.  
El dato en DB no se toca.

---

## `prompt_source` — códigos y textos

| Código en DB | Texto para el usuario (frontend) |
|-------------|----------------------------------|
| `extended` | Basado en la descripción extendida de la entidad |
| `scene` | Basado en la escena o capítulo generado |
| `entity_desc` | Basado en la descripción general de la entidad |
| `name_only` | Solo el nombre — la entidad no tiene suficiente contexto |

---

## Estrategia del prompt builder por categoría

Basada en `domain/prompt_templates.py` y `domain/category_rules.py`.

| Categoría | Qué genera el LLM de texto | Estrategia visual | `prompt_source` resultante |
|-----------|---------------------------|-------------------|---------------------------|
| `extended_description` | Rasgos físicos, apariencia, características | `direct` — el texto ya es un descriptor visual | `extended` |
| `backstory` | Narrativa de orígenes en prosa | `entity_only` — ignorar el texto, usar descripción de entidad | `entity_desc` o `name_only` |
| `scene` | Ambientación, acción, diálogo | `first_sentences` — primeras 2 oraciones tienen el setting | `scene` |
| `chapter` | Narrativa larga estructurada | `first_sentences` — solo la oración de apertura | `scene` |

### Límites de tokens

```
target:  ≤ 75 tokens   — objetivo ideal
máximo:  ≤ 150 tokens  — hard limit
```

### Preparación para Opción B (siguiente sprint)

Cada estrategia en `prompt_builder.py` debe incluir un comentario `# [OPTION_B]`
con la instrucción LLM exacta que se usará para extracción semántica cuando se
implemente la integración con el LLM para construir prompts más precisos.

Ejemplo del comentario a dejar:
```python
# [OPTION_B] llm_instruction: "Del siguiente texto extrae solo los descriptores
# físicos y visuales. Formato: adjetivo sustantivo separados por coma.
# Máximo 15 palabras."
```

---

## Flujo completo

```
PASO 1 — Entrar a la página de generación
  ContentCard (status=confirmed)
    → botón "Generar imagen"
    → navega a /collections/:id/entities/:eid/contents/:cid/image-generation
    → al cargar la página: POST /build-prompt { content_id }
    → backend ejecuta prompt_builder según category + entity_type
    → devuelve: { auto_prompt, prompt_source, prompt_strategy, token_count, truncated }
    → frontend muestra auto_prompt en textarea editable
    → frontend muestra prompt_source con texto descriptivo para el usuario
    → frontend muestra selector de batch_size [ 1 | 2 | 3 | 4 ] default 4
    → nada se guarda en DB todavía

PASO 2 — Generar batch
    → usuario edita el prompt si quiere
    → botón "Generar"
    → POST /generate { content_id, final_prompt, batch_size }
    → backend:
        [mock]    devuelve N placeholders — NO guarda en DB
        [ComfyUI] genera N imágenes con seeds distintos
                  guarda image_generations + N image_records
                  guarda archivos en media/{collection_id}/{entity_id}/{generation_id}/
    → frontend muestra grid de N imágenes

PASO 3 — Curar el batch
    → usuario ve las imágenes generadas
    → botón "Borrar" en cada imagen → DELETE directo → is_deleted = true
    → las que no borra quedan persistidas
    → botón "Generar más" → vuelve al Paso 2 con el mismo prompt editable
    → puede editar el prompt entre batches
```

---

## Endpoints

### `POST /collections/{id}/entities/{eid}/image-generation/build-prompt`
Construye el prompt automático sin guardar nada.

**Request:**
```json
{ "content_id": "uuid" }
```

**Response:**
```json
{
  "auto_prompt": "fantasy character portrait...",
  "prompt_source": "extended",
  "prompt_source_label": "Basado en la descripción extendida de la entidad",
  "prompt_strategy": "direct",
  "token_count": 62,
  "truncated": false
}
```

---

### `POST /collections/{id}/entities/{eid}/image-generation/generate`
Genera el batch de imágenes. Con mock devuelve placeholders sin guardar.
Con ComfyUI genera y persiste.

**Request:**
```json
{
  "content_id": "uuid",
  "final_prompt": "fantasy character portrait, editado por usuario...",
  "batch_size": 4
}
```

**Response:**
```json
{
  "generation_id": "uuid",
  "auto_prompt": "fantasy character portrait...",
  "final_prompt": "fantasy character portrait, editado...",
  "prompt_source": "extended",
  "prompt_source_label": "Basado en la descripción extendida de la entidad",
  "batch_size": 4,
  "backend": "mock",
  "images": [
    {
      "id": "uuid",
      "image_url": "http://localhost:8000/media/...",
      "seed": 42,
      "width": 1024,
      "height": 1024,
      "generation_ms": 0
    }
  ]
}
```

---

### `DELETE /collections/{id}/entities/{eid}/image-generation/{generation_id}/images/{image_id}`
Borra una imagen individual del batch. Soft delete.

**Response:** 204 No Content

---

## Archivos a crear y modificar

### Backend — nuevos
```
backend/app/models/image_generation.py
backend/app/services/image_generation_service.py
backend/app/api/routes/image_generation.py
backend/app/domain/prompt_builder.py              ← reemplaza versión anterior
backend/alembic/versions/xxxx_add_image_generation_tables.py
backend/tests/test_prompt_builder.py              ← reemplaza versión anterior
backend/tests/test_image_generation.py            ← reemplaza versión anterior
```

### Backend — modificados
```
backend/app/core/config.py       ← storage_backend, storage_base_url,
                                    image_prompt_max_tokens, image_prompt_target_tokens,
                                    image_backend, image_batch_size_default
backend/app/models/__init__.py   ← importar ImageGeneration, ImageRecord
backend/app/main.py              ← registrar router image_generation
backend/.env.example             ← STORAGE_BACKEND, STORAGE_BASE_URL, IMAGE_BACKEND
```

### Frontend — nuevos
```
frontend/src/api/imageGeneration.ts
frontend/src/types/imageGeneration.ts
frontend/src/pages/ImageGenerationPage.tsx        ← reemplaza ImagePreviewPage.tsx
```

### Frontend — modificados
```
frontend/src/components/ContentCard.tsx   ← renombrar botón, ajustar navigate URL
frontend/src/App.tsx                      ← renombrar ruta a image-generation
frontend/src/types/index.ts               ← exportar imageGeneration.ts
frontend/src/api/index.ts                 ← exportar imageGeneration.ts
```

### Frontend — eliminar
```
frontend/src/pages/ImagePreviewPage.tsx   ← reemplazada por ImageGenerationPage.tsx
frontend/src/api/images.ts                ← reemplazada por imageGeneration.ts
frontend/src/types/image.ts               ← reemplazada por imageGeneration.ts
frontend/src/components/ImagePreviewCard.tsx ← ya no aplica, lógica en la página
```

---

## Tipos TypeScript — `imageGeneration.ts`

```typescript
export type ImageBackend = "mock" | "local" | "runpod";
export type PromptSource = "extended" | "scene" | "entity_desc" | "name_only";
export type PromptStrategy = "direct" | "first_sentences" | "entity_only";

export const PROMPT_SOURCE_LABEL: Record<PromptSource, string> = {
  extended:    "Basado en la descripción extendida de la entidad",
  scene:       "Basado en la escena o capítulo generado",
  entity_desc: "Basado en la descripción general de la entidad",
  name_only:   "Solo el nombre — la entidad no tiene suficiente contexto",
};

export interface BuildPromptRequest {
  content_id: string;
}

export interface BuildPromptResponse {
  auto_prompt: string;
  prompt_source: PromptSource;
  prompt_source_label: string;
  prompt_strategy: PromptStrategy;
  token_count: number;
  truncated: boolean;
}

export interface GenerateImagesRequest {
  content_id: string;
  final_prompt: string;
  batch_size: number;        // 1-4
}

export interface ImageResult {
  id: string;
  image_url: string;
  seed: number;
  width: number;
  height: number;
  generation_ms: number;
  is_deleted: boolean;
}

export interface GenerateImagesResponse {
  generation_id: string;
  auto_prompt: string;
  final_prompt: string;
  prompt_source: PromptSource;
  prompt_source_label: string;
  batch_size: number;
  backend: ImageBackend;
  images: ImageResult[];
}
```

---

## Variables de entorno nuevas

```bash
# Storage
STORAGE_BACKEND=local           # local | s3 | r2
STORAGE_BASE_URL=http://localhost:8000/media

# Image generation
IMAGE_BACKEND=mock              # mock | local | runpod
IMAGE_PROMPT_MAX_TOKENS=150
IMAGE_PROMPT_TARGET_TOKENS=75
IMAGE_BATCH_SIZE_DEFAULT=4
```

---

## Notas para implementación real (ComfyUI — siguiente sprint)

- Seeds: generar de forma determinista por batch para reproducibilidad
  - Ejemplo: `seed_n = base_seed + n` donde `base_seed` es aleatorio por generación
- Al borrar todas las imágenes de un `image_generation`, el registro padre
  queda huérfano — se mantiene como auditoría, no se borra en cascade
- `generation_ms` real se mide desde que se envía a ComfyUI hasta recibir respuesta
- Crear carpeta `media/{collection_id}/{entity_id}/{generation_id}/` antes de guardar
- Si ComfyUI falla a mitad del batch, las imágenes ya guardadas se mantienen
- El campo `backend` en `image_generations` registra con qué backend se generó
  realmente — útil para comparar tiempos local vs runpod

---

## Tiempo estimado

| Tarea | Tiempo |
|-------|--------|
| Migración Alembic (2 tablas) | 20 min |
| `config.py` | 10 min |
| `prompt_builder.py` refactor | 45 min |
| `image_generation_service.py` | 40 min |
| Route + endpoints | 20 min |
| Tests backend | 50 min |
| Tipos TypeScript | 15 min |
| API client frontend | 15 min |
| `ImageGenerationPage.tsx` | 60 min |
| `ContentCard.tsx` ajustes | 10 min |
| `App.tsx` ruta + limpiar archivos viejos | 10 min |
| **Total** | **~4.5 horas** |
