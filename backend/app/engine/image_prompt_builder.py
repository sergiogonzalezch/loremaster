# Engine para construcción de prompts visuales para generación de imágenes
# Fusiona: prompt_builder + image_pipeline
# Usa LLM para extraer tipo específico + atributos visuales del contenido confirmado

import logging
import threading

from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings
from app.models.enums import ContentCategory
from app.models.entities import EntityType

from app.domain.image_prompt_rules import (
    _llm_instruction_by_entity_category,
    _TYPE_EXTRACT_PROMPT,
    _ATTRIBUTE_EXTRACT_SUFFIX,
)

logger = logging.getLogger(__name__)

_llm_semaphore = threading.Semaphore(settings.max_concurrent_llm_calls)

generation_chain = None

QUALITY_SUFFIX = "high quality, masterpiece, sharp focus, professional digital art"


def _get_generation_chain():
    global generation_chain
    if generation_chain is None:
        from app.engine.llm import llm

        generation_chain = llm | StrOutputParser()
    return generation_chain


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


def _extract_with_llm(
    content_text: str,
    entity_type: EntityType,
    category: ContentCategory,
    target_tokens: int,
) -> tuple[str, str]:
    """Usa el LLM para extraer tipo específico y atributos visuales."""
    instruction_key = (entity_type, category)
    llm_instruction = _llm_instruction_by_entity_category[instruction_key]
    type_prompt = _TYPE_EXTRACT_PROMPT.get(entity_type, "")

    logger.debug(
        "_extract_with_llm: entity_type=%s category=%s target_tokens=%d text_len=%d",
        entity_type,
        category,
        target_tokens,
        len(content_text),
    )

    try:
        with _llm_semaphore:
            chain = _get_generation_chain()

            tipo_result = chain.invoke(
                f"{type_prompt}\n\nTEXT:\n---\n{content_text}\n---"
            )
            tipo_especifico = tipo_result.strip().lower() if tipo_result else ""
            if not tipo_especifico:
                tipo_especifico = entity_type.value

            attributes_prompt = f"""{llm_instruction}

TEXT TO ANALYZE:
---
{content_text}
---

{_ATTRIBUTE_EXTRACT_SUFFIX}"""

            result = chain.invoke(attributes_prompt)
    except Exception as e:
        logger.error("LLM extraction failed: %s", e)
        raise RuntimeError("LLM service unavailable") from e

    if not result or not result.strip():
        logger.warning(
            "LLM returned empty result for entity_type=%s category=%s",
            entity_type,
            category,
        )
        return tipo_especifico, ""

    attributes = _truncate_to_tokens(result.strip(), target_tokens)
    logger.info(
        "Extracted %d tokens for entity_type=%s category=%s, tipo=%s",
        _estimate_tokens(attributes),
        entity_type,
        category,
        tipo_especifico,
    )

    return tipo_especifico, attributes


def build_visual_prompt(
    entity_type: EntityType,
    confirmed_content: str,
    category: ContentCategory,
    max_tokens: int = 512,
) -> dict[str, str | int]:
    """
    Construye un prompt visual para generación de imagen usando LLM.

    El prompt NO incluye el nombre de la entidad - solo atributos visuales
    que los modelos de imagen pueden interpretar correctamente.

    Args:
        entity_type: Tipo de entidad (character, creature, etc.)
        confirmed_content: Contenido confirmado del EntityContent
        category: Categoría del contenido
        max_tokens: Límite de tokens para el prompt (default 512).
            El límite de 512 es el máximo del text encoder de Stable Diffusion.
            Reservamos 15 tokens (~60 chars) para prefijo (tipo específico) y sufijo (quality).

    Returns:
        {
            "prompt": str,
            "token_count": int,
            "category": str,
        }

    Raises:
        RuntimeError: Si el LLM no está disponible
    """
    tipo_especifico, llm_attributes = _extract_with_llm(
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
        "category": category.value,
    }
