# Pendientes Backend — Fase Posterior

Problemas identificados en el análisis del backend que quedan fuera del alcance actual y se abordarán en una fase posterior.

---

## Medio

### Sin autenticación ni identidad de usuario
La API es completamente pública. No existe modelo de usuario ni mecanismo de control de acceso.
Para un proyecto colaborativo (writers, RPG creators) esto es una limitación de producto importante.
Definir el modelo de acceso (single-tenant vs multi-tenant) antes de implementar.

---

## Bajos

### Sin operaciones en lote
No existe un endpoint de bulk-create para entidades ni documentos.
Crear recursos uno a uno via REST es lento para bases de conocimiento grandes.

### Prefix `lm_` hardcodeado en Qdrant
El nombre de las colecciones en Qdrant usa el prefijo `lm_` de forma hardcodeada en `engine/rag.py`.
Si se comparte la instancia de Qdrant entre proyectos o entornos, hay riesgo de colisión de nombres.
Mover el prefijo a configuración (`settings`).

### Prometheus/Grafana sin integración real
Los servicios de Prometheus y Grafana están declarados en `docker-compose.yml` pero no hay
ninguna instrumentación en el código (métricas, endpoints `/metrics`, etc.).