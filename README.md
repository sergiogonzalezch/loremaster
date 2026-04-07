# 📜 Lore Master API

Backend en **FastAPI** para gestionar colecciones de conocimiento (lore), documentos y generación de respuestas basadas en contenido ingestado.

## 1) Objetivo y alcance

Lore Master API sirve como capa de backend para:
- crear y administrar colecciones,
- cargar documentos por colección,
- generar respuestas usando los documentos cargados,
- (en evolución) modelar entidades narrativas.

> Estado actual: implementación **MVP con almacenamiento en memoria (mock)**, útil para validar flujos API antes de persistencia real.

## 2) Stack y dependencias principales

- **Framework**: FastAPI
- **Validación**: Pydantic
- **Servidor local**: Uvicorn
- **Config**: python-dotenv
- **Persistencia actual**: diccionarios en memoria (`documents_db_mock.py`)

## 3) Puesta en marcha local

### Requisitos
- Python 3.10+
- pip

### Instalación
```bash
git clone https://github.com/sergiogonzalezch/loremaster.git
cd loremaster/backend
python -m venv .venv
source .venv/bin/activate   # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Variables de entorno
Crear `.env` dentro de `backend/` (puedes partir de `.env.example`) con al menos:

```env
PROJECT_NAME="Lore Master API"
ENVIRONMENT="development"
OLLAMA_MODEL="llama3"
```

### Ejecutar
```bash
cd backend
uvicorn app.main:app --reload
```

### Endpoints base
- `GET /` estado general del servicio
- `GET /health` healthcheck
- Swagger: `GET /docs`

## 4) Árbol del proyecto y responsabilidades

```text
backend/
  app/
    api/routes/
      collections.py   # CRUD básico de colecciones
      documents.py     # Ingesta y lectura/borrado de documentos
      generate.py      # Generación de respuestas por colección
      entities.py      # Ruta de entidades (actualmente no montada)
    services/
      collection_service.py
      documents_service.py
      generate_service.py
      entities_service.py
      documents_db_mock.py  # "base de datos" en memoria
    models/
      models.py        # Schemas Pydantic de request/response
    main.py            # Inicialización FastAPI + router include
  config.py            # Settings del proyecto
```

## 5) Contratos API y reglas funcionales (actual)

### Colecciones
- `POST /api/v1/collections/` crea colección (`name`, `description`).
- `GET /api/v1/collections/` lista colecciones.
- `GET /api/v1/collections/{collection_id}` obtiene detalle.
- `DELETE /api/v1/collections/{collection_id}` elimina colección.

### Documentos
- `POST /api/v1/collections/{collection_id}/documents` ingesta archivo.
- MIME permitido: `text/plain`, `application/pdf`.
- Tamaño máximo: **50 MB**.
- `GET /api/v1/collections/{collection_id}/documents` lista documentos.
- `GET /api/v1/collections/{collection_id}/documents/{doc_id}` obtiene documento.
- `DELETE /api/v1/collections/{collection_id}/documents/{doc_id}` elimina documento.

### Generación
- `POST /api/v1/collections/{collection_id}/text` recibe `query` y retorna respuesta mock usando fuentes de esa colección.

