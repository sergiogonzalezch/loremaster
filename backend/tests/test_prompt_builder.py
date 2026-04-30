# tests/test_prompt_builder.py

from app.domain.prompt_builder import build_visual_prompt, _estimate_tokens
from app.models.entities import EntityType


def test_pb_01_token_count_within_max():
    """El prompt nunca supera max_tokens."""
    long_content = "palabra " * 300
    result = build_visual_prompt(
        entity_type=EntityType.character,
        entity_name="Aragorn",
        entity_description="Un guerrero valiente",
        confirmed_content=long_content,
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
        max_tokens=150,
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
        max_tokens=150,
    )
    assert result["source"] == "description"
    assert "Hoja forjada" in result["prompt"]


def test_pb_05_empty_everything_falls_back_to_name_only():
    """Sin contenido ni descripción solo usa el nombre."""
    result = build_visual_prompt(
        entity_type=EntityType.location,
        entity_name="Torre del Norte",
        entity_description="",
        confirmed_content="",
        max_tokens=150,
    )
    assert result["source"] == "name_only"
    assert "Torre del Norte" in result["prompt"]


def test_pb_06_all_entity_types_produce_valid_prompt():
    """Todos los entity types generan un prompt con prefijo correcto."""
    from app.models.entities import EntityType

    for etype in EntityType:
        result = build_visual_prompt(
            entity_type=etype,
            entity_name="Entidad de prueba",
            entity_description="desc",
            confirmed_content="contenido de prueba",
            max_tokens=150,
        )
        assert result["token_count"] > 0
        assert result["token_count"] <= 150
        assert "high quality" in result["prompt"]


def test_pb_07_target_tokens_respected_when_possible():
    """Con contenido moderado el resultado está cerca del objetivo ≤75."""
    result = build_visual_prompt(
        entity_type=EntityType.character,
        entity_name="Galadriel",
        entity_description="Reina élfica de gran poder",
        confirmed_content="Dama de luz, portadora de Nenya",
        max_tokens=150,
        target_tokens=75,
    )
    assert result["token_count"] <= 75
