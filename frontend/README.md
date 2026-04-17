# Lore Master — Frontend

SPA React para interactuar con la API de Lore Master.

## Stack

| | |
|---|---|
| Framework | React 19 |
| Lenguaje | TypeScript |
| Bundler | Vite |
| UI | React Bootstrap 2 + Bootstrap 5 |
| Routing | React Router 7 |
| HTTP | fetch nativo |

## Requisitos

- Node.js 18+
- Backend corriendo en `http://localhost:8000`

## Instalación y ejecución

```bash
cd frontend
npm install
npm run dev
```

Disponible en `http://localhost:5173`.

## Variables de entorno

Crea un archivo `.env` en `frontend/`:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## Estructura del proyecto

```
src/
├── api/           → Funciones fetch tipadas por recurso
├── types/         → Interfaces TypeScript (mirror de schemas backend)
├── components/    → Layout, Navbar, modales reutilizables
└── pages/         → CollectionsPage, CollectionDetailPage, EntityDetailPage, GeneratePage
```

## Pantallas

| Página | Descripción |
|---|---|
| **Colecciones** | Listado de colecciones, crear nueva, eliminar |
| **Detalle colección** | Tabs con documentos, entidades y generación de texto libre |
| **Detalle entidad** | Información de la entidad y sistema de borradores RAG (generar, editar, confirmar, descartar) |
| **Generar texto** | Consulta libre contra el lore cargado en la colección |

## Conexión con backend

El frontend consume la API en `VITE_API_BASE_URL`. Para que las peticiones no sean bloqueadas por CORS, añade `http://localhost:5173` a `ALLOWED_ORIGINS` en `backend/.env`.

## Build para producción

```bash
npm run build
```

Los artefactos se generan en `frontend/dist/`.