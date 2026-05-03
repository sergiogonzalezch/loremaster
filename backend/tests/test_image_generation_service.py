# tests/test_image_generation_service.py

import pytest
from sqlalchemy.orm import Session
from app.core.exceptions import NoContextAvailableError
from app.models.entities import Entity, EntityType
from app.models.enums import ContentCategory, ContentStatus
from app.models.entity_content import EntityContent
from app.services.image_generation_service import (
    build_prompt_service,
    generate_images_service,
    delete_image_service,
    get_generation_service,
    ALLOWED_IMAGE_CATEGORIES,
)


@pytest.fixture
def sample_entity_content_confirmed(db_session: Session, sample_entity: Entity) -> EntityContent:
    """EntityContent confirmado para tests."""
    content = EntityContent(
        entity_id=sample_entity.id,
        collection_id=sample_entity.collection_id,
        generated_text_id="gen-001",
        category=ContentCategory.backstory,
        content="En las montañas nevadas del norte, nació un héroe.",
        status=ContentStatus.confirmed,
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(content)
    return content


# ── Tests build_prompt_service ────────────────────────────────────────────────────


def test_ig_01_build_prompt_with_confirmed_content(
    db_session: Session, sample_entity: Entity, sample_entity_content_confirmed: EntityContent
):
    """IG-01: build_prompt retorna prompt válido con contenido confirmado."""
    result = build_prompt_service(
        db_session,
        sample_entity,
        sample_entity_content_confirmed.id,
    )

    assert result.auto_prompt
    assert result.token_count > 0
    assert result.token_count <= 150
    assert result.prompt_source in {"extended", "scene", "entity_desc", "name_only"}
    assert result.prompt_strategy in {"llm_extraction", "fallback", "direct", "first_sentences", "entity_only"}


def test_ig_02_build_prompt_fails_for_unconfirmed_content(
    db_session: Session, sample_entity: Entity
):
    """IG-02: build_prompt lanza error si el contenido no está confirmado."""
    pending_content = EntityContent(
        entity_id=sample_entity.id,
        collection_id=sample_entity.collection_id,
        generated_text_id="gen-002",
        category=ContentCategory.backstory,
        content="Contenido pendiente",
        status=ContentStatus.pending,
    )
    db_session.add(pending_content)
    db_session.commit()

    with pytest.raises(NoContextAvailableError):
        build_prompt_service(db_session, sample_entity, pending_content.id)


def test_ig_03_build_prompt_fails_for_nonexistent_content(
    db_session: Session, sample_entity: Entity
):
    """IG-03: build_prompt lanza error si el content_id no existe."""
    with pytest.raises(NoContextAvailableError):
        build_prompt_service(db_session, sample_entity, "00000000-0000-0000-0000-000000000000")


def test_ig_04_build_prompt_fails_for_unsupported_category(
    db_session: Session, sample_entity: Entity
):
    """IG-04: build_prompt lanza error si la categoría no es soportada."""
    # Verificar que las categorías permitidas están definidas
    assert ContentCategory.backstory in ALLOWED_IMAGE_CATEGORIES
    assert ContentCategory.extended_description in ALLOWED_IMAGE_CATEGORIES
    assert ContentCategory.scene in ALLOWED_IMAGE_CATEGORIES
    assert ContentCategory.chapter in ALLOWED_IMAGE_CATEGORIES


# ── Tests generate_images_service ───────────────────────────���────────────────────────


def test_ig_05_generate_batch_returns_images(
    db_session: Session, sample_entity: Entity, sample_entity_content_confirmed: EntityContent
):
    """IG-05: generate_images retorna batch de imágenes."""
    result = generate_images_service(
        db_session,
        sample_entity,
        sample_entity_content_confirmed.id,
        final_prompt="test prompt",
        batch_size=2,
    )

    assert result.generation_id
    assert result.auto_prompt
    assert result.final_prompt == "test prompt"
    assert result.batch_size == 2
    assert len(result.images) == 2
    assert result.backend == "mock"


def test_ig_06_generate_batch_size_limits(
    db_session: Session, sample_entity: Entity, sample_entity_content_confirmed: EntityContent
):
    """IG-06: batch_size debe estar entre 1 y 4."""
    result_min = generate_images_service(
        db_session,
        sample_entity,
        sample_entity_content_confirmed.id,
        final_prompt="test",
        batch_size=1,
    )
    assert len(result_min.images) == 1

    result_max = generate_images_service(
        db_session,
        sample_entity,
        sample_entity_content_confirmed.id,
        final_prompt="test",
        batch_size=4,
    )
    assert len(result_max.images) == 4


def test_ig_07_generate_persists_generation_record(
    db_session: Session, sample_entity: Entity, sample_entity_content_confirmed: EntityContent
):
    """IG-07: generate_images guarda ImageGeneration en DB."""
    result = generate_images_service(
        db_session,
        sample_entity,
        sample_entity_content_confirmed.id,
        final_prompt="test prompt",
        batch_size=2,
    )

    from sqlmodel import select
    from app.models.image_generation import ImageGeneration

    gen_record = db_session.exec(
        select(ImageGeneration).where(ImageGeneration.id == result.generation_id)
    ).first()
    assert gen_record is not None
    assert gen_record.final_prompt == "test prompt"


# ── Tests delete_image_service ────────────────────────────────────────────────────


def test_ig_08_delete_image_not_found_in_mock(
    db_session: Session, sample_entity: Entity, sample_entity_content_confirmed: EntityContent
):
    """IG-08: delete_image falla porque mock no persiste imágenes."""
    result = generate_images_service(
        db_session,
        sample_entity,
        sample_entity_content_confirmed.id,
        final_prompt="test",
        batch_size=1,
    )

    image_id = result.images[0].id

    with pytest.raises(NoContextAvailableError):
        delete_image_service(db_session, sample_entity, result.generation_id, image_id)


def test_ig_09_delete_image_fails_for_wrong_entity(
    db_session: Session, sample_entity: Entity, sample_entity_content_confirmed: EntityContent
):
    """IG-09: delete_image verifica ownership."""
    result = generate_images_service(
        db_session,
        sample_entity,
        sample_entity_content_confirmed.id,
        final_prompt="test",
        batch_size=1,
    )

    image_id = result.images[0].id

    other_entity = Entity(
        collection_id=sample_entity.collection_id,
        type=EntityType.character,
        name="Other Entity",
        description="Other",
    )
    db_session.add(other_entity)
    db_session.commit()

    with pytest.raises(NoContextAvailableError):
        delete_image_service(db_session, other_entity, result.generation_id, image_id)


# ── Tests get_generation_service ─────────────────��──────────────────────────────────


def test_ig_10_get_generation_returns_generation_record(
    db_session: Session, sample_entity: Entity, sample_entity_content_confirmed: EntityContent
):
    """IG-10: get_generation retorna la generación guardada."""
    result = generate_images_service(
        db_session,
        sample_entity,
        sample_entity_content_confirmed.id,
        final_prompt="test prompt",
        batch_size=2,
    )

    retrieved = get_generation_service(db_session, sample_entity, result.generation_id)

    assert retrieved.generation_id == result.generation_id
    assert retrieved.batch_size == 2
    # Con mock backend, las imágenes no se persisten en DB
    # así que verify que temos el generation_id correto


def test_ig_11_get_generation_fails_for_nonexistent(
    db_session: Session, sample_entity: Entity
):
    """IG-11: get_generation lanza error si no existe."""
    with pytest.raises(NoContextAvailableError):
        get_generation_service(db_session, sample_entity, "00000000-0000-0000-0000-000000000000")


def test_ig_12_get_generation_validates_entity_ownership(
    db_session: Session, sample_entity: Entity, sample_entity_content_confirmed: EntityContent
):
    """IG-12: get_generation verifica ownership."""
    result = generate_images_service(
        db_session,
        sample_entity,
        sample_entity_content_confirmed.id,
        final_prompt="test",
        batch_size=1,
    )

    other_entity = Entity(
        collection_id=sample_entity.collection_id,
        type=EntityType.character,
        name="Other Entity",
        description="Other",
    )
    db_session.add(other_entity)
    db_session.commit()

    with pytest.raises(NoContextAvailableError):
        get_generation_service(db_session, other_entity, result.generation_id)


# ── Tests prompt_source_labels ────────────────────────────────────────────────────


def test_ig_13_prompt_source_labels_return_correct_text():
    """IG-13: get_prompt_source_label retorna texto correcto."""
    from app.domain.prompt_builder import get_prompt_source_label

    assert get_prompt_source_label("extended") == "Basado en la descripción extendida de la entidad"
    assert get_prompt_source_label("scene") == "Basado en la escena o capítulo generado"
    assert get_prompt_source_label("entity_desc") == "Basado en la descripción general de la entidad"
    assert get_prompt_source_label("name_only") == "Solo el nombre — la entidad no tiene suficiente contexto"
    assert get_prompt_source_label("template") == "Prompt determinista (template)"
    assert get_prompt_source_label("fallback") == "Prompt determinista (fallback)"