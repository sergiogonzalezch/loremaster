"""
Construcción de prompts visuales para generación de imágenes.

Estrategia configurable via config.py (PROMPT_STRATEGY):
- "llm": usa invoke_prompt_extraction_pipeline() para extraer descriptores vía LLM
- "template": usa estrategias deterministas por categoría

Las estrategias deterministas permanecen como fallback si el LLM falla.
"""

from __future__ import annotations

from app.core.config import settings
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
        "faction emblem design, heraldic composition, fantasy art, symbolic imagery,"
    ),
    EntityType.item: (
        "fantasy item showcase, neutral background, "
        "detailed textures, magical aura, product lighting,"
    ),
}

# ── Sufijo de calidad fijo ────────────────────────────────────────────────────

QUALITY_SUFFIX = "high quality, masterpiece, sharp focus, professional digital art"

# ── Estrategia visual por categoría (template fallback) ────────────────────

CATEGORY_VISUAL_STRATEGY: dict[ContentCategory, dict] = {
    ContentCategory.extended_description: {
        "strategy": "direct",
        "prefix_addition": "detailed appearance,",
    },
    ContentCategory.backstory: {
        "strategy": "entity_only",
        "prefix_addition": "dramatic origin scene, atmospheric,",
    },
    ContentCategory.scene: {
        "strategy": "first_sentences",
        "prefix_addition": "action scene, dynamic composition,",
        "sentences": 2,
    },
    ContentCategory.chapter: {
        "strategy": "first_sentences",
        "prefix_addition": "epic narrative scene, cinematic,",
        "sentences": 1,
    },
}

# ── Prompt source labels ────────────────────────────────────────────────────

PROMPT_SOURCE_LABELS: dict[str, str] = {
    "content_direct": "Basado en la descripción extendida de la entidad",
    "content_sentences": "Basado en la escena o capítulo generado",
    "description": "Basado en la descripción general de la entidad",
    "name_only": "Solo el nombre — la entidad no tiene suficiente contexto",
    "llm_extraction": "Extraído vía LLM",
    "template": "Prompt determinista (template)",
    "fallback": "Prompt determinista (fallback)",
    "extended": "Basado en la descripción extendida de la entidad",
    "scene": "Basado en la escena o capítulo generado",
    "entity_desc": "Basado en la descripción general de la entidad",
}


def _estimate_tokens(text: str) -> int:
    """~4 chars por token."""
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

    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(sentences[:n])


def _map_source_to_code(source: str) -> str:
    """Mapea el código interno al código de base de datos."""
    mapping = {
        "content_direct": "extended",
        "content_sentences": "scene",
        "description": "entity_desc",
        "name_only": "name_only",
    }
    return mapping.get(source, source)


def _build_with_template(
    entity_type: EntityType,
    entity_name: str,
    entity_description: str,
    confirmed_content: str,
    category: ContentCategory,
    max_tokens: int,
    target_tokens: int,
) -> dict[str, str | int | bool]:
    """Estrategia determinista (template) - fallback cuando LLM no está disponible."""
    strategy_config = CATEGORY_VISUAL_STRATEGY.get(
        category,
        {"strategy": "entity_only", "prefix_addition": ""},
    )
    strategy = strategy_config["strategy"]
    prefix_addition = strategy_config.get("prefix_addition", "")

    prefix = STYLE_PREFIX.get(entity_type, "fantasy art,")
    if prefix_addition:
        prefix = f"{prefix} {prefix_addition}"

    prefix_tokens = _estimate_tokens(prefix)
    suffix_tokens = _estimate_tokens(QUALITY_SUFFIX)
    name_tokens = _estimate_tokens(entity_name)
    overhead = prefix_tokens + suffix_tokens + name_tokens + 5
    available_tokens = max_tokens - overhead
    target_available = max(10, target_tokens - overhead)

    narrative = ""
    source = "name_only"
    truncated = False

    if strategy == "direct" and confirmed_content.strip():
        narrative = confirmed_content.strip()
        source = "content_direct"

    elif strategy == "first_sentences" and confirmed_content.strip():
        n = strategy_config.get("sentences", 2)
        narrative = _extract_first_sentences(confirmed_content, n)
        source = "content_sentences"

    elif strategy == "entity_only":
        if entity_description.strip():
            narrative = entity_description.strip()
            source = "description"

    if not narrative and entity_description.strip():
        narrative = entity_description.strip()
        source = "description"

    narrative_source_text = (
        confirmed_content if source.startswith("content") else entity_description
    )

    if narrative:
        if _estimate_tokens(narrative) > target_available:
            narrative_at_target = _truncate_to_tokens(narrative, target_available)
            if narrative_at_target:
                narrative = narrative_at_target
                truncated = _estimate_tokens(narrative_source_text) > target_available
            elif _estimate_tokens(narrative) <= available_tokens:
                truncated = False
            else:
                narrative = _truncate_to_tokens(narrative, available_tokens)
                truncated = True

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
        "source": _map_source_to_code(source),
        "strategy": strategy,
        "category": category.value,
    }


def build_visual_prompt(
    entity_type: EntityType,
    entity_name: str,
    entity_description: str,
    confirmed_content: str,
    category: ContentCategory,
    max_tokens: int = 150,
    target_tokens: int = 75,
    use_llm_extraction: bool | None = None,
) -> dict[str, str | int | bool]:
    """
    Construye un prompt visual para generación de imagen.

    Args:
        entity_type: Tipo de entidad (character, creature, etc.)
        entity_name: Nombre de la entidad
        entity_description: Descripción general de la entidad
        confirmed_content: Contenido confirmado del EntityContent
        category: Categoría del contenido
        max_tokens: Límite máximo de tokens
        target_tokens: Token objetivo para el prompt
        use_llm_extraction: Override - si None, usa settings.prompt_strategy

    Returns:
        {
            "prompt": str,
            "token_count": int,
            "truncated": bool,
            "source": str,      # extended | scene | entity_desc | name_only
            "strategy": str,   # template | llm_extraction | fallback
            "category": str,
        }
    """
    if use_llm_extraction is None:
        use_llm_extraction = settings.prompt_strategy == "llm"

    if use_llm_extraction:
        try:
            from app.engine.rag_pipeline import invoke_prompt_extraction_pipeline

            llm_narrative = invoke_prompt_extraction_pipeline(
                content_text=confirmed_content,
                category=category,
                target_tokens=target_tokens,
            )

            if llm_narrative.strip():
                prefix = STYLE_PREFIX.get(entity_type, "fantasy art,")
                prefix_tokens = _estimate_tokens(prefix)
                suffix_tokens = _estimate_tokens(QUALITY_SUFFIX)
                name_tokens = _estimate_tokens(entity_name)
                overhead = prefix_tokens + suffix_tokens + name_tokens + 5
                target_available = max(10, target_tokens - overhead)

                narrative = _truncate_to_tokens(llm_narrative, target_available)

                parts = [prefix, entity_name]
                if narrative:
                    parts.append(narrative)
                parts.append(QUALITY_SUFFIX)

                prompt = ", ".join(p.strip().rstrip(",") for p in parts if p.strip())
                token_count = _estimate_tokens(prompt)

                return {
                    "prompt": prompt,
                    "token_count": token_count,
                    "truncated": _estimate_tokens(llm_narrative) > target_tokens,
                    "source": _map_source_to_code("content_direct"),
                    "strategy": "llm_extraction",
                    "category": category.value,
                }
        except Exception:
            pass

    # Template/deterministic strategy (o fallback cuando LLM falla)
    template_result = _build_with_template(
        entity_type=entity_type,
        entity_name=entity_name,
        entity_description=entity_description,
        confirmed_content=confirmed_content,
        category=category,
        max_tokens=max_tokens,
        target_tokens=target_tokens,
    )
    # Si use_llm_extraction era True pero falló, marcar como fallback
    # Si use_llm_extraction es False, usar la estrategia real
    if use_llm_extraction:
        template_result["strategy"] = "fallback"
    return template_result


def get_prompt_source_label(source: str) -> str:
    """Retorna el texto descriptivo para el usuario."""
    return PROMPT_SOURCE_LABELS.get(source, source)