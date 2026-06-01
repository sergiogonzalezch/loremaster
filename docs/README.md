# Documentación — Lore Master

## `architecture/` — Referencia técnica
*Explican CÓMO funciona el sistema. Documentación permanente.*

| Documento | Contenido |
|---|---|
| [DOCUMENTATION.md](architecture/DOCUMENTATION.md) | Especificación completa: HU-01 a HU-06, ERD, stack, pipelines RAG/imagen, flujos auth |
| [DEPLOY.md](architecture/DEPLOY.md) | Runbook operacional: cómo levantar el stack, primer admin, checklist, debug |
| [ENVIRONMENT.md](architecture/ENVIRONMENT.md) | Variables de entorno, modos (local/Docker/prod), launchers, prerequisitos |
| [ENV-ARCHITECTURE.md](architecture/ENV-ARCHITECTURE.md) | Flujo de variables entre archivos, prioridad Pydantic, clasificación |
| [LIMITERS.md](architecture/LIMITERS.md) | Todos los límites del sistema: tamaños, tokens, rate limits, regex, columnas DB |
| [CLERK-APP-INTEGRATION.md](architecture/CLERK-APP-INTEGRATION.md) | Implementación Clerk: flujo auth, modelo de almacenamiento, fusión de cuentas |
| [MOD.md](architecture/MOD.md) | Diseño del sistema de moderación: patrones regex, Llama Guard, guardrails |
| [COST-REPORT.md](architecture/COST-REPORT.md) | Análisis de costos por escenario (demo ~$11/mes, prod, GPU cloud) |
| [DEPLOY-CLOUDFLARE.md](architecture/DEPLOY-CLOUDFLARE.md) | Plan de deploy gratuito: tu equipo como servidor usando Cloudflare Tunnel + R2 |

## `planning/` — Seguimiento de tareas
*Rastrean QUÉ hay que hacer y qué está hecho.*

| Documento | Contenido |
|---|---|
| [STRATEGY.md](planning/STRATEGY.md) | Estado rápido pendientes/resueltos + hoja de ruta semanas 9-12 |
| [WEEKLY_CHECKLISTS.md](planning/WEEKLY_CHECKLISTS.md) | Checklist semanal detallado con criterios de aceptación por semana |
| [FIX.md](planning/FIX.md) | Log de deuda técnica: 61 ítems con estado y fecha de cierre |

## `completed/` — Planes de implementación finalizados
*Guías de cómo se implementaron features ya completadas. Referencia histórica.*

| Documento | Contenido |
|---|---|
| [PLAN-DEPLOY-STORAGE.md](completed/PLAN-DEPLOY-STORAGE.md) | Integración S3/boto3 con Floci, MinIO y Cloudflare R2 |
| [PLAN-LLAMA-GUARD.md](completed/PLAN-LLAMA-GUARD.md) | Implementación Llama Guard 3 como capa semántica de moderación |

## `history/` y `old/`
Documentos de sesiones anteriores y versiones obsoletas. Solo para referencia histórica.
