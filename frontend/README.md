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

| Script                  | Descripción                                        |
| ----------------------- | -------------------------------------------------- |
| `npm run dev`           | Servidor de desarrollo con HMR en `localhost:5173` |
| `npm run build`         | Type-check + bundle de producción en `dist/`       |
| `npm run lint`          | ESLint sobre todo el proyecto                      |
| `npm run preview`       | Sirve el build de producción localmente            |
| `npm test`              | Vitest en modo watch                               |
| `npm run test:coverage` | Cobertura de tests (proveedor v8, reporte CLI)     |

## Estructura del proyecto

```
src/
├── api/
│   ├── apiClient.ts        → apiFetch<T> con ApiError / ApiAbortError
│   ├── auth.ts             → login() / register() — POST /auth/login y /auth/register
│   ├── collections.ts      → CRUD de colecciones
│   ├── documents.ts        → upload (FormData), listado y eliminación de documentos
│   ├── entities.ts         → CRUD de entidades
│   ├── contents.ts         → generate / list / edit / confirm / discard / share / delete EntityContent
│   ├── generate.ts         → consulta RAG libre (POST /collections/{id}/query)
│   ├── imageGeneration.ts  → buildPrompt / generate / list / get / shareImage / deleteImage
│   ├── users.ts            → getMyProfile() / updateMyProfile() / getPublicProfile() / getPublicFeed() / getPublicImages()
│   ├── query.ts            → buildQuery() — utilidad para construir query strings de URL
│   └── index.ts            → barrel export (no incluye query.ts — uso interno)
├── components/
│   ├── ContentCard.tsx        → Card de EntityContent con acciones según estado
│   ├── ConfirmModal.tsx       → Modal de confirmación reutilizable
│   ├── Layout.tsx             → Navbar con username del usuario autenticado + Outlet + StarfieldCanvas
│   ├── LoadingSpinner.tsx     → Spinner centrado con texto opcional
│   ├── MarkdownContent.tsx    → Renderizado markdown sanitizado
│   ├── ProtectedRoute.tsx     → Guard: redirige a /login si useAuth().user es null
│   ├── PublicContentModal.tsx → Modal de lectura completa de EntityContent compartido (markdown, badges, owner link)
│   ├── PublicImageModal.tsx   → Modal de imagen compartida: imagen, seed, prompts, descarga
│   ├── StarfieldCanvas.tsx    → Fondo animado canvas: estrellas de fondo + estrellas de colecciones (evento lm:collections) + estrellas fugaces
│   └── TokenCounter.tsx       → Estimación de tokens (aviso a los 400)
├── contexts/
│   └── AuthContext.tsx     → AuthProvider + AuthContext: estado global del usuario decodificado del JWT
├── hooks/
│   ├── useAuth.ts                      → Acceso al contexto de autenticación (lanza si se usa fuera de AuthProvider)
│   ├── useCollectionDocumentsStatus.ts → Monitoriza estado de documentos; refresca automáticamente cada 3s si hay documentos procesando
│   ├── useDebouncedValue.ts            → Debounce de un valor con delay configurable (default 300 ms)
│   ├── useEntityContents.ts            → Fetching/refresco de contenidos de una entidad
│   └── useGenerate.ts                  → Wrapper cancellable para llamadas LLM (AbortSignal)
├── pages/
│   ├── LoginPage.tsx             → Formulario login/registro con tabs; redirige a / tras autenticar
│   ├── CollectionsPage.tsx       → Listado, creación y eliminación de colecciones propias
│   ├── CollectionDetailPage.tsx  → Tabs: Documentos / Entidades / Generar texto
│   ├── EntityDetailPage.tsx      → Detalle de entidad + generación de contenido por categoría
│   ├── GeneratePage.tsx          → Consulta RAG libre contra una colección
│   ├── ProfilePage.tsx           → Perfil propio editable: display_name, bio, avatar_url, email
│   ├── PublicFeedPage.tsx        → Feed público: galería de imágenes compartidas + cards de contenido paginadas (abre modales al hacer clic)
│   └── PublicProfilePage.tsx     → Perfil público de un usuario: galería de imágenes + cards de contenido compartido (abre modales al hacer clic)
├── types/
│   ├── collection.ts       → Collection (incluye owner_id), CreateCollectionRequest, CollectionListResponse
│   ├── content.ts           → EntityContent, PaginatedResponse<T>, request types
│   ├── document.ts          → Document, DocumentListResponse
│   ├── entity.ts            → Entity, CreateEntityRequest, UpdateEntityRequest, EntityListResponse
│   ├── generate.ts          → GenerateTextRequest, GenerateTextResponse
│   ├── imageGeneration.ts   → BuildPromptRequest/Response, GenerateImagesRequest/Response, ImageGenerationItem, ImageRecordData
│   ├── user.ts              → UserProfile, UpdateProfileRequest, SharedContentItem, PublicFeedItem, SharedImageItem, PublicImageItem, PublicProfile
│   └── index.ts             → barrel export
├── test/
│   ├── setup.ts                              → Configura @testing-library/jest-dom globalmente
│   ├── errors.test.ts                        → getErrorMessage + parseApiError
│   ├── tokens.test.ts                        → estimateTokens + QUERY_TOKEN_WARN_AT
│   ├── formatters.test.ts                    → formatDate
│   ├── constants.test.ts                     → ENTITY_CATEGORY_MAP, badges, labels, límites
│   ├── ConfirmModal.test.tsx                 → Render, show/hide, callbacks, variante
│   ├── TokenCounter.test.tsx                 → Conteo, umbral de advertencia, warnAt custom
│   ├── MarkdownContent.test.tsx              → Sanitización XSS: script, onerror, javascript:, markdown estándar
│   ├── ContentCard.test.tsx                  → Estados pending/confirmed/discarded, busy-lock, rollback optimista
│   ├── CollectionsPage.test.tsx              → CRUD colecciones, modal, paginación auto-back
│   ├── CollectionDetailPage.test.tsx         → Tabs documentos/entidades, estados de carga
│   ├── EntityDetailPage.test.tsx             → Generación, límite borradores, error 404
│   ├── GeneratePage.test.tsx                 → Consulta RAG libre, errores 422/503
│   ├── useGenerate.test.ts                   → run, cancel, reset, AbortSignal, doble llamada
│   ├── useEntityContents.test.ts             → fetch, loading, error, filtros, setError
│   ├── useCollectionDocumentsStatus.test.ts  → Polling lifecycle: inicio, activo, se detiene, ApiAbortError
│   └── useDebouncedValue.test.ts             → valor inicial, delay no cumplido, delay cumplido
└── utils/
    ├── constants.ts   → ENTITY_TYPE_BADGE/LABELS, ENTITY_CATEGORY_MAP, CATEGORY_LABELS,
    │                    MAX_PENDING_CONTENTS, constantes de tokens
    ├── enums.ts       → DocumentStatus, EntityType, ContentCategory, ContentStatus
    ├── errors.ts      → getErrorMessage(), parseApiError() — mensajes en español
    ├── formatters.ts  → formatDate() locale es-ES
    └── tokens.ts      → estimateTokens(), QUERY_TOKEN_WARN_AT
```

## Tests

**Stack:** Vitest 3 + @testing-library/react 16 + happy-dom 15.

Los tests se encuentran en `src/test/`. Las llamadas a la API se mockean con `vi.mock()`, sin MSW.

| Categoría   | Archivos                                                                        | Tests |
| ----------- | ------------------------------------------------------------------------------- | ----- |
| Utilidades  | errors, tokens, formatters, constants                                           | 26    |
| Componentes | ConfirmModal, TokenCounter, ContentCard, MarkdownContent                        | 28    |
| Hooks       | useGenerate, useEntityContents, useDebouncedValue, useCollectionDocumentsStatus | 23    |
| Páginas     | CollectionsPage, CollectionDetailPage, EntityDetailPage, GeneratePage           | 41    |

**Total: 118 tests.**

Aspectos destacados de cobertura:

- **`ContentCard`**: estados pending/confirmed/discarded, busy-lock (doble clic bloqueado), rollback optimista en fallo de API, badge de auditoría `✎ editado`.
- **`MarkdownContent`**: sanitización XSS — `<script>`, `onerror`, `javascript:` href bloqueados; markdown estándar y `https://` permitidos.
- **`useCollectionDocumentsStatus`**: polling activo cuando hay documentos `processing`; polling detenido automáticamente cuando todos salen de ese estado; `ApiAbortError` no actualiza estado.
- **`CollectionsPage`**: paginación auto-back cuando la página actual queda vacía tras eliminación.
- **`EntityDetailPage`**: alerta de error en carga 404, formulario de generación, límite de borradores.

## Autenticación

Flujo JWT local. Al iniciar la app, `AuthProvider` decodifica el token almacenado en `localStorage` y expone el usuario vía contexto. `ProtectedRoute` usa `useAuth().user` para redirigir a `/login` si no hay sesión activa.

- **Login**: `POST /api/v1/auth/login` → guarda `access_token` en `localStorage`.
- **Registro**: `POST /api/v1/auth/register` → crea cuenta y devuelve token directamente (login implícito).
- El token se adjunta en todas las peticiones via cabecera `Authorization: Bearer <token>` dentro de `apiFetch`.
- **`AuthContext` / `useAuth`**: estado global del usuario (`{ id, username }`). `AuthProvider` envuelve toda la app en `App.tsx`. `useAuth()` lanza si se llama fuera del provider.
- **`logout()`**: expuesto por `useAuth()`; elimina el token de `localStorage` y limpia el estado del contexto.
- Utilidades de bajo nivel en `src/utils/token.ts`: `getToken()`, `setToken()`, `removeToken()` — usadas por `AuthProvider` y `apiFetch`, no directamente por componentes.

## Pantallas

| Ruta                             | Página            | Auth | Descripción                                                                                                                                     |
| -------------------------------- | ----------------- | ---- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `/login`                         | Login / Registro  | No   | Formulario con tabs "Iniciar sesión" / "Registrarse"; redirige a `/` tras autenticar                                                            |
| `/`                              | Colecciones       | Sí   | Cards con todas las colecciones; crear (modal) o eliminar con confirmación                                                                      |
| `/collections/:id`               | Detalle colección | Sí   | **Documentos**: upload PDF/TXT, tabla con estado; **Entidades**: tabla con badges, navegación al detalle; **Generar texto**: consulta RAG libre |
| `/collections/:id/entities/:eid` | Detalle entidad   | Sí   | Card de entidad editable; formulario de generación; lista de `ContentCard`; generación de imágenes                                              |
| `/collections/:id/generate`      | Generar texto     | Sí   | Consulta RAG libre con manejo de errores 422/503                                                                                                |
| `/profile`                       | Mi perfil         | Sí   | Formulario para editar display_name, bio, avatar_url y email del usuario autenticado                                                            |
| `/public`                        | Feed público      | No   | Galería de imágenes compartidas + cards de contenido paginadas; clic abre modal de lectura completa                                             |
| `/users/:username`               | Perfil público    | No   | Perfil de cualquier usuario: galería de imágenes + contenidos compartidos con modal                                                             |

## Contenido público y perfiles

Las colecciones son siempre privadas. El contenido individual (textos narrativos e imágenes) se puede compartir de forma selectiva mediante un toggle `is_shared`. El contenido compartido aparece en dos superficies públicas sin autenticación:

- **`/public`** — Feed global paginado: sección de imágenes (thumbnails clicables) + cards de textos con preview. Clic abre modal de lectura completa (`PublicContentModal`) o modal de imagen (`PublicImageModal`).
- **`/users/:username`** — Perfil público de un usuario: galería de imágenes compartidas + cards de contenidos. Mismo comportamiento de modales.

`PublicImageModal` muestra la imagen a tamaño completo, seed, fecha, `auto_prompt`, `final_prompt` y botón de descarga. `PublicContentModal` muestra el texto completo en Markdown con badges de categoría/tipo y link al perfil del autor.

## Generación de imágenes

Flujo de dos pasos para generar imágenes de entidades:

1. **build-prompt** → `POST .../image-generation/build-prompt`: Genera el `auto_prompt` (prompt visual LLM) a partir de un contenido confirmado de la entidad.
2. **generate** → `POST .../image-generation/generate`: Genera imágenes usando el `auto_prompt` del frontend + `final_prompt` del usuario. No hay regeneración en backend.

El componente `ImageGenerator.tsx` orquesta este flujo: construye el prompt visual, permite editar `final_prompt`, y genera batches de 1-4 imágenes. Cada imagen individual se puede compartir/descompartir desde la galería (`ImageGallery.tsx`) o desde `ImagePanel.tsx`.

## Ciclo de vida de EntityContent

| Estado      | Acciones disponibles                      |
| ----------- | ----------------------------------------- |
| `pending`   | Confirmar · Editar · Descartar · Eliminar |
| `confirmed` | Editar · Eliminar                         |
| `discarded` | — (solo visible en el historial)          |

- **Confirmar** → descarta el resto de contenidos pendientes **de la misma categoría**, sin descartar contenidos ya confirmados.
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
