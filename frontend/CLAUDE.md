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
├── api/                  # apiClient, collections, documents, entities, contents, generate, imageGeneration
├── components/           # Layout, ContentCard, ConfirmModal, StarfieldCanvas, etc.
├── hooks/               # useGenerate, useEntityContents, useCollectionDocumentsStatus
├── pages/                # Collections, CollectionDetail, EntityDetail, Generate
├── types/                # TypeScript schemas (mirror backend)
└── utils/                # enums, constants, errors (ES), formatters, tokens
```

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
**Documentation:** [../docs/DOCUMENTATION.md](../docs/DOCUMENTATION.md)
**Skills:** [SKILLS.md](./SKILLS.md)
