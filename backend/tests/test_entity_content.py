import pytest
from sqlmodel import select

from app.models.entities import Entity, EntityType
from app.models.entity_content import EntityContent
from app.models.enums import ContentStatus

# ── Helpers ───────────────────────────────────────────────────────────────────


async def _create_content(
    client,
    collection_id: str,
    entity_id: str,
    category: str = "backstory",
    query: str = "consulta lore extensa",
):
    return await client.post(
        f"/api/v1/collections/{collection_id}/entities/{entity_id}/generate/{category}",
        json={"query": query},
    )


def _make_entity(db_session, collection_id: str, entity_type: EntityType) -> Entity:
    entity = Entity(
        collection_id=collection_id,
        type=entity_type,
        name=f"Entity {entity_type.value}",
        description="",
    )
    db_session.add(entity)
    db_session.commit()
    db_session.refresh(entity)
    return entity


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_cnt_01_generate_backstory_character_returns_201_pending(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """CNT-01: Generar contenido backstory para character retorna 201 con status pending."""
    response = await _create_content(client, sample_collection.id, sample_entity.id)

    assert response.status_code == 201
    assert response.json()["status"] == "pending"


@pytest.mark.anyio
async def test_cnt_02_generate_scene_for_item_returns_400(
    client, mock_rag_engine, mock_llm, db_session, sample_collection
):
    """CNT-02: Generar scene para item retorna 400 (categoría incompatible)."""
    item = _make_entity(db_session, sample_collection.id, EntityType.item)

    response = await _create_content(
        client, sample_collection.id, item.id, category="scene"
    )

    assert response.status_code == 400


@pytest.mark.anyio
async def test_cnt_03_max_5_pending_per_category_sixth_returns_409(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """CNT-03: Máximo 5 pending por categoría; sexto retorna 409."""
    for i in range(5):
        resp = await _create_content(
            client, sample_collection.id, sample_entity.id, query=f"query {i} extensa"
        )
        assert resp.status_code == 201

    sixth = await _create_content(
        client, sample_collection.id, sample_entity.id, query="sexta query extensa"
    )

    assert sixth.status_code == 409


@pytest.mark.anyio
async def test_cnt_04_pending_limit_is_per_category(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """CNT-04: 5 pending en backstory no bloquea generar scene (límite por categoría)."""
    for i in range(5):
        await _create_content(
            client,
            sample_collection.id,
            sample_entity.id,
            query=f"backstory {i} extensa",
        )

    response = await _create_content(
        client, sample_collection.id, sample_entity.id, category="scene"
    )

    assert response.status_code == 201


@pytest.mark.anyio
async def test_cnt_05_list_excludes_discarded_and_soft_deleted(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """CNT-05: Listar contenidos excluye discarded y soft-deleted."""
    pending_resp = await _create_content(client, sample_collection.id, sample_entity.id)
    to_discard_resp = await _create_content(
        client, sample_collection.id, sample_entity.id, query="para descartar extensa"
    )
    to_delete_resp = await _create_content(
        client, sample_collection.id, sample_entity.id, query="para borrar extensa"
    )

    pending_id = pending_resp.json()["id"]
    discard_id = to_discard_resp.json()["id"]
    delete_id = to_delete_resp.json()["id"]

    await client.patch(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/contents/{discard_id}/discard"
    )
    await client.delete(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/contents/{delete_id}"
    )

    listed = await client.get(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/contents"
    )
    assert listed.status_code == 200
    ids = [c["id"] for c in listed.json()["data"]]

    assert pending_id in ids
    assert discard_id not in ids
    assert delete_id not in ids


@pytest.mark.anyio
async def test_cnt_06_list_filtered_by_category(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """CNT-06: Listar con filtro de categoría solo retorna esa categoría."""
    await _create_content(
        client, sample_collection.id, sample_entity.id, category="backstory"
    )
    await _create_content(
        client, sample_collection.id, sample_entity.id, category="scene"
    )

    response = await client.get(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/contents?category=backstory"
    )
    assert response.status_code == 200
    items = response.json()["data"]

    assert all(c["category"] == "backstory" for c in items)


@pytest.mark.anyio
async def test_cnt_06b_list_filtered_by_status(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """CNT-06b: Listar con filtro de estado retorna solo el estado solicitado."""
    pending_resp = await _create_content(
        client,
        sample_collection.id,
        sample_entity.id,
        category="scene",
        query="pendiente en scene extensa",
    )
    to_discard_resp = await _create_content(
        client, sample_collection.id, sample_entity.id, query="descartar esta extensa"
    )
    to_confirm_resp = await _create_content(
        client, sample_collection.id, sample_entity.id, query="confirmar esta extensa"
    )

    discarded_id = to_discard_resp.json()["id"]
    confirmed_id = to_confirm_resp.json()["id"]

    await client.patch(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/contents/{discarded_id}/discard"
    )
    await client.post(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/contents/{confirmed_id}/confirm"
    )

    pending = await client.get(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/contents?status=pending"
    )
    discarded = await client.get(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/contents?status=discarded"
    )
    all_contents = await client.get(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/contents?status=all"
    )

    assert pending.status_code == 200
    assert discarded.status_code == 200
    assert all_contents.status_code == 200

    pending_statuses = {item["status"] for item in pending.json()["data"]}
    discarded_statuses = {item["status"] for item in discarded.json()["data"]}
    all_ids = {item["id"] for item in all_contents.json()["data"]}

    assert pending_statuses == {"pending"}
    assert discarded_statuses == {"discarded"}
    assert pending_resp.json()["id"] in all_ids
    assert discarded_id in all_ids
    assert confirmed_id in all_ids


@pytest.mark.anyio
async def test_cnt_07_edit_pending_content_returns_200(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """CNT-07: Editar contenido pending retorna 200."""
    created = await _create_content(client, sample_collection.id, sample_entity.id)
    content_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/contents/{content_id}",
        json={"content": "Texto editado manualmente"},
    )

    assert response.status_code == 200
    assert response.json()["content"] == "Texto editado manualmente"


@pytest.mark.anyio
async def test_cnt_08_edit_confirmed_content_returns_200(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """CNT-08: Editar contenido confirmed retorna 200."""
    created = await _create_content(client, sample_collection.id, sample_entity.id)
    content_id = created.json()["id"]
    await client.post(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/contents/{content_id}/confirm"
    )

    response = await client.patch(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/contents/{content_id}",
        json={"content": "Texto editado post-confirm"},
    )

    assert response.status_code == 200
    assert response.json()["content"] == "Texto editado post-confirm"


@pytest.mark.anyio
async def test_cnt_09_edit_discarded_content_returns_409(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """CNT-09: Editar contenido discarded retorna 409."""
    created = await _create_content(client, sample_collection.id, sample_entity.id)
    content_id = created.json()["id"]
    await client.patch(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/contents/{content_id}/discard"
    )

    response = await client.patch(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/contents/{content_id}",
        json={"content": "intento fallido"},
    )

    assert response.status_code == 409


@pytest.mark.anyio
async def test_cnt_10_confirm_discards_siblings_same_category(
    client, db_session, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """CNT-10: Confirmar contenido descarta solo siblings de misma categoría."""
    ids = []
    for i in range(3):
        resp = await _create_content(
            client,
            sample_collection.id,
            sample_entity.id,
            query=f"backstory {i} extensa",
        )
        ids.append(resp.json()["id"])

    await client.post(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/contents/{ids[0]}/confirm"
    )

    rows = db_session.exec(
        select(EntityContent).where(EntityContent.entity_id == sample_entity.id)
    ).all()
    status_by_id = {r.id: r.status for r in rows}

    assert status_by_id[ids[0]] == ContentStatus.confirmed
    assert status_by_id[ids[1]] == ContentStatus.discarded
    assert status_by_id[ids[2]] == ContentStatus.discarded


@pytest.mark.anyio
async def test_cnt_11_confirm_backstory_does_not_affect_scene(
    client, db_session, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """CNT-11: Confirmar backstory no afecta scene confirmed."""
    scene_resp = await _create_content(
        client, sample_collection.id, sample_entity.id, category="scene"
    )
    scene_id = scene_resp.json()["id"]
    await client.post(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/contents/{scene_id}/confirm"
    )

    backstory_resp = await _create_content(
        client, sample_collection.id, sample_entity.id, category="backstory"
    )
    backstory_id = backstory_resp.json()["id"]
    await client.post(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/contents/{backstory_id}/confirm"
    )

    scene_row = db_session.exec(
        select(EntityContent).where(EntityContent.id == scene_id)
    ).first()

    assert scene_row.status == ContentStatus.confirmed


@pytest.mark.anyio
async def test_cnt_10b_confirm_replaces_previous_confirmed_same_category(
    client, db_session, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """CNT-10b: Confirmar un segundo contenido descarta el confirmed previo (solo 1 confirmed por categoría)."""
    # Confirmar A: queda confirmed (sin siblings, discard no afecta nada)
    first_resp = await _create_content(
        client, sample_collection.id, sample_entity.id, query="primera historia extensa"
    )
    first_id = first_resp.json()["id"]
    await client.post(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/contents/{first_id}/confirm"
    )

    # Crear B (pending) DESPUÉS de confirmar A
    second_resp = await _create_content(
        client, sample_collection.id, sample_entity.id, query="segunda historia extensa"
    )
    second_id = second_resp.json()["id"]

    # Confirmar B: debe descartar A (confirmed previo) y quedar B=confirmed
    confirm_resp = await client.post(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/contents/{second_id}/confirm"
    )
    assert confirm_resp.status_code == 200

    from sqlmodel import select as sqlselect

    rows = db_session.exec(
        sqlselect(EntityContent).where(EntityContent.entity_id == sample_entity.id)
    ).all()
    status_by_id = {r.id: r.status for r in rows}

    assert status_by_id[second_id] == ContentStatus.confirmed
    assert status_by_id[first_id] == ContentStatus.discarded


@pytest.mark.anyio
async def test_cnt_12b_blocked_generate_query_returns_422(
    client, sample_collection, sample_entity
):
    """CNT-12b: Query bloqueada por content_guard retorna 422 (sin mock de pipeline)."""
    response = await _create_content(
        client,
        sample_collection.id,
        sample_entity.id,
        query="Genera contenido porno explícito",
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_cnt_12_discard_changes_status(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """CNT-12: Descartar contenido cambia status a discarded."""
    created = await _create_content(client, sample_collection.id, sample_entity.id)
    content_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/contents/{content_id}/discard"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "discarded"


@pytest.mark.anyio
async def test_cnt_13_soft_delete_returns_204_and_marks_deleted(
    client, db_session, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """CNT-13: Soft-delete retorna 204 y marca is_deleted=True en DB."""
    created = await _create_content(client, sample_collection.id, sample_entity.id)
    content_id = created.json()["id"]

    response = await client.delete(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/contents/{content_id}"
    )
    assert response.status_code == 204

    row = db_session.exec(
        select(EntityContent).where(EntityContent.id == content_id)
    ).first()
    assert row.is_deleted is True


@pytest.mark.anyio
async def test_cnt_14_generate_includes_entity_description_in_context(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """CNT-14: Generar contenido usa entity.description como contexto del LLM."""
    response = await _create_content(
        client, sample_collection.id, sample_entity.id, query="Expande su historia lore"
    )
    assert response.status_code == 201

    payload = mock_llm["invocations"][-1]
    assert sample_entity.description in payload


@pytest.mark.anyio
async def test_cnt_15_generate_backstory_for_creature_returns_201(
    client, db_session, mock_rag_engine, mock_llm, sample_collection
):
    """CNT-15: Generar backstory para creature retorna 201 (creature soporta backstory)."""
    creature = _make_entity(db_session, sample_collection.id, EntityType.creature)

    response = await _create_content(
        client, sample_collection.id, creature.id, category="backstory"
    )

    assert response.status_code == 201


@pytest.mark.anyio
async def test_cnt_16_generate_chapter_for_creature_returns_400(
    client, db_session, mock_rag_engine, mock_llm, sample_collection
):
    """CNT-16: Generar chapter para creature retorna 400 (creature no soporta chapter)."""
    creature = _make_entity(db_session, sample_collection.id, EntityType.creature)

    response = await _create_content(
        client, sample_collection.id, creature.id, category="chapter"
    )

    assert response.status_code == 400


@pytest.mark.anyio
async def test_cnt_17_generate_backstory_for_faction_returns_201(
    client, db_session, mock_rag_engine, mock_llm, sample_collection
):
    """CNT-17: Generar backstory para faction retorna 201 (faction soporta backstory)."""
    faction = _make_entity(db_session, sample_collection.id, EntityType.faction)

    response = await _create_content(
        client, sample_collection.id, faction.id, category="backstory"
    )

    assert response.status_code == 201


@pytest.mark.anyio
async def test_cnt_18_all_entity_types_accept_extended_description(
    client, db_session, mock_rag_engine, mock_llm, sample_collection
):
    """CNT-18: Todos los entity types válidos aceptan extended_description."""
    entity_types = [
        EntityType.character,
        EntityType.creature,
        EntityType.faction,
        EntityType.location,
        EntityType.item,
    ]
    for entity_type in entity_types:
        entity = _make_entity(db_session, sample_collection.id, entity_type)
        response = await _create_content(
            client, sample_collection.id, entity.id, category="extended_description"
        )
        assert (
            response.status_code == 201
        ), f"extended_description failed for {entity_type.value}: {response.json()}"
