"""
Construcción de prompts visuales para generación de imágenes.

Estrategia actual: Opción C — templates por categoría (determinista, sin LLM).
Preparado para Opción B — extracción semántica vía LLM (próximo sprint).

La estrategia se selecciona con IMAGE_BACKEND y PROMPT_STRATEGY en config.
Cuando PROMPT_STRATEGY="llm" se usará invoke_prompt_extraction_pipeline()
que aún no está implementado — ver TODO marcados con [OPTION_B].
"""

from __future__ import annotations

from app.models.entities import EntityType
from app.models.enums import ContentCategory

# ── Prefijos visuales por entity type ────────────────────────────────────────

STYLE_PREFIX: dict[EntityType, str] = {
    EntityType.character: (
        "fantasy character portrait, detailed face, "
        "cinematic lighting, epic atmosphere,"
    ),
    EntityType.creature: (
        "fantasy creature illustration, dramatic pose, "
        "detailed anatomy, dark fantasy art,"
    ),
    EntityType.location: (
        "fantasy landscape, wide establishing shot, "
        "atmospheric perspective, detailed environment,"
    ),
    EntityType.faction: (
        "faction emblem design, heraldic composition, " "fantasy art, symbolic imagery,"
    ),
    EntityType.item: (
        "fantasy item showcase, neutral background, "
        "detailed textures, magical aura, product lighting,"
    ),
}

# ── Sufijo de calidad fijo ────────────────────────────────────────────────────

QUALITY_SUFFIX = "high quality, masterpiece, sharp focus, professional digital art"

# ── Estrategia visual por categoría ──────────────────────────────────────────
# Derivada de prompt_templates.py:
#   backstory        → narrativa de orígenes, NO descriptores visuales
#   extended_desc    → rasgos físicos y apariencia, SÍ descriptores visuales
#   scene            → ambientación + acción, primeras oraciones útiles
#   chapter          → narrativa larga, solo apertura es visual

CATEGORY_VISUAL_STRATEGY: dict[ContentCategory, dict] = {
    ContentCategory.extended_description: {
        # El LLM genera: "rasgos, apariencia, características distintivas"
        # → texto directamente útil como descriptor visual
        "strategy": "direct",
        "prefix_addition": "detailed appearance,",
        # [OPTION_B] llm_instruction: "Extrae solo descriptores físicos y
        # visuales. Formato: adjetivo sustantivo separados por coma."
    },
    ContentCategory.backstory: {
        # El LLM genera: "orígenes, motivaciones, eventos formativos"
        # → narrativa en prosa, NO útil directo para imagen
        # → usar solo entidad + descripción + mood de origen
        "strategy": "entity_only",
        "prefix_addition": "dramatic origin scene, atmospheric,",
        # [OPTION_B] llm_instruction: "Del texto de trasfondo extrae solo
        # el ambiente visual del lugar de origen y rasgos físicos si los hay.
        # Máximo 10 palabras visuales."
    },
    ContentCategory.scene: {
        # El LLM genera: "ambientación, diálogo y acción"
        # → las primeras 1-2 oraciones tienen el setting y los actores
        "strategy": "first_sentences",
        "prefix_addition": "action scene, dynamic composition,",
        "sentences": 2,
        # [OPTION_B] llm_instruction: "Extrae el setting visual de la escena:
        # lugar, iluminación, postura de personajes. Máximo 12 palabras."
    },
    ContentCategory.chapter: {
        # El LLM genera: "capítulo con inicio, desarrollo y cierre"
        # → solo las primeras oraciones establecen el contexto visual
        "strategy": "first_sentences",
        "prefix_addition": "epic narrative scene, cinematic,",
        "sentences": 1,
        # [OPTION_B] llm_instruction: "Extrae solo la descripción visual
        # de la escena de apertura. Máximo 10 palabras descriptivas."
    },
}

# ── Utilidades de tokens ──────────────────────────────────────────────────────


def _estimate_tokens(text: str) -> int:
    """~4 chars por token. Consistente con estimateTokens() del frontend."""
    return max(0, len(text) // 4)


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Trunca a max_tokens preservando palabras completas."""
    if _estimate_tokens(text) <= max_tokens:
        return text
    words = text.split()
    result: list[str] = []
    for word in words:
        candidate = " ".join(result + [word])
        if _estimate_tokens(candidate) > max_tokens:
            break
        result.append(word)
    return " ".join(result)


def _extract_first_sentences(text: str, n: int = 2) -> str:
    """Extrae las primeras N oraciones de un texto."""
    import re

    # Separar por punto, signo de exclamación o interrogación seguido de espacio/fin
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(sentences[:n])


# ── Builder principal ─────────────────────────────────────────────────────────


def build_visual_prompt(
    entity_type: EntityType,
    entity_name: str,
    entity_description: str,
    confirmed_content: str,
    category: ContentCategory,
    max_tokens: int = 150,
    target_tokens: int = 75,
) -> dict[str, str | int | bool]:
    """
    Construye un prompt visual para generación de imagen.

    Estrategia: Opción C (templates deterministas por categoría).
    Ver CATEGORY_VISUAL_STRATEGY para la lógica por categoría.

    # [OPTION_B] Cuando se implemente extracción LLM:
    # - Añadir parámetro use_llm_extraction: bool = False
    # - Si use_llm_extraction=True, llamar a invoke_prompt_extraction_pipeline()
    #   pasando confirmed_content + strategy["llm_instruction"]
    # - El resultado reemplaza a `narrative` antes del ensamblado final

    Retorna:
        {
            "prompt": str,
            "token_count": int,
            "truncated": bool,
            "source": str,      # "content_direct" | "content_sentences" |
                                #  "entity_only" | "description" | "name_only"
            "strategy": str,    # estrategia aplicada
            "category": str,    # categoría del contenido base
        }
    """
    strategy_config = CATEGORY_VISUAL_STRATEGY.get(
        category,
        {"strategy": "entity_only", "prefix_addition": ""},
    )
    strategy = strategy_config["strategy"]
    prefix_addition = strategy_config.get("prefix_addition", "")

    prefix = STYLE_PREFIX.get(entity_type, "fantasy art,")
    if prefix_addition:
        prefix = f"{prefix} {prefix_addition}"

    # ── Calcular tokens disponibles para narrativa ────────────────────────────
    prefix_tokens = _estimate_tokens(prefix)
    suffix_tokens = _estimate_tokens(QUALITY_SUFFIX)
    name_tokens = _estimate_tokens(entity_name)
    overhead = prefix_tokens + suffix_tokens + name_tokens + 5
    available_tokens = max_tokens - overhead
    target_available = max(10, target_tokens - overhead)

    # ── Extraer narrativa según estrategia ────────────────────────────────────
    narrative = ""
    source = "name_only"
    truncated = False

    if strategy == "direct" and confirmed_content.strip():
        # extended_description: usar el texto directamente
        narrative = confirmed_content.strip()
        source = "content_direct"

    elif strategy == "first_sentences" and confirmed_content.strip():
        # scene / chapter: extraer primeras N oraciones
        n = strategy_config.get("sentences", 2)
        narrative = _extract_first_sentences(confirmed_content, n)
        source = "content_sentences"

    elif strategy == "entity_only":
        # backstory: el texto narrativo no es útil visualmente
        # usar descripción de la entidad si existe
        if entity_description.strip():
            narrative = entity_description.strip()
            source = "description"
        # si no hay descripción, source queda "name_only"

    # Fallback: si la estrategia no produjo narrativa, intentar descripción
    if not narrative and entity_description.strip():
        narrative = entity_description.strip()
        source = "description"

    # ── Truncar para respetar límite de tokens ────────────────────────────────
    if narrative:
        if _estimate_tokens(narrative) > target_available:
            narrative_at_target = _truncate_to_tokens(narrative, target_available)
            if narrative_at_target:
                narrative = narrative_at_target
                truncated = _estimate_tokens(confirmed_content) > target_available
            elif _estimate_tokens(narrative) <= available_tokens:
                # No cabe en target pero sí en max
                truncated = False
            else:
                narrative = _truncate_to_tokens(narrative, available_tokens)
                truncated = True

    # ── Ensamblar prompt final ────────────────────────────────────────────────
    parts = [prefix, entity_name]
    if narrative:
        parts.append(narrative)
    parts.append(QUALITY_SUFFIX)

    prompt = ", ".join(p.strip().rstrip(",") for p in parts if p.strip())
    token_count = _estimate_tokens(prompt)

    return {
        "prompt": prompt,
        "token_count": token_count,
        "truncated": truncated,
        "source": source,
        "strategy": strategy,
        "category": category.value,
    }
