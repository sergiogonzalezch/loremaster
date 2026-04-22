import pytest
from sqlmodel import select

from app.models.entity_text_draft import EntityTextDraft


async def _create_draft(
    client, collection_id: str, entity_id: str, query: str = "consulta lore"
):
    return await client.post(
        f"/api/v1/collections/{collection_id}/entities/{entity_id}/generate",
        json={"query": query},
    )


@pytest.mark.anyio
async def test_generate_draft(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """DRF-01: Generar draft retorna 201 con status pending."""
    response = await _create_draft(client, sample_collection.id, sample_entity.id)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["content"]


@pytest.mark.anyio
async def test_max_pending_drafts_409(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """DRF-02: Máximo 5 drafts pending; sexto retorna 409."""
    for i in range(5):
        resp = await _create_draft(
            client, sample_collection.id, sample_entity.id, f"query larga {i}"
        )
        assert resp.status_code == 201

    sixth = await _create_draft(
        client, sample_collection.id, sample_entity.id, "query sexta"
    )
    assert sixth.status_code == 409


@pytest.mark.anyio
async def test_list_drafts_visibility(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """DRF-03: Solo pending y confirmed aparecen en listado; discarded y soft-deleted no."""
    to_discard = await _create_draft(
        client, sample_collection.id, sample_entity.id, "query discard"
    )
    to_confirm = await _create_draft(
        client, sample_collection.id, sample_entity.id, "query confirm"
    )
    to_delete = await _create_draft(
        client, sample_collection.id, sample_entity.id, "query delete"
    )

    discard_id = to_discard.json()["id"]
    confirm_id = to_confirm.json()["id"]
    delete_id = to_delete.json()["id"]

    await client.patch(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts/{discard_id}/discard"
    )
    await client.post(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts/{confirm_id}/confirm"
    )
    await client.delete(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts/{delete_id}"
    )

    # Crear el draft pending después de la confirmación para que no sea auto-descartado.
    pending = await _create_draft(
        client, sample_collection.id, sample_entity.id, "query pending"
    )
    pending_id = pending.json()["id"]

    listed = await client.get(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts"
    )
    assert listed.status_code == 200
    ids = [d["id"] for d in listed.json()["data"]]

    assert pending_id in ids
    assert confirm_id in ids
    assert discard_id not in ids
    assert delete_id not in ids


@pytest.mark.anyio
async def test_edit_pending_draft(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """DRF-04: Actualizar contenido de draft pending retorna 200."""
    created = await _create_draft(client, sample_collection.id, sample_entity.id)
    draft_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts/{draft_id}",
        json={"content": "Contenido actualizado"},
    )
    assert response.status_code == 200
    assert response.json()["content"] == "Contenido actualizado"


@pytest.mark.anyio
async def test_edit_confirmed_draft(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """DRF-05: Actualizar draft confirmado retorna 200 (editable)."""
    created = await _create_draft(client, sample_collection.id, sample_entity.id)
    draft_id = created.json()["id"]
    await client.post(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts/{draft_id}/confirm"
    )

    response = await client.patch(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts/{draft_id}",
        json={"content": "contenido editado post-confirm"},
    )
    assert response.status_code == 200
    assert response.json()["content"] == "contenido editado post-confirm"


@pytest.mark.anyio
async def test_edit_discarded_draft_404(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """DRF-06: Actualizar draft descartado retorna 404."""
    created = await _create_draft(client, sample_collection.id, sample_entity.id)
    draft_id = created.json()["id"]
    await client.patch(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts/{draft_id}/discard"
    )

    response = await client.patch(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts/{draft_id}",
        json={"content": "intento de editar descartado"},
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_confirm_returns_draft_response(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """DRF-07: Confirmar draft retorna EntityTextDraftResponse con status confirmed."""
    created = await _create_draft(client, sample_collection.id, sample_entity.id)
    draft_id = created.json()["id"]

    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts/{draft_id}/confirm"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == draft_id
    assert data["status"] == "confirmed"
    assert data["confirmed_at"] is not None
    assert data["entity_id"] == sample_entity.id
    assert data["collection_id"] == sample_collection.id
    assert "content" in data
    assert "query" in data
    assert "name" not in data


@pytest.mark.anyio
async def test_confirm_auto_discards_sibling_pending(
    client, db_session, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """DRF-08: Confirmar un draft descarta automáticamente otros pending."""
    drafts = []
    for i in range(3):
        resp = await _create_draft(
            client, sample_collection.id, sample_entity.id, f"query {i} lore"
        )
        drafts.append(resp.json())

    confirm_resp = await client.post(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts/{drafts[0]['id']}/confirm"
    )
    assert confirm_resp.status_code == 200

    db_drafts = db_session.exec(
        select(EntityTextDraft).where(EntityTextDraft.entity_id == sample_entity.id)
    ).all()
    status_by_id = {item.id: item.status.value for item in db_drafts}
    assert status_by_id[drafts[0]["id"]] == "confirmed"
    assert status_by_id[drafts[1]["id"]] == "discarded"
    assert status_by_id[drafts[2]["id"]] == "discarded"


@pytest.mark.anyio
async def test_confirm_second_cycle_discards_previous_confirmed(
    client, db_session, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """DRF-09: Segundo ciclo de confirmación descarta el confirmed anterior."""
    first = await _create_draft(
        client, sample_collection.id, sample_entity.id, "primer ciclo lore"
    )
    first_id = first.json()["id"]
    await client.post(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts/{first_id}/confirm"
    )

    second = await _create_draft(
        client, sample_collection.id, sample_entity.id, "segundo ciclo lore"
    )
    second_id = second.json()["id"]
    await client.post(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts/{second_id}/confirm"
    )

    db_drafts = db_session.exec(
        select(EntityTextDraft).where(EntityTextDraft.entity_id == sample_entity.id)
    ).all()
    status_by_id = {d.id: d.status.value for d in db_drafts}
    assert status_by_id[first_id] == "discarded"
    assert status_by_id[second_id] == "confirmed"


@pytest.mark.anyio
async def test_discard_draft(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """DRF-10: Descartar draft cambia status a discarded."""
    created = await _create_draft(client, sample_collection.id, sample_entity.id)
    draft_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts/{draft_id}/discard"
    )
    assert response.status_code == 200
    assert response.json()["status"] == "discarded"


@pytest.mark.anyio
async def test_soft_delete_draft(
    client, mock_rag_engine, mock_llm, db_session, sample_collection, sample_entity
):
    """DRF-11: DELETE hace soft-delete del draft (is_deleted=True), retorna 204."""
    created = await _create_draft(client, sample_collection.id, sample_entity.id)
    draft_id = created.json()["id"]

    response = await client.delete(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts/{draft_id}"
    )
    assert response.status_code == 204

    db_draft = db_session.exec(
        select(EntityTextDraft).where(EntityTextDraft.id == draft_id)
    ).first()
    assert db_draft is not None
    assert db_draft.is_deleted is True


@pytest.mark.anyio
async def test_generate_uses_entity_description_as_context(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """DRF-12: Generar draft usa descripción de entidad como contexto adicional del LLM."""
    response = await _create_draft(
        client, sample_collection.id, sample_entity.id, "Expande su historia"
    )
    assert response.status_code == 201

    assert len(mock_llm["invocations"]) >= 1
    payload = mock_llm["invocations"][-1]
    assert "A ranger" in payload["context"]


@pytest.mark.anyio
async def test_filter_drafts_by_status_pending(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """DRF-13: Filtrar drafts por status=pending retorna solo los pendientes."""
    created = await _create_draft(client, sample_collection.id, sample_entity.id, "query pending lore")
    draft_id = created.json()["id"]

    to_confirm = await _create_draft(
        client, sample_collection.id, sample_entity.id, "query to confirm lore"
    )
    # Crear un segundo pending antes de confirmar para que no sea auto-descartado
    # Confirmamos el primero — el segundo queda discarded por auto-discard
    await client.post(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts/{to_confirm.json()['id']}/confirm"
    )

    # Ahora draft_id fue auto-descartado; creamos uno nuevo pending
    new_pending = await _create_draft(
        client, sample_collection.id, sample_entity.id, "nuevo pending lore"
    )
    new_pending_id = new_pending.json()["id"]

    response = await client.get(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts?status=pending"
    )
    assert response.status_code == 200
    body = response.json()
    ids = [d["id"] for d in body["data"]]
    assert new_pending_id in ids
    assert all(d["status"] == "pending" for d in body["data"])


@pytest.mark.anyio
async def test_filter_drafts_by_status_confirmed(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """DRF-14: Filtrar drafts por status=confirmed retorna solo los confirmados."""
    created = await _create_draft(
        client, sample_collection.id, sample_entity.id, "query confirm lore"
    )
    draft_id = created.json()["id"]
    await client.post(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts/{draft_id}/confirm"
    )

    response = await client.get(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts?status=confirmed"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["status"] == "confirmed"


@pytest.mark.anyio
async def test_filter_drafts_created_after_future(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """DRF-15: created_after en el futuro retorna lista vacía."""
    await _create_draft(client, sample_collection.id, sample_entity.id, "query future lore")

    response = await client.get(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts?created_after=2099-01-01T00:00:00"
    )
    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 0
