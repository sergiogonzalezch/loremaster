# Sistema de Moderación — Diseño (resumen público)

> **Nota (2026-06-02):** Este documento fue **redactado** para el repositorio
> público. La versión interna incluía los patrones regex exactos, las técnicas de
> evasión probadas y los detalles de detección por categoría de daño (incluyendo
> seguridad infantil). Publicar esa información permitiría construir evasiones del
> guard, por lo que aquí solo se describe el diseño de alto nivel. El detalle de
> implementación y el harness de evaluación se mantienen fuera del control de
> versiones (y en el código fuente, no documentados a nivel de patrón).

---

## Arquitectura de moderación

LoreMaster aplica moderación en **tres capas**, todas self-hosted (sin enviar
contenido de usuarios a servicios externos):

1. **Guard léxico de input** — valida queries y prompts del usuario antes del RAG
   y antes de la generación. Normaliza el texto (Unicode NFKD, lowercase, defensa
   contra ofuscación común) antes de aplicar las reglas.
2. **Guard léxico de output** — valida la salida del LLM antes de persistir o
   compartir. Diseñado asimétricamente: el contenido dañino se bloquea cuando
   aparece con **intención instructiva**, permitiendo narrativa de ficción
   (batallas, conflicto, villanos) sin falsos positivos.
3. **Capa semántica (Llama Guard 3)** — clasificación binaria safe/unsafe sobre el
   output, opcional y *fail-open*. Activable con `LLAMA_GUARD_ENABLED=true`. Cubre
   los casos que un guard léxico no puede detectar por framing indirecto.

El guard aplica un límite de tamaño de texto antes de normalizar para prevenir
ReDoS.

---

## Principios de diseño

- **Input vs output asimétrico.** El output exige contexto instructivo para
  bloquear (p. ej. "cómo fabricar X"), de modo que el LLM pueda narrar violencia
  ficticia. El input es más estricto en categorías no negociables.
- **Minimizar falsos positivos en RPG.** El caso de uso principal es worldbuilding
  narrativo: guerra, conflicto, villanía y romance adulto son contenido legítimo.
  Las reglas se calibran para no bloquear narrativa válida.
- **Categorías no negociables.** La seguridad infantil se bloquea siempre, con
  independencia del framing. Los detalles de detección no se documentan
  públicamente.
- **Auditoría.** Los eventos de moderación se registran con contexto
  (`user_id`, `collection_id`, `entity_id`, `operation`, patrón disparado) para
  trazabilidad, sin almacenar el contenido completo.

---

## Decisión de producto — alcance de contenido

LoreMaster es una herramienta narrativa **para adultos**. Romance, intimidad y
contenido sensual entre adultos son aceptables; el contenido sexual explícito y
las categorías críticas se bloquean. Esta decisión está anclada en el dataset de
evaluación y se revisaría si el público objetivo cambiara a familiar/educativo.

---

## Validación — guard harness

La efectividad del guard se mide con un harness de evaluación
(`backend/evaluations/guard_harness/`, no versionado en resultados) sobre tres
tipos de dataset:

- **adversarial** — inputs diseñados para evadir el guard a través de categorías
  de daño.
- **bypass** — variantes de evasión técnica (ofuscación de caracteres, idiomas).
- **rpg_legitimate** — queries y outputs que deben pasar sin bloqueo (narrativa de
  ficción).

Cada caso se evalúa con un juez mecánico (¿decisión correcta?) y jueces
LLM-as-judge para severidad de falsos negativos y detección de falsos positivos.
Los ciclos de evaluación cerraron la cobertura de evasión técnica y eliminaron los
falsos positivos sobre narrativa RPG legítima; la capa semántica (Llama Guard 3)
cubre los casos residuales de framing indirecto.

---

*Documento redactado para publicación el 2026-06-02. El diseño detallado, los
patrones de detección y los resultados del harness se mantienen fuera del
repositorio público.*
