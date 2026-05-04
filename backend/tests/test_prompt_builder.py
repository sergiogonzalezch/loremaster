# tests/test_prompt_builder.py
# Tests para app.engine.image_prompt_builder

from app.engine.image_prompt_builder import build_visual_prompt, _estimate_tokens
from app.models.entities import EntityType
from app.models.enums import ContentCategory


def test_pb_01_token_count_within_max():
    """El prompt nunca supera max_tokens."""
    long_content = "palabra " * 300
    result = build_visual_prompt(
        entity_type=EntityType.character,
        confirmed_content=long_content,
        category=ContentCategory.extended_description,
        max_tokens=512,
    )
    assert result["token_count"] <= 512


def test_pb_02_short_content_returns_valid_prompt():
    """Contenido corto genera un prompt válido."""
    result = build_visual_prompt(
        entity_type=EntityType.character,
        confirmed_content="Una elfa con arco de plata",
        category=ContentCategory.extended_description,
        max_tokens=512,
    )
    assert "prompt" in result
    assert result["token_count"] > 0
    assert result["category"] == "extended_description"


def test_pb_03_long_content_truncates():
    """Contenido muy largo se trunca pero no supera max_tokens."""
    result = build_visual_prompt(
        entity_type=EntityType.character,
        confirmed_content="palabra " * 200,
        category=ContentCategory.extended_description,
        max_tokens=512,
    )
    assert result["token_count"] <= 512


def test_pb_04_different_entity_types():
    """Diferentes tipos de entidad retornan prompts válidos."""
    for entity_type in [
        EntityType.character,
        EntityType.creature,
        EntityType.location,
        EntityType.faction,
        EntityType.item,
    ]:
        result = build_visual_prompt(
            entity_type=entity_type,
            confirmed_content="Test content",
            category=ContentCategory.extended_description,
            max_tokens=512,
        )
        assert "prompt" in result
        assert "token_count" in result


def test_pb_05_all_categories_supported():
    """Todas las categorías de imagen generan prompts."""
    for category in [
        ContentCategory.extended_description,
        ContentCategory.backstory,
        ContentCategory.scene,
        ContentCategory.chapter,
    ]:
        result = build_visual_prompt(
            entity_type=EntityType.character,
            confirmed_content="Test",
            category=category,
            max_tokens=512,
        )
        assert result["category"] == category.value


def test_pb_06_quality_suffix_present():
    """El prompt siempre incluye el quality suffix."""
    from app.engine.image_prompt_builder import QUALITY_SUFFIX

    result = build_visual_prompt(
        entity_type=EntityType.character,
        confirmed_content="Test content",
        category=ContentCategory.extended_description,
        max_tokens=512,
    )
    assert QUALITY_SUFFIX in result["prompt"]


def test_estimate_tokens_counts_correctly():
    """_estimate_tokens cuenta aproximadamente 4 chars por token."""
    assert _estimate_tokens("abcd") == 1  # 4 chars
    assert _estimate_tokens("a b c d") == 1  # 7 chars (3 spaces)
    assert _estimate_tokens("") == 0
    assert _estimate_tokens("palabra ") == 2  # 8 chars (7 letters + 1 space)
    assert _estimate_tokens("palabra " * 4) == 8  # 32 chars
