# Lore Master — Frontend

SPA React para interactuar con la API de Lore Master. Permite gestionar colecciones de documentos, entidades narrativas y generar contenido con RAG por categoría.

## Stack

|           |                                                  |
| --------- | ------------------------------------------------ |
| Framework | React 19                                         |
| Lenguaje  | TypeScript 6 (strict)                            |
| Bundler   | Vite 8                                           |
| UI        | React Bootstrap 2 + Bootstrap 5                  |
| Routing   | React Router 7                                   |
| HTTP      | `fetch` nativo (sin axios)                       |
| Markdown  | react-markdown 10 (remark-gfm + rehype-sanitize) |

## Requisitos

- Node.js 18+
- Backend corriendo en `http://localhost:8000` (ver `../backend/README.md`)

## Instalación y ejecución

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173
```

## Variables de entorno

El archivo `.env` (opcional en local) permite sobreescribir la URL de la API:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

El proxy de Vite redirige `/api/*` → `http://localhost:8000` en desarrollo, evitando CORS sin configuración adicional. En producción, `VITE_API_BASE_URL` debe apuntar al backend desplegado.

## Scripts disponibles

| Script            | Descripción                                        |
| ----------------- | -------------------------------------------------- |
| `npm run dev`     | Servidor de desarrollo con HMR en `localhost:5173` |
| `npm run build`   | Type-check + bundle de producción en `dist/`       |
| `npm run lint`    | ESLint sobre todo el proyecto                      |
| `npm run preview` | Sirve el build de producción localmente            |

## Estructura del proyecto

```
src/
├── api/
│   ├── apiClient.ts        → apiFetch<T> con ApiError / ApiAbortError
│   ├── collections.ts      → CRUD de colecciones
│   ├── documents.ts        → upload (FormData), listado y eliminación de documentos
│   ├── entities.ts         → CRUD de entidades
│   ├── contents.ts         → generate / list / edit / confirm / discard / delete EntityContent
│   ├── generate.ts         → consulta RAG libre
│   └── index.ts            → barrel export
├── components/
│   ├── ContentCard.tsx     → Card de EntityContent con acciones según estado
│   ├── ConfirmModal.tsx    → Modal de confirmación reutilizable
│   ├── Layout.tsx          → Navbar + Outlet (React Router)
│   ├── LoadingSpinner.tsx  → Spinner centrado con texto opcional
│   ├── MarkdownContent.tsx → Renderizado markdown sanitizado
│   └── TokenCounter.tsx    → Estimación de tokens (aviso a los 400)
├── hooks/
│   ├── useEntityContents.ts → Fetching/refresco de contenidos de una entidad
│   └── useGenerate.ts       → Wrapper cancellable para llamadas LLM (AbortSignal)
├── pages/
│   ├── CollectionsPage.tsx       → Listado, creación y eliminación de colecciones
│   ├── CollectionDetailPage.tsx  → Tabs: Documentos / Entidades / Generar texto
│   ├── EntityDetailPage.tsx      → Detalle de entidad + generación de contenido por categoría
│   └── GeneratePage.tsx          → Consulta RAG libre contra una colección
├── types/
│   ├── collection.ts  → Collection, CreateCollectionRequest, CollectionListResponse
│   ├── content.ts     → EntityContent, PaginatedResponse<T>, request types
│   ├── document.ts    → Document, DocumentListResponse
│   ├── entity.ts      → Entity, CreateEntityRequest, UpdateEntityRequest, EntityListResponse
│   ├── generate.ts    → GenerateTextRequest, GenerateTextResponse
│   └── index.ts       → barrel export
└── utils/
    ├── constants.ts   → ENTITY_TYPE_BADGE/LABELS, ENTITY_CATEGORY_MAP, CATEGORY_LABELS,
    │                    MAX_PENDING_CONTENTS, constantes de tokens
    ├── enums.ts       → DocumentStatus, EntityType, ContentCategory, ContentStatus
    ├── errors.ts      → getErrorMessage(), parseApiError() — mensajes en español
    ├── formatters.ts  → formatDate() locale es-ES
    └── tokens.ts      → estimateTokens(), QUERY_TOKEN_WARN_AT
```

## Pantallas

| Ruta                             | Página            | Descripción                                                                                                                                     |
| -------------------------------- | ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `/`                              | Colecciones       | Cards con todas las colecciones; crear (modal) o eliminar con confirmación                                                                      |
| `/collections/:id`               | Detalle colección | **Documentos**: upload PDF/TXT, tabla con estado; **Entidades**: tabla con badges, navegación al detalle; **Generar texto**: consulta RAG libre |
| `/collections/:id/entities/:eid` | Detalle entidad   | Card de entidad editable; formulario de generación con selector de categoría; lista de `ContentCard`                                            |
| `/collections/:id/generate`      | Generar texto     | Consulta RAG libre con manejo de errores 422/503                                                                                                |

## Ciclo de vida de EntityContent

| Estado      | Acciones disponibles                      |
| ----------- | ----------------------------------------- |
| `pending`   | Confirmar · Editar · Descartar · Eliminar |
| `confirmed` | Editar · Eliminar                         |
| `discarded` | — (solo visible en el historial)          |

- **Confirmar** → descarta el resto de contenidos pendientes **de la misma categoría**.
- **Descartar** → `PATCH .../discard`, cambia el estado a `discarded`, el contenido sigue visible.
- **Eliminar** → soft-delete (`DELETE`), desaparece del listado.

## Sistema de categorías

Cada tipo de entidad tiene un conjunto de categorías válidas (espejo de `backend/app/domain/category_rules.py`):

| Tipo de entidad       | Categorías permitidas                                 |
| --------------------- | ----------------------------------------------------- |
| Personaje (character) | Trasfondo · Descripción extendida · Escena · Capítulo |
| Criatura (creature)   | Trasfondo · Descripción extendida · Escena            |
| Lugar (location)      | Descripción extendida · Escena                        |
| Facción (faction)     | Trasfondo · Descripción extendida · Escena            |
| Objeto (item)         | Trasfondo · Descripción extendida                     |

Límite: máximo **5 contenidos pendientes por entidad por categoría**.
