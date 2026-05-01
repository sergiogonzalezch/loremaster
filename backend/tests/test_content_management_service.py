import pytest
from sqlmodel import select

from app.models.entity_content import EntityContent
from app.models.enums import ContentCategory, ContentStatus
from app.models.generated_texts import GeneratedText
from app.services.content_management_service import _discard_sibling_contents


@pytest.mark.anyio
async def test_discard_sibling_contents_only_affects_same_category(
    db_session, sample_collection, sample_entity
):
    """CMS-01: Descarta siblings solo de la misma categoría, no otras."""
    gt = GeneratedText(
        entity_id=sample_entity.id,
        collection_id=sample_collection.id,
        category="backstory",
        query="q",
        raw_content="raw",
        sources_count=1,
    )
    db_session.add(gt)
    db_session.flush()

    keep_confirmed = EntityContent(
        entity_id=sample_entity.id,
        collection_id=sample_collection.id,
        generated_text_id=gt.id,
        category=ContentCategory.scene,
        content="otra categoria",
        status=ContentStatus.confirmed,
    )
    sibling_pending = EntityContent(
        entity_id=sample_entity.id,
        collection_id=sample_collection.id,
        generated_text_id=gt.id,
        category=ContentCategory.backstory,
        content="same cat pending",
        status=ContentStatus.pending,
    )
    sibling_confirmed = EntityContent(
        entity_id=sample_entity.id,
        collection_id=sample_collection.id,
        generated_text_id=gt.id,
        category=ContentCategory.backstory,
        content="same cat confirmed",
        status=ContentStatus.confirmed,
    )
    selected = EntityContent(
        entity_id=sample_entity.id,
        collection_id=sample_collection.id,
        generated_text_id=gt.id,
        category=ContentCategory.backstory,
        content="selected",
        status=ContentStatus.pending,
    )
    db_session.add(keep_confirmed)
    db_session.add(sibling_pending)
    db_session.add(sibling_confirmed)
    db_session.add(selected)
    db_session.commit()

    discarded = _discard_sibling_contents(
        db_session,
        entity_id=sample_entity.id,
        collection_id=sample_collection.id,
        category=ContentCategory.backstory,
        exclude_id=selected.id,
        statuses=[ContentStatus.pending, ContentStatus.confirmed],
    )
    db_session.commit()

    assert discarded == 2

    rows = db_session.exec(
        select(EntityContent).where(EntityContent.entity_id == sample_entity.id)
    ).all()
    by_id = {r.id: r for r in rows}
    assert by_id[sibling_pending.id].status == ContentStatus.discarded
    assert by_id[sibling_confirmed.id].status == ContentStatus.discarded
    assert by_id[keep_confirmed.id].status == ContentStatus.confirmed
    assert by_id[selected.id].status == ContentStatus.pending
