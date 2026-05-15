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

El archivo `.env` (opcional en local) permite sobreescribir la URL de la API y activar el modo Clerk:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_CLERK_PUBLISHABLE_KEY=pk_test_...   # opcional: activa modo Clerk
```

El proxy de Vite redirige `/api/*` → `http://localhost:8000` en desarrollo, evitando CORS sin configuración adicional. En producción, `VITE_API_BASE_URL` debe apuntar al backend desplegado.

Si `VITE_CLERK_PUBLISHABLE_KEY` está definida, la app usa Clerk para autenticación: `ClerkProvider` envuelve la app, `LoginPage` muestra `<SignIn />` de Clerk y `ClerkBridge` sincroniza la sesión con el backend. Sin esta variable, la app usa el formulario de login/registro propio.

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
│   ├── apiClient.ts   → apiFetch<T> con ApiError / ApiAbortError; 401 → evento custom auth:unauthorized
│   ├── factory.ts     → apiGet, apiPost, apiPatch, apiDelete — helpers CRUD tipados
│   ├── query.ts       → buildQuery() — constructor de query strings de URL
│   ├── admin.ts       → listUsers() / deleteUser()
│   ├── auth.ts        → login() / register() / logoutApi()
│   ├── clerkSync.ts   → syncClerkSession(clerkToken) — POST /auth/clerk/sync con JWT en header
│   ├── collections.ts → CRUD de colecciones
│   ├── documents.ts   → upload (FormData), listado y eliminación de documentos
│   ├── entities.ts    → CRUD de entidades
│   ├── contents.ts    → generate / list / edit / confirm / discard / share / delete EntityContent
│   ├── generate.ts    → consulta RAG libre (POST /collections/{id}/query)
│   ├── images.ts      → buildPrompt / generate / list / get / shareImage / deleteImage
│   ├── metadata.ts    → getAvailableModels() y otros endpoints de metadatos
│   ├── models.ts      → tipos de modelos LLM disponibles
│   ├── users.ts       → getMyProfile() / updateMyProfile() / getPublicProfile() / getPublicFeed() / getPublicImages() / getMyAvatar() / uploadMyAvatar() / deleteMyAvatar()
│   └── index.ts       → barrel export
├── components/
│   ├── AdminRoute.tsx          → Guard de ruta: redirige a / si el usuario no es admin
│   ├── AppNavbar.tsx           → Navbar: logo, link Colecciones, dropdown de usuario; modo Clerk usa ClerkLogoutItem
│   ├── ConfirmModal.tsx        → Modal de confirmación reutilizable
│   ├── ContentCard.tsx         → Card de EntityContent con acciones según estado
│   ├── EntityContentsPanel.tsx → Panel de contenidos de entidad por categoría (lista + generación)
│   ├── EntityEditForm.tsx      → Formulario de edición inline de entidad
│   ├── FilterBar.tsx           → PageSizeSelect + OrderSelect — filtros de listado reutilizables
│   ├── ImageGallery.tsx        → Galería de imágenes generadas con acciones de compartir/eliminar
│   ├── ImageGenerator.tsx      → Flujo build-prompt → generate; batch 1-4 imágenes
│   ├── ImagePanel.tsx          → Panel de imágenes de entidad: galería + generador
│   ├── Layout.tsx              → AppNavbar + Outlet + StarfieldCanvas
│   ├── LoadingSpinner.tsx      → Spinner centrado con texto opcional
│   ├── MarkdownContent.tsx     → Renderizado markdown sanitizado (rehype-sanitize)
│   ├── ModelSelector.tsx       → Selector de modelo LLM para generación
│   ├── PaginationControls.tsx  → Controles de paginación reutilizables
│   ├── ProtectedRoute.tsx      → Guard dual: modo Clerk usa useUser(), modo local usa useAuth().user
│   ├── PublicContentModal.tsx  → Modal de lectura de EntityContent compartido (markdown, badges, owner)
│   ├── PublicImageModal.tsx    → Modal de imagen compartida: imagen, seed, prompts, descarga
│   ├── SafeImage.tsx           → img con fallback ante error de carga
│   ├── StarfieldCanvas.tsx     → Fondo animado canvas: estrellas + estrellas fugaces
│   └── TokenCounter.tsx        → Estimación de tokens (aviso a los 400)
├── contexts/
│   └── AuthContext.tsx    → AuthProvider + AuthContext: verifica sesión via GET /users/me, auto-logout timer
├── hooks/
│   ├── useApiError.ts                      → Manejo centralizado de errores de API (estado + setter)
│   ├── useAuth.ts                          → Acceso al contexto de autenticación
│   ├── useCollectionDocumentsStatus.ts     → Monitoriza estado de documentos; polling cada 3s si hay procesando
│   ├── useDebouncedValue.ts                → Debounce de un valor con delay configurable (default 300 ms)
│   ├── useDeleteConfirm.ts                 → Lógica de confirmación de eliminación (estado modal + callback)
│   ├── useEntityContents.ts                → Fetching/refresco de contenidos de una entidad
│   ├── useFormSubmit.ts                    → Estado de guardado de formularios (loading, error, success)
│   ├── useGenerate.ts                      → Wrapper cancellable para llamadas LLM (AbortSignal)
│   └── usePagination.ts                    → Estado de paginación: página actual, pageSize, callbacks
├── pages/
│   ├── CollectionDetailPage/
│   │   ├── index.tsx        → Tab container: Documentos / Entidades / Generar texto
│   │   ├── DocumentsTab.tsx → Upload PDF/TXT, tabla con estado de procesado
│   │   ├── EntitiesTab.tsx  → Tabla de entidades con badges y navegación al detalle
│   │   └── GenerateTab.tsx  → Consulta RAG libre contra la colección
│   ├── AdminPage.tsx         → Tabla de usuarios con avatar, email, rol, estado; eliminar usuario
│   ├── CollectionsPage.tsx   → Listado, creación y eliminación de colecciones propias
│   ├── EntityDetailPage.tsx  → Card editable + generación de contenido por categoría + imágenes
│   ├── GeneratePage.tsx      → Consulta RAG libre con manejo de errores 422/503
│   ├── LoginPage.tsx         → Dual: modo Clerk muestra <SignIn />; modo local muestra formulario con tabs
│   ├── ProfilePage.tsx       → Formulario editable: display_name, bio, avatar, email
│   ├── PublicFeedPage.tsx    → Feed público paginado: galería de imágenes + cards de contenido
│   └── PublicProfilePage.tsx → Perfil público: galería de imágenes + contenidos compartidos
├── types/
│   ├── collection.ts  → Collection (incluye owner_id), CreateCollectionRequest, CollectionListResponse
│   ├── content.ts     → EntityContent, PaginatedResponse<T>, request types
│   ├── document.ts    → Document, DocumentListResponse
│   ├── entity.ts      → Entity, CreateEntityRequest, UpdateEntityRequest, EntityListResponse
│   ├── generate.ts    → GenerateTextRequest, GenerateTextResponse
│   ├── images.ts      → BuildPromptRequest/Response, GenerateImagesRequest/Response, ImageGenerationItem, ImageRecordData
│   ├── user.ts        → UserProfile, UpdateProfileRequest, SharedContentItem, PublicProfile, UserAdminRecord
│   └── index.ts       → barrel export
├── utils/
│   ├── clerkConfig.ts → clerkKey con VITE_CLERK_PUBLISHABLE_KEY (fichero separado para Fast Refresh)
│   ├── constants.ts   → ENTITY_TYPE_BADGE/LABELS, ENTITY_CATEGORY_MAP, CATEGORY_LABELS, MAX_PENDING_CONTENTS
│   ├── enums.ts       → DocumentStatus, EntityType, ContentCategory, ContentStatus
│   ├── errors.ts      → getErrorMessage(), parseApiError() — mensajes en español
│   ├── formatters.ts  → formatDate() locale es-ES
│   ├── strings.ts     → helpers de manipulación de strings
│   ├── token.ts       → utilidades de token de sesión
│   └── tokens.ts      → estimateTokens(), QUERY_TOKEN_WARN_AT
├── App.tsx   → Raíz: ClerkBridge (sincroniza sesión Clerk→backend), UnauthorizedHandler (auth:unauthorized → /login)
└── main.tsx  → Entry point: monta App en #root
```

## Tests

**Stack:** Vitest 3 + @testing-library/react 16 + happy-dom 15.

Los tests se encuentran en `src/test/`. Las llamadas a la API se mockean con `vi.mock()`, sin MSW.

| Categoría   | Archivos                                                                        | Tests |
| ----------- | ------------------------------------------------------------------------------- | ----- |
| Utilidades  | errors, tokens, formatters, constants                                           | 26    |
| Componentes | ConfirmModal, TokenCounter, ContentCard, MarkdownContent                        | 32    |
| Hooks       | useGenerate, useEntityContents, useDebouncedValue, useCollectionDocumentsStatus | 26    |
| Páginas     | CollectionsPage, CollectionDetailPage, EntityDetailPage, GeneratePage           | 37    |

**Total: 121 tests.**

Aspectos destacados de cobertura:

- **`ContentCard`**: estados pending/confirmed/discarded, busy-lock (doble clic bloqueado), rollback optimista en fallo de API, badges de auditoría `✎ editado` (presencia/ausencia y sección colapsable del output original).
- **`MarkdownContent`**: sanitización XSS — `<script>`, `onerror`, `javascript:` href bloqueados; markdown estándar y `https://` permitidos.
- **`useCollectionDocumentsStatus`**: polling activo cuando hay documentos `processing`; polling detenido automáticamente cuando todos salen de ese estado; `ApiAbortError` no actualiza estado.
- **`CollectionsPage`**: paginación auto-back cuando la página actual queda vacía tras eliminación.
- **`EntityDetailPage`**: alerta de error en carga 404, formulario de generación, límite de borradores.

## Autenticación

El JWT de sesión viaja siempre en una cookie HttpOnly (`access_token`). El frontend nunca lo lee directamente. Hay dos modos de autenticación según `VITE_CLERK_PUBLISHABLE_KEY`:

### Modo local (sin Clerk)

- **Login**: `POST /auth/login` con `{ username_or_email, password }` → backend emite cookie `access_token` + cookie `csrf_token`.
- **Registro**: `POST /auth/register` → crea cuenta y emite cookie directamente.
- **`ProtectedRoute`**: usa `useAuth().user` (null → redirect a `/login`).
- **`LoginPage`**: formulario propio con tabs login/registro.

### Modo Clerk (`VITE_CLERK_PUBLISHABLE_KEY` definida)

- `ClerkProvider` envuelve la app. `LoginPage` muestra `<SignIn />` de Clerk.
- Tras autenticar con Clerk, `ClerkBridge` obtiene el JWT de Clerk y llama `POST /auth/clerk/sync` (JWT en header `Authorization: Bearer`). El backend crea/recupera el usuario local y emite cookie de sesión.
- `ClerkBridge` llama `login()` en `AuthContext` para actualizar el estado y navega a `/`.
- **`ProtectedRoute`**: usa `useUser()` de Clerk (no espera al sync) para evitar redirect prematuro.

### Comportamiento común

- **`AuthProvider`** al montar llama `GET /users/me` para verificar si hay sesión activa (cookie válida). `loading=true` hasta que responde, evitando redirect prematuro en refresh.
- **`apiFetch`**: usa `credentials: "include"` en todas las peticiones (cookies automáticas). Para mutaciones añade `X-CSRF-Token` leído de la cookie `csrf_token`.
- **401 fuera de `/login`**: `apiClient.ts` emite `new CustomEvent("auth:unauthorized")`. `UnauthorizedHandler` (en `App.tsx`) lo captura, llama `logout()` y navega a `/login` con React Router — sin full-page reload ni flash en blanco.
- **Auto-logout**: `AuthProvider` programa un `setTimeout` al tiempo exacto de expiración del token (60 min). Al disparar, llama `logout()` que invalida la sesión en servidor y limpia el estado.

## Pantallas

| Ruta                             | Página            | Auth       | Descripción                                                                                                                                      |
| -------------------------------- | ----------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `/login`                         | Login / Registro  | No         | Modo local: formulario con tabs login/registro. Modo Clerk: widget `<SignIn />` de Clerk                                                         |
| `/`                              | Colecciones       | Sí         | Cards con todas las colecciones; crear (modal) o eliminar con confirmación                                                                       |
| `/collections/:id`               | Detalle colección | Sí         | **Documentos**: upload PDF/TXT, tabla con estado; **Entidades**: tabla con badges, navegación al detalle; **Generar texto**: consulta RAG libre  |
| `/collections/:id/entities/:eid` | Detalle entidad   | Sí         | Card de entidad editable; formulario de generación; lista de `ContentCard`; generación de imágenes                                               |
| `/collections/:id/generate`      | Generar texto     | Sí         | Consulta RAG libre con manejo de errores 422/503                                                                                                 |
| `/profile`                       | Mi perfil         | Sí         | Formulario para editar display_name, bio, avatar y email; botón ← Volver                                                                         |
| `/admin`                         | Administración    | Sí (admin) | Tabla de usuarios con avatar, email, rol y estado; link al perfil público; eliminar usuario (bloqueado para cuenta propia)                       |
| `/feed`                          | Feed público      | No         | Galería de imágenes compartidas + cards de contenido paginadas; clic abre modal de lectura completa                                              |
| `/users/:username`               | Perfil público    | No         | Perfil de cualquier usuario: galería de imágenes + contenidos compartidos; botón Compartir (copia URL) + engranaje hacia `/profile` (solo owner) |

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
