# Engine para extracción de atributos visuales de imágenes
# Este pipeline es independiente del RAG (texto)
# Usa el LLM para extraer atributos visuales del contenido confirmado

import logging
import threading

from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings
from app.models.enums import ContentCategory
from app.models.entities import EntityType

logger = logging.getLogger(__name__)

_llm_semaphore = threading.Semaphore(settings.max_concurrent_llm_calls)

generation_chain = None

_ATTRIBUTE_EXTRACT_SUFFIX = "Respond IN ENGLISH only with the list of visual attributes, without explanation."

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


def invoke_prompt_extraction(
    content_text: str,
    entity_type: EntityType,
    category: ContentCategory,
    target_tokens: int = 150,
) -> tuple[str, str]:
    """Usa el LLM para extraer tipo específico y atributos visuales de un texto.

    Args:
        content_text: Texto del EntityContent confirmado
        entity_type: Tipo de entidad (character, creature, location, faction, item)
        category: Categoría del contenido (determina la instrucción)
        target_tokens: Límite de tokens para los atributos

    Returns:
        (tipo_especifico, atributos_visuales)

    Raises:
        RuntimeError: Si el LLM no está disponible
    """
    from app.domain.image_prompt_rules import (
        _llm_instruction_by_entity_category,
        _TYPE_EXTRACT_PROMPT,
    )

# 
    instruction_key = (entity_type, category)
    llm_instruction = _llm_instruction_by_entity_category[instruction_key]
    type_prompt = _TYPE_EXTRACT_PROMPT.get(entity_type, "")

    logger.debug(
        "invoke_prompt_extraction: entity_type=%s category=%s target_tokens=%d text_len=%d",
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
        logger.warning("LLM returned empty result for entity_type=%s category=%s", entity_type, category)
        return tipo_especifico, ""

    truncated = _truncate_to_tokens(result.strip(), target_tokens)
    logger.info("Extracted %d tokens for entity_type=%s category=%s, tipo=%s", _estimate_tokens(truncated), entity_type, category, tipo_especifico)

    return tipo_especifico, truncated