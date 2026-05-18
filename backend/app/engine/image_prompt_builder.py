"""Motor para construcción de prompts visuales para generación de imágenes.

Usa LLM para extraer tipo específico y atributos visuales del contenido confirmado
en una sola llamada, produciendo un prompt directamente usable por modelos de imagen.
"""

import logging
import threading

from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings
from app.domain.image_prompt_rules import build_combined_prompt
from app.engine.llm import get_llm
from app.models.db.entity import EntityType
from app.models.enums import ContentCategory

logger = logging.getLogger(__name__)

_llm_semaphore = threading.Semaphore(settings.max_concurrent_llm_calls)

_generation_chain = get_llm(settings.image_prompt_model) | StrOutputParser()
"""Cadena de extracción visual (prompt → image_prompt_model → parser)."""

QUALITY_SUFFIX = "high quality, masterpiece, sharp focus, professional digital art"
"""Sufijo de calidad añadido a todos los prompts visuales."""


def _estimate_tokens(text: str) -> int:
    """Estima tokens usando ~4 caracteres por token."""
    return max(0, len(text) // 4)


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Trunca el texto a max_tokens preservando palabras completas."""
    if _estimate_tokens(text) <= max_tokens:
        return text
    words = text.split()
    result: list[str] = []
    for word in words:
        candidate = " ".join([*result, word])
        if _estimate_tokens(candidate) > max_tokens:
            break
        result.append(word)
    return " ".join(result)


def _extract_with_llm(
    content_text: str,
    entity_type: EntityType,
    category: ContentCategory,
    target_tokens: int,
) -> str:
    """Usa el LLM para extraer tipo y atributos visuales en una sola llamada.

    Retorna una cadena comma-separated directamente usable como prompt de imagen.
    Formato: <tipo>, <atributo1>, <atributo2>, ...

    Raises:
        RuntimeError: Si el LLM no está disponible.

    """
    prompt = build_combined_prompt(entity_type, category, content_text)

    logger.debug(
        "_extract_with_llm: entity_type=%s category=%s target_tokens=%d text_len=%d",
        entity_type,
        category,
        target_tokens,
        len(content_text),
    )

    try:
        with _llm_semaphore:
            result = _generation_chain.invoke(prompt)
    except Exception as e:
        logger.exception("LLM extraction failed")
        msg = "LLM service unavailable"
        raise RuntimeError(msg) from e

    if not result or not result.strip():
        logger.warning(
            "LLM returned empty result for entity_type=%s category=%s",
            entity_type,
            category,
        )
        return entity_type.value

    attributes = _truncate_to_tokens(result.strip(), target_tokens)
    logger.info(
        "Extracted %d tokens for entity_type=%s category=%s",
        _estimate_tokens(attributes),
        entity_type,
        category,
    )
    return attributes


def build_visual_prompt(
    entity_type: EntityType,
    confirmed_content: str,
    category: ContentCategory,
    max_tokens: int = 512,
) -> dict[str, str | int]:
    """Construye un prompt visual para generación de imagen usando LLM.

    El prompt NO incluye el nombre de la entidad — solo atributos visuales
    que los modelos de imagen pueden interpretar correctamente.

    Args:
        entity_type: Tipo de entidad (character, creature, etc.)
        confirmed_content: Contenido confirmado del EntityContent
        category: Categoría del contenido
        max_tokens: Límite de tokens para el prompt (default 512).
            El límite de 512 es el máximo del text encoder de Stable Diffusion.

    Returns:
        {
            "prompt": str,
            "token_count": int,
            "category": str,
        }

    Raises:
        RuntimeError: Si el LLM no está disponible

    """
    suffix_tokens = _estimate_tokens(QUALITY_SUFFIX)
    available = max(10, max_tokens - suffix_tokens - 14)

    attributes = _extract_with_llm(
        content_text=confirmed_content,
        entity_type=entity_type,
        category=category,
        target_tokens=available,
    )

    prompt = f"{attributes}, {QUALITY_SUFFIX}"
    token_count = _estimate_tokens(prompt)

    return {
        "prompt": prompt,
        "token_count": token_count,
        "category": category.value,
    }
