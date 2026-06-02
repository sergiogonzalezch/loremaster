# Auditoría de Seguridad — Lore Master

**Fecha:** 2026-05-09
**Branch:** `main`
**Metodología:** 5 agentes en paralelo (auth/IDOR, inyecciones clásicas + LLM, manejo de archivos, config/secretos, frontend) leyendo el código real, no solo grepeando.

> **Nota (2026-06-02):** Este documento fue **redactado** para el repositorio público.
> Los hallazgos originales incluían rutas exactas, números de línea y payloads de
> explotación. Como las 53 vulnerabilidades están **cerradas** (ver
> `AUDIT-SECURITY-REVIEW3-2026-05-12.md`), se conserva únicamente el resumen por
> categoría y severidad para evidenciar el alcance del trabajo de seguridad, sin
> exponer detalle accionable. El detalle completo se mantiene fuera del control de
> versiones.

---

## Resumen ejecutivo

| Severidad | Total | Distribución por área |
|---|---:|---|
| **Crítico** | **8** | Auth · File handling · Config |
| **Alto** | **14** | Config · File handling · Auth · Inyección · Frontend |
| **Medio** | 18 | distribuido |
| **Bajo** | 13 | distribuido |
| **Total** | **53** | |

**Conclusión:** La auditoría inicial identificó huecos en tres áreas principales:
**autorización** (IDOR cross-tenant), **manejo de archivos** (path traversal,
mounts públicos, límites de parsers) y **configuración** (gestión de secretos,
pinning de dependencias, headers de seguridad). El modelo de datos vía SQLModel
resultó limpio: **cero SQL injection, cero command injection, cero deserialización
insegura**.

Estado posterior: **53/53 resueltos** (ver `AUDIT-SECURITY-REVIEW3-2026-05-12.md`).

---

## Distribución de hallazgos por categoría

Resumen redactado — sin rutas, líneas ni payloads.

### 🔴 Críticos (8)
- **Autorización (4):** verificación de identidad en producción e IDOR
  cross-tenant en rutas de documentos y entidades.
- **Manejo de archivos (2):** path traversal en construcción de rutas de usuario
  y exposición de árbol multimedia sin control de acceso.
- **Config (2):** gestión del secreto de firma JWT y credenciales de base de
  datos por defecto.

### 🟠 Altos (14)
- **Auth/privilegios (3):** propagación de claims sensibles, validación de email,
  limpieza de contenido al eliminar usuarios.
- **Prompt injection LLM/RAG (2):** inyección indirecta vía documentos y vía
  campos de entidad interpolados fuera del contexto delimitado.
- **Manejo de archivos (3):** validación de tipo de archivo, límites de parser
  (PDF bombs), rate limiting de endpoints sensibles.
- **Config (5):** headers de seguridad, validación de issuer/algoritmo en JWT,
  pinning de dependencias y lockfile.
- **Frontend (1):** almacenamiento de token y superficie XSS.

### 🟡 Medios (18) · 🟢 Bajos (13)
Distribuidos entre LLM/RAG, auth, configuración operativa, manejo de archivos y
frontend. Incluyen endurecimiento del content guard, gating de documentación de
API, redacción de PII en logs, borrado físico en cascada y defensa en profundidad
en validación de imágenes y rutas.

---

## Áreas verificadas y limpias

- **Cero SQL injection.** Todo SQLModel parametrizado; filtros con bound
  parameters; ordenamiento por `Literal` restringido.
- **Cero command injection.** Sin `subprocess`/`os.system`/`eval`/`exec` en `app/`.
- **Cero deserialización insegura.** Sin `pickle.loads`; YAML solo con `safe_load`.
- **Sin secretos commiteados.** `.env` nunca tracked en git history (verificado).
- **CORS no usa `*` con `allow_credentials`** (validador lo bloquea).
- **Bcrypt** usado correctamente para hashing de passwords.
- **Frontend:** sin `dangerouslySetInnerHTML`, `innerHTML`, `eval`, `new Function`,
  `document.write`, ni `postMessage` con `*`. `npm audit`: 0 vulnerabilidades.
- **Mass-assignment** estructuralmente prevenido — los schemas de request no
  aceptan campos de identidad/rol.
- **Open redirect:** sin redirects controlados por input en backend.

---

## Líneas de trabajo de mayor leverage

Resumen de las prioridades que cerraron la mayoría de los críticos:

1. Aplicar verificación de ownership consistente en rutas de documentos y entidades.
2. Unificar la verificación de identidad (incl. estado de usuario) entre los flujos
   de auth local y Clerk.
3. Validación estricta de `username` + contención de rutas bajo el directorio raíz
   de media (defensa en profundidad).
4. Sustituir el servido estático de media por un controller con auth y headers de
   seguridad.
5. Endurecer configuración: exigir secretos por entorno, pinear dependencias y
   variabilizar credenciales de infraestructura.

---

*Documento redactado para publicación el 2026-06-02. Verificación de cierre en
`AUDIT-SECURITY-REVIEW3-2026-05-12.md`.*
