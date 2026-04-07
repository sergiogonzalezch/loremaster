# Arquitectura, estructura y lineamientos de ERD

## 1) Estructura actual (mock)

La implementación usa diccionarios en memoria como almacenamiento:
- `collections = {}`
- `documents = {}`
- `entities = {}`

Relación implícita actual:
- 1 colección → N documentos
- entidades sin relación formal con colección/documento

## 2) ERD actual (representación conceptual)

```mermaid
erDiagram
    COLLECTION ||--o{ DOCUMENT : contains

    COLLECTION {
        uuid id
        string name
        string description
        string status
    }

    DOCUMENT {
        uuid id
        uuid collection_id
        string filename
        text content
        string status
    }

    ENTITY {
        uuid id
        string name
        string description
    }
```

> Nota: `ENTITY` existe en servicio/modelo, pero hoy no está integrada con persistencia relacional ni montada en `main.py`.

## 3) ERD objetivo sugerido (producción)

```mermaid
erDiagram
    USER ||--o{ COLLECTION : owns
    COLLECTION ||--o{ DOCUMENT : contains
    DOCUMENT ||--o{ DOCUMENT_CHUNK : splits_into
    DOCUMENT_CHUNK ||--o{ CHUNK_EMBEDDING : embedded_as
    COLLECTION ||--o{ ENTITY : defines
    ENTITY ||--o{ ENTITY_RELATION : source
    ENTITY ||--o{ ENTITY_RELATION : target

    USER {
        uuid id
        string email
        string display_name
        datetime created_at
    }

    COLLECTION {
        uuid id
        uuid user_id
        string name
        text description
        string status
        datetime created_at
        datetime updated_at
    }

    DOCUMENT {
        uuid id
        uuid collection_id
        string filename
        string mime_type
        string source_type
        string checksum_sha256
        string status
        datetime created_at
    }

    DOCUMENT_CHUNK {
        uuid id
        uuid document_id
        int chunk_index
        text content
        int token_count
    }

    CHUNK_EMBEDDING {
        uuid id
        uuid chunk_id
        string model_name
        int dimension
        string vector_ref
        datetime created_at
    }

    ENTITY {
        uuid id
        uuid collection_id
        string name
        text description
        string entity_type
        json attributes
        datetime created_at
        datetime updated_at
    }

    ENTITY_RELATION {
        uuid id
        uuid source_entity_id
        uuid target_entity_id
        string relation_type
        float confidence
        datetime created_at
    }
```

## 4) Comparación: actual vs objetivo

### Actual (mock)
- ✅ Muy rápido para prototipo.
- ❌ Sin persistencia.
- ❌ Sin auditoría temporal (`created_at`, `updated_at`).
- ❌ Sin claves/índices ni reglas referenciales.

### Objetivo (producción)
- ✅ Trazabilidad por usuario/colección/documento.
- ✅ Separación de chunking/embeddings para RAG real.
- ✅ Modelado formal de entidades y relaciones narrativas.
- ✅ Base para escalar queries y observabilidad.

## 5) Lineamientos y reglas de desarrollo (modelos/schemas/docs)

### Modelos de dominio
1. Todo modelo persistente debe incluir `id`, `created_at`, `updated_at`.
2. Estados (`status`) deben usar enums explícitos.
3. Relación entre tablas debe tener FK y comportamiento de borrado definido.

### Schemas API (Pydantic)
1. Separar request/response por caso de uso (no reutilizar modelo interno sin control).
2. Tipar respuestas con `response_model` en FastAPI.
3. Declarar validaciones (longitud, regex, límites) en `Field(...)`.
4. Estandarizar envelope de respuesta (`data`, `meta`, `errors`).

### Documentación viva
1. Si se cambia endpoint/modelo, actualizar README + docs en el mismo PR.
2. Mantener sección “Breaking changes”.
3. Añadir ejemplos mínimos de request/response por endpoint.

### Gobernanza técnica
1. Versionar API (`/api/v1`, `/api/v2`) al romper contratos.
2. Evitar lógica de negocio en rutas; mantenerla en `services/`.
3. Agregar pruebas de contrato para rutas críticas.
