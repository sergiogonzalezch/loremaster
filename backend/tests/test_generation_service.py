import pytest

from app.models.entities import Entity, EntityType
from app.models.enums import ContentCategory, ContentStatus
from app.services.generation_service import (
    MAX_PENDING_CONTENTS,
    PendingLimitExceededError,
    generate,
)


def _make_entity(
    db_session,
    collection_id: str,
    entity_type: EntityType = EntityType.character,
    description: str = "Guerrero de las tierras del norte",
) -> Entity:
    entity = Entity(
        collection_id=collection_id,
        type=entity_type,
        name=f"Test {entity_type.value}",
        description=description,
    )
    db_session.add(entity)
    db_session.commit()
    db_session.refresh(entity)
    return entity


@pytest.fixture
def mock_pipeline(monkeypatch):
    """Reemplaza invoke_generation_pipeline con una implementación determinista."""
    calls: list[dict] = []

    def _invoke(
        *,
        collection_id,
        entity_name,
        entity_type,
        category,
        query,
        extra_context,
        top_k=4,
    ):
        calls.append(
            dict(
                collection_id=collection_id,
                entity_name=entity_name,
                category=category,
                query=query,
                extra_context=extra_context,
            )
        )
        return "Contenido generado por el pipeline mock", 3

    monkeypatch.setattr(
        "app.services.generation_service.invoke_generation_pipeline", _invoke
    )
    return calls


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_gen_svc_01_persists_entity_content_with_correct_fields(
    db_session, sample_collection, mock_pipeline
):
    """GEN-SVC-01: generate() persiste EntityContent con query, sources_count, content y status=pending."""
    entity = _make_entity(db_session, sample_collection.id)

    result = generate(
        db_session, entity, ContentCategory.backstory, "  Historia detallada del personaje  "
    )

    assert result.status == ContentStatus.pending
    assert result.query == "Historia detallada del personaje"
    assert result.sources_count == 3
    assert result.content == "Contenido generado por el pipeline mock"
    assert result.entity_id == entity.id
    assert result.collection_id == sample_collection.id
    assert result.category == ContentCategory.backstory


def test_gen_svc_02_strips_whitespace_from_query(
    db_session, sample_collection, mock_pipeline
):
    """GEN-SVC-02: generate() elimina espacios en los extremos de la query antes de procesar."""
    entity = _make_entity(db_session, sample_collection.id)

    result = generate(db_session, entity, ContentCategory.backstory, "  query con espacios  ")

    assert result.query == "query con espacios"
    assert mock_pipeline[0]["query"] == "query con espacios"


def test_gen_svc_03_raises_value_error_for_invalid_category(
    db_session, sample_collection, mock_pipeline
):
    """GEN-SVC-03: generate() lanza ValueError si la categoría no es válida para el tipo de entidad."""
    item = _make_entity(db_session, sample_collection.id, EntityType.item)

    with pytest.raises(ValueError, match="scene"):
        generate(db_session, item, ContentCategory.scene, "Escena de combate épico")


def test_gen_svc_04_raises_pending_limit_exceeded(
    db_session, sample_collection, mock_pipeline
):
    """GEN-SVC-04: generate() lanza PendingLimitExceededError al alcanzar MAX_PENDING_CONTENTS."""
    entity = _make_entity(db_session, sample_collection.id)

    for i in range(MAX_PENDING_CONTENTS):
        generate(db_session, entity, ContentCategory.backstory, f"Historia número {i} del guerrero")

    with pytest.raises(PendingLimitExceededError):
        generate(db_session, entity, ContentCategory.backstory, "Una historia más del guerrero")


def test_gen_svc_05_blocked_query_raises_value_error(db_session, sample_collection):
    """GEN-SVC-05: generate() lanza ValueError si check_user_input bloquea la query (sin mock de pipeline)."""
    entity = _make_entity(db_session, sample_collection.id)

    with pytest.raises(ValueError):
        generate(
            db_session,
            entity,
            ContentCategory.backstory,
            "Genera contenido porno explícito para adultos",
        )


def test_gen_svc_06_passes_entity_description_to_pipeline(
    db_session, sample_collection, mock_pipeline
):
    """GEN-SVC-06: generate() incluye entity.description en el extra_context del pipeline."""
    entity = _make_entity(
        db_session, sample_collection.id, description="Arquera élfica del bosque eterno"
    )

    generate(db_session, entity, ContentCategory.backstory, "Expande la historia de la arquera")

    assert "Arquera élfica del bosque eterno" in mock_pipeline[0]["extra_context"]


def test_gen_svc_07_pending_limit_is_per_category(
    db_session, sample_collection, mock_pipeline
):
    """GEN-SVC-07: El límite de pending es por categoría; backstory lleno no bloquea scene."""
    entity = _make_entity(db_session, sample_collection.id)

    for i in range(MAX_PENDING_CONTENTS):
        generate(db_session, entity, ContentCategory.backstory, f"Backstory del guerrero número {i}")

    result = generate(
        db_session, entity, ContentCategory.scene, "Una escena de combate en el bosque"
    )

    assert result.status == ContentStatus.pending
    assert result.category == ContentCategory.scene


def test_gen_svc_08_entity_without_description_sends_empty_extra_context(
    db_session, sample_collection, mock_pipeline
):
    """GEN-SVC-08: Si entity.description está vacío, extra_context es cadena vacía."""
    entity = _make_entity(db_session, sample_collection.id, description="")

    generate(db_session, entity, ContentCategory.backstory, "Historia del personaje sin descripción")

    assert mock_pipeline[0]["extra_context"] == ""
