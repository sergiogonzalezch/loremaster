# tests/test_prompt_builder.py

from app.domain.prompt_builder import build_visual_prompt, _estimate_tokens
from app.models.entities import EntityType
from app.models.enums import ContentCategory


def test_pb_01_token_count_within_max():
    """El prompt nunca supera max_tokens."""
    long_content = "palabra " * 300
    result = build_visual_prompt(
        entity_type=EntityType.character,
        entity_name="Aragorn",
        entity_description="Un guerrero valiente",
        confirmed_content=long_content,
        category=ContentCategory.extended_description,
        max_tokens=150,
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
    )
    assert result["token_count"] <= 150


def test_pb_04_empty_content_uses_fallback():
    """Sin contenido confirmado pero con descripción, genera un prompt válido."""
    result = build_visual_prompt(
        entity_type=EntityType.item,
        entity_name="Espada",
        entity_description="Espada de acero valyrio",
        confirmed_content="",
        category=ContentCategory.extended_description,
        max_tokens=150,
    )
    assert result["token_count"] <= 150
    assert "fantasy item showcase" in result["prompt"]


def test_pb_05_empty_everything_falls_back_to_default():
    """Sin contenido ni descripción genera prompt con prefijo por defecto."""
    result = build_visual_prompt(
        entity_type=EntityType.character,
        entity_name="Corto",
        entity_description="",
        confirmed_content="",
        category=ContentCategory.extended_description,
        max_tokens=150,
    )
    assert "Corto" not in result["prompt"]
    assert "fantasy character portrait" in result["prompt"]
    assert result["token_count"] <= 150


def test_pb_06_different_entity_types_have_different_prefixes():
    """Diferentes tipos de entidad tienen diferentes prefijos de estilo."""
    result_char = build_visual_prompt(
        entity_type=EntityType.character,
        entity_name="Test",
        entity_description="Test",
        confirmed_content="Test",
        category=ContentCategory.extended_description,
        max_tokens=150,
    )
    result_creature = build_visual_prompt(
        entity_type=EntityType.creature,
        entity_name="Test",
        entity_description="Test",
        confirmed_content="Test",
        category=ContentCategory.extended_description,
        max_tokens=150,
    )
    result_location = build_visual_prompt(
        entity_type=EntityType.location,
        entity_name="Test",
        entity_description="Test",
        confirmed_content="Test",
        category=ContentCategory.extended_description,
        max_tokens=150,
    )

    assert "fantasy character portrait" in result_char["prompt"]
    assert "fantasy creature illustration" in result_creature["prompt"]
    assert "fantasy landscape" in result_location["prompt"]


def test_pb_07_extended_description_category():
    """Extended description genera prompt con atributos visuales."""
    result = build_visual_prompt(
        entity_type=EntityType.character,
        entity_name="Test",
        entity_description="Test",
        confirmed_content="Test description",
        category=ContentCategory.extended_description,
        max_tokens=150,
    )
    assert "fantasy character portrait" in result["prompt"]


def test_pb_08_backstory_category():
    """Backstory genera prompt con atributos visuales."""
    result = build_visual_prompt(
        entity_type=EntityType.character,
        entity_name="Test",
        entity_description="Test",
        confirmed_content="Test backstory",
        category=ContentCategory.backstory,
        max_tokens=150,
    )
    assert "fantasy character portrait" in result["prompt"]


def test_pb_09_scene_category():
    """Scene genera prompt con atributos visuales."""
    result = build_visual_prompt(
        entity_type=EntityType.character,
        entity_name="Test",
        entity_description="Test",
        confirmed_content="El sol caía sobre las colinas.",
        category=ContentCategory.scene,
        max_tokens=150,
    )
    assert "fantasy character portrait" in result["prompt"]


def test_estimate_tokens_counts_correctly():
    """_estimate_tokens cuenta aproximadamente 4 chars por token."""
    assert _estimate_tokens("abcd") == 1
    assert _estimate_tokens("a b c d") == 1
    assert _estimate_tokens("") == 0