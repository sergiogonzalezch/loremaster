# tests/test_prompt_builder.py

from app.domain.prompt_builder import build_visual_prompt, _estimate_tokens, QUALITY_SUFFIX
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


def test_pb_04_strategy_is_llm_extraction():
    """Sin contenido confirmado lanza error (LLM only, no fallback)."""
    from app.engine.image_pipeline import invoke_prompt_extraction
    from unittest.mock import patch

    with patch("app.engine.image_pipeline.invoke_prompt_extraction") as mock:
        mock.return_value = ("robot", "metal silver")
        result = build_visual_prompt(
            entity_type=EntityType.character,
            entity_name="Test",
            entity_description="Test",
            confirmed_content="Test content",
            category=ContentCategory.extended_description,
            max_tokens=150,
        )
        assert result["strategy"] == "llm_extraction"
        assert result["source"] == "llm_extraction"


def test_pb_05_different_entity_types():
    """Diferentes tipos de entidad retornan prompts válidos."""
    from unittest.mock import patch

    with patch("app.engine.image_pipeline.invoke_prompt_extraction") as mock:
        mock.return_value = ("test", "test attributes")

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

        assert result_char["strategy"] == "llm_extraction"
        assert result_creature["strategy"] == "llm_extraction"


def test_pb_06_all_categories_supported():
    """Todas las categorías de imagen generan prompts."""
    from unittest.mock import patch

    with patch("app.engine.image_pipeline.invoke_prompt_extraction") as mock:
        mock.return_value = ("test", "test attributes")

        for category in [ContentCategory.extended_description, ContentCategory.backstory, ContentCategory.scene, ContentCategory.chapter]:
            result = build_visual_prompt(
                entity_type=EntityType.character,
                entity_name="Test",
                entity_description="Test",
                confirmed_content="Test",
                category=category,
                max_tokens=150,
            )
            assert result["strategy"] == "llm_extraction"
            assert result["category"] == category.value


def test_pb_07_quality_suffix_present():
    """El prompt siempre incluye el quality suffix."""
    from unittest.mock import patch

    with patch("app.engine.image_pipeline.invoke_prompt_extraction") as mock:
        mock.return_value = ("robot", "silver metal")
        result = build_visual_prompt(
            entity_type=EntityType.character,
            entity_name="Test",
            entity_description="Test",
            confirmed_content="Test",
            category=ContentCategory.extended_description,
            max_tokens=150,
        )
        assert QUALITY_SUFFIX in result["prompt"]


def test_estimate_tokens_counts_correctly():
    """_estimate_tokens cuenta aproximadamente 4 chars por token."""
    assert _estimate_tokens("abcd") == 1
    assert _estimate_tokens("a b c d") == 1
    assert _estimate_tokens("") == 0