# tests/test_prompt_builder.py

from app.domain.prompt_builder import build_visual_prompt, _estimate_tokens
from app.models.entities import EntityType
from app.models.enums import ContentCategory


def test_pb_01_token_count_within_max():
    """El prompt nunca supera max_tokens (con template)."""
    long_content = "palabra " * 300
    result = build_visual_prompt(
        entity_type=EntityType.character,
        entity_name="Aragorn",
        entity_description="Un guerrero valiente",
        confirmed_content=long_content,
        category=ContentCategory.extended_description,
        max_tokens=150,
        use_llm_extraction=False,
    )
    assert result["token_count"] <= 150


def test_pb_02_short_content_not_truncated():
    """Contenido corto no se marca como truncado."""
    result = build_visual_prompt(
        entity_type=EntityType.character,
        entity_name="Aria",
        entity_description="Elfa arquera",
        confirmed_content="Una elfa con arco de plata",
        category=ContentCategory.extended_description,
        max_tokens=150,
        use_llm_extraction=False,
    )
    assert result["truncated"] is False


def test_pb_03_long_content_is_truncated():
    """Contenido muy largo se trunca y se marca."""
    result = build_visual_prompt(
        entity_type=EntityType.character,
        entity_name="X",
        entity_description="",
        confirmed_content="palabra " * 200,
        category=ContentCategory.extended_description,
        max_tokens=150,
        use_llm_extraction=False,
    )
    assert result["truncated"] is True
    assert result["token_count"] <= 150


def test_pb_04_empty_content_falls_back_to_description():
    """Sin contenido RAG usa la descripción de entidad."""
    result = build_visual_prompt(
        entity_type=EntityType.item,
        entity_name="Espada Élfica",
        entity_description="Hoja forjada con luz de luna",
        confirmed_content="",
        category=ContentCategory.extended_description,
        max_tokens=150,
        use_llm_extraction=False,
    )
    assert result["source"] == "entity_desc"
    assert "Hoja forjada" in result["prompt"]


def test_pb_05_empty_everything_falls_back_to_name_only():
    """Sin contenido ni descripción usa solo el nombre."""
    result = build_visual_prompt(
        entity_type=EntityType.character,
        entity_name="Corto",
        entity_description="",
        confirmed_content="",
        category=ContentCategory.extended_description,
        max_tokens=150,
        use_llm_extraction=False,
    )
    assert result["source"] == "name_only"
    assert "Corto" in result["prompt"]


def test_pb_06_backstory_strategy():
    """Backstory usa estrategia entity_only."""
    result = build_visual_prompt(
        entity_type=EntityType.character,
        entity_name="Frodo",
        entity_description="Hobbit del Condado",
        confirmed_content="El sol caía sobre las colinas.",
        category=ContentCategory.backstory,
        max_tokens=150,
        use_llm_extraction=False,
    )
    assert result["strategy"] == "entity_only"
    assert result["prompt"]


def test_pb_07_extended_description_strategy():
    """Extended description usa strategy direct."""
    result = build_visual_prompt(
        entity_type=EntityType.character,
        entity_name="Gandalf",
        entity_description="Mago gris",
        confirmed_content="Barba larga y sombrero gris",
        category=ContentCategory.extended_description,
        max_tokens=150,
        use_llm_extraction=False,
    )
    assert result["strategy"] == "direct"
    assert "Barba" in result["prompt"]


def test_pb_08_backstory_ignores_content():
    """Backstory ignora el contenido narrativo."""
    result = build_visual_prompt(
        entity_type=EntityType.character,
        entity_name="Frodo",
        entity_description="Hobbit del Shire",
        confirmed_content="El sol caía sobre las colinas. Las flores brillaban. Después llegó la oscuridad.",
        category=ContentCategory.backstory,
        max_tokens=150,
        use_llm_extraction=False,
    )
    assert result["strategy"] == "entity_only"
    assert "Hobbit del Shire" in result["prompt"]


def test_pb_09_scene_extracts_sentences():
    """Scene extrae primeras oraciones."""
    result = build_visual_prompt(
        entity_type=EntityType.character,
        entity_name="Frodo",
        entity_description="Hobbit del Shire",
        confirmed_content="El sol caía sobre las colinas. Las flores brillaban en el viento. Después llegó la oscuridad.",
        category=ContentCategory.scene,
        max_tokens=150,
        use_llm_extraction=False,
    )
    assert result["strategy"] == "first_sentences"
    assert "sol caía" in result["prompt"]


def test_estimate_tokens_counts_correctly():
    """_estimate_tokens cuenta aproximadamente 4 chars por token."""
    assert _estimate_tokens("abcd") == 1
    assert _estimate_tokens("a b c d") == 1
    assert _estimate_tokens("") == 0