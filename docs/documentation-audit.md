# Auditoría de documentación del proyecto

Este documento propone mejoras concretas sobre la documentación, priorizando **los puntos 1 al 5** y añadiendo lineamientos para evolución del proyecto.

## 1. Claridad de propósito

### Estado actual
- El README describe intención general, pero mezcla estado draft, setup y ejecución sin separar claramente alcance MVP vs roadmap.

### Mejora aplicada
- Se separó objetivo/alcance del estado de implementación.
- Se explicita que el almacenamiento es **mock en memoria**, para evitar falsas expectativas de persistencia.

### Regla recomendada
- Toda documentación principal debe iniciar con:
  1) Qué problema resuelve,
  2) Qué sí incluye hoy,
  3) Qué NO incluye todavía.

## 2. Onboarding y ejecución local

### Estado actual
- Había pasos incompletos y comandos ambiguos (`cd` duplicado/confuso).

### Mejora aplicada
- Se normalizó una secuencia reproducible: clonado, entorno virtual, instalación, `.env`, ejecución con uvicorn.

### Regla recomendada
- Mantener un bloque de instalación **copiable** de inicio a fin.
- Evitar instrucciones implícitas o dependientes de contexto no documentado.

## 3. Contratos de API

### Estado actual
- Endpoints definidos en código pero con bajo detalle de reglas operativas en documentación.

### Mejora aplicada
- Se documentaron rutas por dominio (colecciones/documentos/generación).
- Se incluyeron restricciones críticas (MIME permitido y límite de 50MB).

### Regla recomendada
- Por endpoint documentar mínimo:
  - método + ruta,
  - payload,
  - validaciones,
  - códigos de error esperables.

## 4. Estructura de proyecto

### Estado actual
- No había una vista estructurada y comentada del árbol del backend.

### Mejora aplicada
- Se incorporó árbol por capas con responsabilidad por archivo/directorio.

### Regla recomendada
- Toda nueva carpeta/módulo debe quedar reflejada en README o docs de arquitectura en el mismo PR.

## 5. Consistencia terminológica y de dominio

### Estado actual
- Se mezclan términos de AI/RAG con comportamiento que todavía es mock, lo que puede confundir.

### Mejora aplicada
- Se etiquetó explícitamente qué parte es mock y qué parte es contrato estable.

### Regla recomendada
- Usar marcadores de madurez:
  - `MVP` (estable),
  - `WIP` (en evolución),
  - `Mock` (simulado).

---

## Recomendaciones adicionales para mejorar documentación

1. Crear una sección de **decisiones arquitectónicas (ADR)** para cambios relevantes.
2. Definir un **glosario de dominio** (colección, documento, entidad, fuente, chunk, embedding).
3. Añadir ejemplos curl por endpoint y ejemplos de errores comunes.
4. Incorporar checklist de PR: “¿actualizaste docs si cambió contrato/estructura?”.
5. Publicar una guía corta de convenciones de nombres para modelos/schemas.
