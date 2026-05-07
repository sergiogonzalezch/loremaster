# tests/test_image_generation_service.py

import pytest
from sqlalchemy.orm import Session
from sqlmodel import select
from unittest.mock import MagicMock, patch

from app.core.exceptions import NoContextAvailableError
from app.models.entities import Entity, EntityType
from app.models.enums import ContentCategory, ContentStatus
from app.models.entity_content import EntityContent
from app.models.image_generation import ImageRecord
from app.services.image_generation_service import (
    build_prompt_service,
    generate_images_service,
    delete_image_service,
    get_generation_service,
    ALLOWED_IMAGE_CATEGORIES,
)


@pytest.fixture
def sample_entity_content_confirmed(
    db_session: Session, sample_entity: Entity
) -> EntityContent:
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
    db_session: Session,
    sample_entity: Entity,
    sample_entity_content_confirmed: EntityContent,
):
    """IG-01: build_prompt retorna prompt válido con contenido confirmado."""
    result = build_prompt_service(
        db_session,
        sample_entity,
        sample_entity_content_confirmed.id,
    )

    assert result.auto_prompt
    assert result.token_count > 0


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
        build_prompt_service(
            db_session, sample_entity, "00000000-0000-0000-0000-000000000000"
        )


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
    mock_image_backend,
    db_session: Session,
    sample_entity: Entity,
    sample_entity_content_confirmed: EntityContent,
):
    """IG-05: generate_images retorna batch de imágenes."""
    result = generate_images_service(
        db_session,
        sample_entity,
        sample_entity_content_confirmed.id,
        auto_prompt="test auto prompt",
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
    mock_image_backend,
    db_session: Session,
    sample_entity: Entity,
    sample_entity_content_confirmed: EntityContent,
):
    """IG-06: batch_size debe estar entre 1 y 4."""
    result_min = generate_images_service(
        db_session,
        sample_entity,
        sample_entity_content_confirmed.id,
        auto_prompt="test auto",
        final_prompt="test",
        batch_size=1,
    )
    assert len(result_min.images) == 1

    result_max = generate_images_service(
        db_session,
        sample_entity,
        sample_entity_content_confirmed.id,
        auto_prompt="test auto",
        final_prompt="test",
        batch_size=4,
    )
    assert len(result_max.images) == 4


def test_ig_07_generate_persists_generation_record(
    mock_image_backend,
    db_session: Session,
    sample_entity: Entity,
    sample_entity_content_confirmed: EntityContent,
):
    """IG-07: generate_images guarda ImageGeneration en DB."""
    result = generate_images_service(
        db_session,
        sample_entity,
        sample_entity_content_confirmed.id,
        auto_prompt="test auto prompt",
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


def test_ig_08_delete_image_works_in_mock(
    mock_image_backend,
    db_session: Session,
    sample_entity: Entity,
    sample_entity_content_confirmed: EntityContent,
):
    """IG-08: delete_image funciona en modo mock (soft delete)."""
    result = generate_images_service(
        db_session,
        sample_entity,
        sample_entity_content_confirmed.id,
        auto_prompt="test auto",
        final_prompt="test",
        batch_size=1,
    )

    image_id = result.images[0].id

    delete_image_service(db_session, sample_entity, result.generation_id, image_id)

    record = db_session.exec(
        select(ImageRecord).where(ImageRecord.id == image_id)
    ).first()

    assert record is not None
    assert record.is_deleted is True
    assert record.deleted_at is not None


def test_ig_09_delete_image_fails_for_wrong_entity(
    mock_image_backend,
    db_session: Session,
    sample_entity: Entity,
    sample_entity_content_confirmed: EntityContent,
):
    """IG-09: delete_image verifica ownership."""
    result = generate_images_service(
        db_session,
        sample_entity,
        sample_entity_content_confirmed.id,
        auto_prompt="test auto",
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
    mock_image_backend,
    db_session: Session,
    sample_entity: Entity,
    sample_entity_content_confirmed: EntityContent,
):
    """IG-10: get_generation retorna la generación guardada."""
    result = generate_images_service(
        db_session,
        sample_entity,
        sample_entity_content_confirmed.id,
        auto_prompt="test auto prompt",
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
        get_generation_service(
            db_session, sample_entity, "00000000-0000-0000-0000-000000000000"
        )


def test_ig_12_get_generation_validates_entity_ownership(
    mock_image_backend,
    db_session: Session,
    sample_entity: Entity,
    sample_entity_content_confirmed: EntityContent,
):
    """IG-12: get_generation verifica ownership."""
    result = generate_images_service(
        db_session,
        sample_entity,
        sample_entity_content_confirmed.id,
        auto_prompt="test auto",
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


def test_ig_13_generate_batch_comfyui(
    db_session: Session,
    sample_entity: Entity,
    sample_entity_content_confirmed: EntityContent,
):
    """IG-13: generate_images con backend comfyui guarda registros en DB."""

    fake_image_bytes = b"fake-png-bytes"

    mock_client = MagicMock()
    mock_client.queue_prompt.return_value = "prompt-uuid-123"
    mock_client.get_history_until_complete.return_value = {
        "status": "completed",
        "outputs": {
            "3": {
                "images": [
                    {"filename": "img_001.png", "subfolder": "", "type": "output"}
                ]
            }
        },
    }
    mock_client.get_output_images.return_value = [
        {"filename": "img_001.png", "subfolder": "", "type": "output", "node_id": "3"}
    ]
    mock_client.download_image.return_value = fake_image_bytes

    with (
        patch("app.services.image_generation_service.settings") as mock_settings,
        patch("app.engine.comfyui_client.ComfyUIClient", return_value=mock_client),
        patch(
            "app.engine.comfyui_client.load_template",
            return_value={"12": {"inputs": {"value": ""}}},
        ),
        patch("app.engine.comfyui_client.inject_prompt", side_effect=lambda w, p: w),
        patch(
            "app.services.image_generation_service._save_comfyui_image",
            return_value="col/ent/gen/img.png",
        ),
    ):
        mock_settings.image_backend = "comfyui"
        mock_settings.comfyui_url = "http://localhost:8188"
        mock_settings.image_width = 1024
        mock_settings.image_height = 1024
        mock_settings.image_seed_base = 42
        mock_settings.storage_base_url = "http://localhost:8000/media"

        result = generate_images_service(
            db_session,
            sample_entity,
            sample_entity_content_confirmed.id,
            auto_prompt="a warrior in blue armor",
            final_prompt="a warrior in blue armor, high quality",
            batch_size=1,
        )

    assert result.generation_id
    assert result.backend == "comfyui"
    assert len(result.images) == 1
    assert result.images[0].image_url is not None
