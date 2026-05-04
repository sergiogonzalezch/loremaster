"""
Construcción de prompts visuales para generación de imágenes.
Usa invoke_prompt_extraction() del image_pipeline para extraer atributos via LLM.
"""

from app.models.entities import EntityType
from app.models.enums import ContentCategory

_ENTITY_TYPE_VISUAL = {
    EntityType.character: "personaje",
    EntityType.creature: "criatura",
    EntityType.location: "lugar",
    EntityType.faction: "facción",
    EntityType.item: "objeto",
}

QUALITY_SUFFIX = "high quality, masterpiece, sharp focus, professional digital art"


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


PROMPT_SOURCE_LABELS = {
    "llm_extraction": "Extraído vía LLM",
    "extended": "Basado en la descripción extendida",
}


def build_visual_prompt(
    entity_type: EntityType,
    entity_name: str,
    entity_description: str,
    confirmed_content: str,
    category: ContentCategory,
    max_tokens: int = 150,
) -> dict[str, str | int | bool]:
    """
    Construye un prompt visual para generación de imagen usando LLM.

    El prompt NO incluye el nombre de la entidad - solo atributos visuales
    que los modelos de imagen pueden interpretar correctamente.

    Args:
        entity_type: Tipo de entidad (character, creature, etc.)
        entity_name: Nombre de la entidad (no se incluye en prompt)
        entity_description: Descripción general de la entidad
        confirmed_content: Contenido confirmado del EntityContent
        category: Categoría del contenido
        max_tokens: Límite de tokens para el prompt (default 150)

    Returns:
        {
            "prompt": str,
            "token_count": int,
            "truncated": bool,
            "source": str,
            "strategy": str,
            "category": str,
        }

    Raises:
        RuntimeError: Si el LLM no está disponible
    """
    from app.engine.image_pipeline import invoke_prompt_extraction

    tipo_especifico, llm_attributes = invoke_prompt_extraction(
        content_text=confirmed_content,
        entity_type=entity_type,
        category=category,
        target_tokens=max_tokens - 15,
    )

    prefix = f"{tipo_especifico}, "
    suffix_tokens = _estimate_tokens(QUALITY_SUFFIX)
    prefix_tokens = _estimate_tokens(prefix)
    overhead = prefix_tokens + suffix_tokens + 5
    available = max(10, max_tokens - overhead)

    attributes = _truncate_to_tokens(llm_attributes, available)

    parts = [prefix]
    if attributes:
        parts.append(attributes)
    parts.append(QUALITY_SUFFIX)

    prompt = ", ".join(p.strip().rstrip(",") for p in parts if p.strip())
    token_count = _estimate_tokens(prompt)

    return {
        "prompt": prompt,
        "token_count": token_count,
        "truncated": _estimate_tokens(llm_attributes) > max_tokens,
        "source": "llm_extraction",
        "strategy": "llm_extraction",
        "category": category.value,
    }


def get_prompt_source_label(source: str) -> str:
    """Retorna el texto descriptivo para el usuario."""
    return PROMPT_SOURCE_LABELS.get(source, source)