import logging
import threading

from langchain_core.output_parsers import StrOutputParser

from app.core.exceptions import NoContextAvailableError
from app.domain.prompt_templates import render_prompt
from app.engine.llm import chain, llm
from app.engine.rag import search_context
from app.core.config import settings
from app.models.enums import ContentCategory
from app.models.entities import EntityType

logger = logging.getLogger(__name__)

_llm_instruction_by_entity_category = {
    (EntityType.character, ContentCategory.extended_description): (
        "Del siguiente texto que describe la apariencia física de un personaje, "
        "extrae SOLO atributos visuales para generación de imagen: género aproximado, edad, "
        "tipo de cuerpo, tono de piel, color y estilo de cabello, color de ojos, "
        "rasgos faciales distintivos, tipo de vestimenta, accesorios, expresión facial, postura. "
        "Formato: lista de atributos separados por coma (ej: female, young adult, slender, fair skin, "
        "long dark hair, brown eyes, angular face, elegant blue gown, pearl necklace, serene expression). "
        "IGNORA: narrativa, motivaciones, emociones, historia, nombres."
    ),
    (EntityType.character, ContentCategory.backstory): (
        "Del siguiente texto de trasfondo histórico de un personaje, "
        "extrae SOLO atributos visuales: vestimenta de época, época histórica, entorno donde creció, "
        "condición social reflejada en ropa, objetos que porta, estado físico de esa época. "
        "Formato: lista de atributos visuales separados por coma. "
        "IGNORA: nombres, fechas, eventos históricos, motivaciones."
    ),
    (EntityType.character, ContentCategory.scene): (
        "De la siguiente escena, extrae SOLO atributos visuales del personaje: "
        "acción que realiza, postura, vestimenta actual, expresión, objetos que porta, "
        "iluminación sobre él, interacción con el entorno. "
        "Formato: lista de atributos separados por coma. "
        "IGNORA: diálogo, pensamientos, emociones."
    ),
    (EntityType.character, ContentCategory.chapter): (
        "Del siguiente capítulo, extrae SOLO los atributos visuales del personaje en la escena de apertura: "
        "posición en el espacio, vestimenta, expresión, iluminación, atmósfera. "
        "Formato: lista de atributos separados por coma. "
        "IGNORA: trama, desarrollo, personajes secundarios."
    ),
    (EntityType.creature, ContentCategory.extended_description): (
        "Del siguiente texto que describe una criatura, extrae SOLO atributos visuales: "
        "especie, tipo de cuerpo, color primario, color secundario, textura de piel/pelaje/escamas, "
        "características distintivas (alas, cola, cuernos, garras), tamaño aproximado, postura típica, "
        "elementos fantásticos (magia, energía, luminescencia). "
        "Formato: lista de atributos separados por coma. "
        "IGNORA: nombre, habilidades, comportamiento, historia."
    ),
    (EntityType.creature, ContentCategory.backstory): (
        "Del siguiente texto de trasfondo de una criatura, "
        "extrae SOLO atributos visuales: entorno nativo, condición física en esa época, "
        "características distintivas que tuvo desde joven, atmósfera del lugar. "
        "Formato: lista de atributos separados por coma. "
        "IGNORA: nombre, eventos, motivaciones."
    ),
    (EntityType.creature, ContentCategory.scene): (
        "De la siguiente escena, extrae SOLO atributos visuales de la criatura: "
        "posición, acción, expresión corporal, interacción con entorno, iluminación. "
        "Formato: lista de atributos separados por coma. "
        "IGNORA: diálogo, pensamientos."
    ),
    (EntityType.creature, ContentCategory.chapter): (
        "Del siguiente capítulo, extrae SOLO atributos visuales de la criatura en la escena de apertura: "
        "posición, acción, entorno, iluminación, atmósfera. "
        "Formato: lista de atributos separados por coma. "
        "IGNORA: trama, desarrollo."
    ),
    (EntityType.location, ContentCategory.extended_description): (
        "Del siguiente texto que describe un lugar, extrae SOLO atributos visuales: "
        "tipo de entorno (bosque, castillo, ciudad, caverna, etc.), estilo arquitectónico, "
        "época/diseño, materiales predominantes, elementos distintivos, iluminación típica, "
        "escala (diminuto, enorme, vasto), atmósfera (misterioso, acogedor, peligroso). "
        "Formato: lista de atributos separados por coma. "
        "IGNORA: historia, eventos, personajes."
    ),
    (EntityType.location, ContentCategory.backstory): (
        "Del siguiente texto histórico de un lugar, "
        "extrae SOLO atributos visuales: apariencia original del lugar, época dorada, "
        "arquitectura de ese período, estado actual vs pasado, símbolo distintivo. "
        "Formato: lista de atributos separados por coma. "
        "IGNORA: eventos, fechas, personajes."
    ),
    (EntityType.location, ContentCategory.scene): (
        "De la siguiente escena, extrae SOLO atributos visuales del lugar: "
        "elementos en primer plano, iluminación, clima, atmósfera, acción que ocurre, "
        "elementos destacados visibles. "
        "Formato: lista de atributos separados por coma. "
        "IGNORA: diálogo, pensamientos."
    ),
    (EntityType.location, ContentCategory.chapter): (
        "Del siguiente capítulo, extrae SOLO atributos visuales del lugar en la escena de apertura: "
        "descripción inicial del espacio, iluminación, atmósfera, elementos presentes. "
        "Formato: lista de atributos separados por coma. "
        "IGNORA: trama, desarrollo."
    ),
    (EntityType.faction, ContentCategory.extended_description): (
        "Del siguiente texto que describe una facción, extrae SOLO atributos visuales: "
        "estilo del emblema/heraldry, símbolo principal, paleta de colores, "
        "material appearance (metálico, tejido, mágico), mood (amenazante, noble, misterioso), "
        "elementos arquitectónicos asociados, tipo de escritura/símbolos. "
        "Formato: lista de atributos separados por coma. "
        "IGNORA: historia, motivaciones, miembros."
    ),
    (EntityType.faction, ContentCategory.backstory): (
        "Del siguiente texto de trasfondo de una facción, "
        "extrae SOLO atributos visuales de su origen: estilo de la época, símbolos originales, "
        "colores fundacionales, elementos de poder de ese tiempo. "
        "Formato: lista de atributos separados por coma. "
        "IGNORA: eventos, fechas, personajes."
    ),
    (EntityType.faction, ContentCategory.scene): (
        "De la siguiente escena que involucra una facción, "
        "extrae SOLO atributos visuales: cómo se manifiesta el símbolo, colores dominantes, "
        "presencia de miembros, atmósfera. "
        "Formato: lista de atributos separados por coma. "
        "IGNORA: diálogo, pensamientos."
    ),
    (EntityType.faction, ContentCategory.chapter): (
        "Del siguiente capítulo, extrae SOLO atributos visuales de la facción en la escena de apertura: "
        "símbolo visible, colores, presencia, atmósfera. "
        "Formato: lista de atributos separados por coma. "
        "IGNORA: trama, desarrollo."
    ),
    (EntityType.item, ContentCategory.extended_description): (
        "Del siguiente texto que describe un objeto, extrae SOLO atributos visuales: "
        "tipo de objeto (espada, amuleto, libro, etc.), material principal, material secundario, "
        "color predominante, color secundario, textura, condición (nuevo, antiguo, dañado, mágico), "
        "tamaño aproximado, elementos decorativos, indicadores mágicos (brillo, runas, energía). "
        "Formato: lista de atributos separados por coma. "
        "IGNORA: historia, propiedades, uso."
    ),
    (EntityType.item, ContentCategory.backstory): (
        "Del siguiente texto de trasfondo de un objeto, "
        "extrae SOLO atributos visuales de su origen: apariencia original, material de la época, "
        "símbolos grabados, condición en ese tiempo. "
        "Formato: lista de atributos separados por coma. "
        "IGNORA: eventos, propietarios, fechas."
    ),
    (EntityType.item, ContentCategory.scene): (
        "De la siguiente escena donde aparece el objeto, "
        "extrae SOLO atributos visuales: cómo se muestra, posición, iluminación, "
        "interacción con personajes, estado visible. "
        "Formato: lista de atributos separados por coma. "
        "IGNORA: diálogo, pensamientos."
    ),
    (EntityType.item, ContentCategory.chapter): (
        "Del siguiente capítulo, extrae SOLO atributos visuales del objeto en la escena de apertura: "
        "presencia, posición, iluminación, estado visible. "
        "Formato: lista de atributos separados por coma. "
        "IGNORA: trama, desarrollo."
    ),
}

_llm_instruction_fallback = (
    "Del siguiente texto, extrae SOLO descriptores visuales relevantes para generación de imagen: "
    "colores, formas, texturas, materiales, atmósfera, iluminación, elementos destacados. "
    "Formato: lista de atributos separados por coma. "
    "IGNORA: narrativa, personajes, historia, nombres."
)

# Limits concurrent LLM calls to avoid overwhelming Ollama (local, single-threaded).
_llm_semaphore = threading.Semaphore(settings.max_concurrent_llm_calls)

# Plain chain for pre-rendered prompts used by invoke_generation_pipeline.
generation_chain = llm | StrOutputParser()


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


def invoke_prompt_extraction_pipeline(
    content_text: str,
    entity_type: EntityType,
    category: ContentCategory,
    target_tokens: int = 150,
) -> str:
    """Usa el LLM para extraer atributos visuales de un texto por tipo de entidad.

    Args:
        content_text: Texto del EntityContent confirmado
        entity_type: Tipo de entidad (character, creature, location, faction, item)
        category: Categoría del contenido (determina la instrucción)
        target_tokens: Límite de tokens para el resultado

    Returns:
        Atributos visuales extraídos por el LLM (sin nombre de entidad)

    Raises:
        RuntimeError: Si el LLM no está disponible
    """
    instruction_key = (entity_type, category)
    llm_instruction = _llm_instruction_by_entity_category.get(
        instruction_key,
        _llm_instruction_fallback,
    )

    full_prompt = f"""{llm_instruction}

TEXTO A ANALIZAR:
---
{content_text}
---

Responde únicamente con la lista de atributos visuales, sin explicación."""

    logger.debug(
        "invoke_prompt_extraction_pipeline: entity_type=%s category=%s target_tokens=%d text_len=%d",
        entity_type,
        category,
        target_tokens,
        len(content_text),
    )

    try:
        with _llm_semaphore:
            result = generation_chain.invoke(full_prompt)
    except Exception as e:
        logger.error("LLM extraction failed: %s", e)
        raise RuntimeError("LLM service unavailable") from e

    if not result or not result.strip():
        logger.warning("LLM returned empty result for entity_type=%s category=%s", entity_type, category)
        return ""

    truncated = _truncate_to_tokens(result.strip(), target_tokens)
    logger.info("Extracted %d tokens for entity_type=%s category=%s", _estimate_tokens(truncated), entity_type, category)

    return truncated


def _retrieve_context(
    collection_id: str,
    query: str,
    extra_context: str = "",
) -> tuple[str, int]:
    """Search Qdrant, merge extra_context, return (context_str, num_chunks).

    Raises:
        RuntimeError: If Qdrant is unavailable.
        NoContextAvailableError: If no context is found from any source.
    """
    try:
        context_chunks = search_context(
            collection_id=collection_id,
            query=query,
            top_k=settings.top_k,
            score_threshold=settings.rag_score_threshold,
        )
    except Exception as e:
        logger.error("Qdrant search failed for collection %s: %s", collection_id, e)
        raise RuntimeError("Vector search unavailable") from e

    rag_context = "\n\n---\n\n".join(context_chunks) if context_chunks else ""
    parts = [p for p in (extra_context, rag_context) if p]
    context = "\n\n---\n\n".join(parts)

    if not context.strip():
        raise NoContextAvailableError()

    return context, len(context_chunks)


def invoke_rag_pipeline(
    collection_id: str,
    query: str,
    extra_context: str = "",
) -> tuple[str, int]:
    """Search RAG context, build prompt, invoke LLM, return (answer, num_chunks).

    Raises:
        RuntimeError: If Qdrant or the LLM is unavailable.
        NoContextAvailableError: If there is no context at all (no chunks and no extra_context).
    """
    logger.debug(
        "invoke_rag_pipeline: collection=%s threshold=%.2f top_k=%d query='%.80s'",
        collection_id,
        settings.rag_score_threshold,
        settings.top_k,
        query,
    )

    context, num_chunks = _retrieve_context(collection_id, query, extra_context)

    try:
        with _llm_semaphore:
            answer = chain.invoke({"context": context, "query": query})
    except Exception as e:
        logger.error("LLM generation failed for collection %s: %s", collection_id, e)
        raise RuntimeError("LLM service unavailable") from e

    logger.info(
        "RAG response generated for collection %s using %d chunk(s)",
        collection_id,
        num_chunks,
    )
    return answer, num_chunks


def invoke_generation_pipeline(
    collection_id: str,
    entity_name: str,
    entity_type: str,
    category: ContentCategory,
    query: str,
    extra_context: str = "",
) -> tuple[str, int]:
    """Entity-aware RAG pipeline using category-specific prompt templates.

    Raises:
        RuntimeError: If Qdrant or the LLM is unavailable.
        NoContextAvailableError: If there is no context at all (no chunks and no extra_context).
    """
    logger.debug(
        "invoke_generation_pipeline: collection=%s entity='%s' category=%s threshold=%.2f top_k=%d query='%.80s'",
        collection_id,
        entity_name,
        category,
        settings.rag_score_threshold,
        settings.top_k,
        query,
    )

    context, num_chunks = _retrieve_context(collection_id, query, extra_context)

    rendered_prompt = render_prompt(
        category=category,
        entity_name=entity_name,
        entity_type=entity_type,
        context=context,
        query=query,
    )

    try:
        with _llm_semaphore:
            answer = generation_chain.invoke(rendered_prompt)
    except Exception as e:
        logger.error(
            "LLM generation failed for entity '%s' collection %s: %s",
            entity_name,
            collection_id,
            e,
        )
        raise RuntimeError("LLM service unavailable") from e

    logger.info(
        "Generation pipeline completed for entity '%s' (category=%s) using %d chunk(s)",
        entity_name,
        category,
        num_chunks,
    )
    return answer, num_chunks