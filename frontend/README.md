# Lore Master — Frontend

SPA React para interactuar con la API de Lore Master. Permite gestionar colecciones de documentos, entidades narrativas y generar texto con RAG.

## Stack

| | |
|---|---|
| Framework | React 19 |
| Lenguaje | TypeScript 6 |
| Bundler | Vite 8 |
| UI | React Bootstrap 2 + Bootstrap 5 |
| Routing | React Router 7 |
| HTTP | `fetch` nativo (sin axios) |

## Requisitos

- Node.js 18+
- Backend corriendo en `http://localhost:8000` (ver `backend/README.md`)

## Instalación y ejecución

```bash
cd frontend
npm install
npm run dev
```

Disponible en `http://localhost:5173`.

## Variables de entorno

El archivo `.env` usa una URL relativa para que el proxy de Vite gestione las peticiones:

```env
VITE_API_BASE_URL=/api/v1
```

El proxy (`vite.config.ts`) redirige `/api/*` → `http://localhost:8000/api/*` en desarrollo, evitando problemas de CORS sin configuración adicional en el backend.

## Estructura del proyecto

```
src/
├── api/
│   ├── apiClient.ts        → apiFetch y apiUpload (fetch + error handling)
│   ├── collections.ts      → CRUD de colecciones
│   ├── documents.ts        → upload, listado y eliminación de documentos
│   ├── entities.ts         → CRUD de entidades
│   ├── drafts.ts           → generación, edición, confirmación, descarte y eliminación de borradores
│   ├── generate.ts         → consulta RAG libre
│   └── index.ts            → barrel export
├── types/
│   ├── collection.ts       → Collection, CreateCollectionRequest, CollectionListResponse
│   ├── document.ts         → Document, DocumentListResponse
│   ├── entity.ts           → Entity, CreateEntityRequest, UpdateEntityRequest, EntityListResponse
│   ├── draft.ts            → Draft, GenerateDraftRequest, UpdateDraftContentRequest, DraftListResponse
│   ├── generate.ts         → GenerateTextRequest, GenerateTextResponse
│   └── index.ts            → barrel export
├── utils/
│   └── enums.ts            → DocumentStatus, EntityType, DraftStatus
├── components/
│   ├── Layout.tsx          → Navbar + Outlet (React Router)
│   ├── ConfirmModal.tsx    → Modal de confirmación reutilizable
│   └── LoadingSpinner.tsx  → Spinner centrado con texto
└── pages/
    ├── CollectionsPage.tsx       → Listado, creación y eliminación de colecciones
    ├── CollectionDetailPage.tsx  → Tabs: Documentos / Entidades / Generar texto
    ├── EntityDetailPage.tsx      → Detalle de entidad + ciclo de vida de borradores
    └── GeneratePage.tsx          → Consulta RAG libre contra una colección
```

## Pantallas

| Ruta | Página | Descripción |
|---|---|---|
| `/` | Colecciones | Cards con todas las colecciones; crear nueva (modal) o eliminar con confirmación |
| `/collections/:id` | Detalle colección | Tab **Documentos**: upload PDF/TXT, tabla con estado y badges; Tab **Entidades**: tabla con badges por tipo, navegación al detalle; Tab **Generar texto**: consulta RAG libre |
| `/collections/:id/entities/:eid` | Detalle entidad | Card de entidad editable (PATCH); generador de borradores; lista de borradores con acciones según estado |
| `/collections/:id/generate` | Generar texto | Consulta RAG libre con manejo de errores 422 / 503 |

## Ciclo de vida de borradores

| Estado | Acciones disponibles |
|---|---|
| `pending` | Confirmar · Editar · Descartar · Eliminar |
| `discarded` | Eliminar |
| `confirmed` | — (solo muestra fecha de confirmación) |

- **Confirmar** → actualiza la descripción de la entidad y descarta el resto de borradores pendientes.
- **Descartar** → cambia el estado a `discarded` (`PATCH .../discard`), el borrador sigue visible.
- **Eliminar** → soft-delete real (`DELETE`), el borrador desaparece del listado.

## Scripts disponibles

| Script | Descripción |
|---|---|
| `npm run dev` | Servidor de desarrollo con HMR en `localhost:5173` |
| `npm run build` | Compilación TypeScript + bundle de producción en `dist/` |
| `npm run lint` | ESLint sobre todo el proyecto |
| `npm run preview` | Sirve el build de producción localmente |