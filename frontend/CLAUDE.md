# CLAUDE.md — Frontend

Quick reference. Full docs → [README.md](./README.md).

## Commands

```bash
npm install              # Install dependencies
npm run dev              # Vite dev server (localhost:5173)
npm run build            # Type-check + bundle
npm run lint             # ESLint
npm test                 # Vitest watch mode
npm run test:coverage    # Coverage report
```

## Stack

- React 19 + TypeScript 6 (strict) + Vite 8
- React Router 7 + React Bootstrap 5
- `fetch` nativo (sin axios)
- react-markdown 10

## Estructura clave

```
src/
├── api/
│   ├── client.ts         # apiFetch, ApiError, ApiAbortError
│   ├── factory.ts        # apiGet, apiPost, apiPatch, apiDelete helpers
│   ├── query.ts          # buildQuery
│   ├── index.ts          # Barrel exports
│   └── endpoints/         # collections, documents, entities, contents, etc.
├── components/
│   ├── common/            # PaginationControls, FilterBar, ConfirmModal, LoadingSpinner
│   ├── domain/            # ContentCard, EntityContentsPanel, ImagePanel
│   └── layout/            # Layout, AppNavbar
├── hooks/                # useGenerate, useEntityContents, useDeleteConfirm, usePagination, useApiError, useFormSubmit
├── pages/
│   └── CollectionDetailPage/  # Split into index, DocumentsTab, EntitiesTab, GenerateTab
├── types/                # TypeScript schemas (mirror backend)
└── utils/                # enums, constants, errors (ES), formatters, tokens
```

## Abstracciones DRY

- **PaginationControls**: Componente reutilizable de paginación
- **FilterBar** (`PageSizeSelect`, `OrderSelect`): Selectores de filtro
- **useApiError**: Hook para manejo de errores de API
- **useFormSubmit**: Hook para formularios con estado de guardado
- **api/factory.ts**: Helpers CRUD tipados (apiGet, apiPost, apiPatch, apiDelete)

## Image Generation

Flujo de dos pasos (ImageGenerator.tsx):

1. `buildPrompt(contentId)` → `POST /image-generation/build-prompt` → `auto_prompt`
2. `generate(auto_prompt, final_prompt, batch_size)` → `POST /image-generation/generate`

## Testing

- Vitest 3 + @testing-library/react 16 + happy-dom 15
- Tests en `src/test/`
- Mocks con `vi.mock('../api/<module>')`

---

**Full documentation:** [README.md](./README.md)
**Documentation:** [../docs/architecture/DOCUMENTATION.md](../docs/architecture/DOCUMENTATION.md)
**Skills:** [SKILLS.md](./SKILLS.md)
