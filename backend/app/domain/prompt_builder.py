# app/domain/prompt_builder.py

from app.models.entities import EntityType

# ── Prefijos por tipo ──────────────────────────────────────────────────────────
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

# ── Sufijo de calidad fijo ─────────────────────────────────────────────────────
QUALITY_SUFFIX = "high quality, masterpiece, sharp focus, professional digital art"


# ── Heurística de tokens (igual que frontend) ──────────────────────────────────
def _estimate_tokens(text: str) -> int:
    """~4 chars por token. Consistente con estimateTokens() del frontend."""
    return max(0, len(text) // 4)


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Trunca texto al número de tokens aproximado preservando palabras completas."""
    if _estimate_tokens(text) <= max_tokens:
        return text
    # Cortar por palabras hasta caber en el límite
    words = text.split()
    result: list[str] = []
    for word in words:
        candidate = " ".join(result + [word])
        if _estimate_tokens(candidate) > max_tokens:
            break
        result.append(word)
    return " ".join(result)


def build_visual_prompt(
    entity_type: EntityType,
    entity_name: str,
    entity_description: str,
    confirmed_content: str,
    max_tokens: int = 150,
    target_tokens: int = 75,
) -> dict[str, str | int]:
    """
    Construye un prompt visual para generación de imagen.

    Retorna:
        {
            "prompt": str,          # prompt final
            "token_count": int,     # tokens estimados
            "truncated": bool,      # si se truncó el contenido RAG
            "source": str,          # "content" | "description" | "name_only"
        }
    """
    prefix = STYLE_PREFIX.get(entity_type, "fantasy art,")

    # Tokens disponibles para contexto narrativo
    # (máx - prefijo - sufijo - nombre - separadores)
    prefix_tokens = _estimate_tokens(prefix)
    suffix_tokens = _estimate_tokens(QUALITY_SUFFIX)
    name_tokens = _estimate_tokens(entity_name)
    overhead = prefix_tokens + suffix_tokens + name_tokens + 5  # separadores

    available_tokens = max_tokens - overhead
    target_available = target_tokens - overhead

    # Estrategia: intentar usar confirmed_content primero,
    # fallback a description, fallback a solo nombre
    source = "content"
    narrative = confirmed_content.strip()

    if not narrative:
        source = "description"
        narrative = entity_description.strip()

    if not narrative:
        source = "name_only"
        narrative = ""

    # Intentar encajar en target primero
    truncated = False
    if narrative and _estimate_tokens(narrative) > target_available:
        narrative_truncated = _truncate_to_tokens(narrative, target_available)
        if narrative_truncated:
            narrative = narrative_truncated
            truncated = True
        elif _estimate_tokens(narrative) <= available_tokens:
            # No cabe en target pero sí en max: mantener sin truncar a target
            truncated = False
        else:
            narrative = _truncate_to_tokens(narrative, available_tokens)
            truncated = True

    # Ensamblar
    parts = [prefix, entity_name]
    if narrative:
        parts.append(narrative)
    parts.append(QUALITY_SUFFIX)

    prompt = ", ".join(p.rstrip(",") for p in parts if p)
    token_count = _estimate_tokens(prompt)

    return {
        "prompt": prompt,
        "token_count": token_count,
        "truncated": truncated,
        "source": source,
    }
