import uuid

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
async def test_list_drafts(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """DRF-02: Listar drafts retorna count=2 en orden desc por created_at."""
    first = await _create_draft(
        client, sample_collection.id, sample_entity.id, "consulta uno"
    )
    second = await _create_draft(
        client, sample_collection.id, sample_entity.id, "consulta dos"
    )
    assert first.status_code == 201
    assert second.status_code == 201

    response = await client.get(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    created = [item["created_at"] for item in data["data"]]
    assert created == sorted(created, reverse=True)


@pytest.mark.anyio
async def test_update_draft_content(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """DRF-03: Actualizar contenido de draft retorna 200."""
    created = await _create_draft(client, sample_collection.id, sample_entity.id)
    draft_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts/{draft_id}",
        json={"content": "Contenido actualizado"},
    )
    assert response.status_code == 200
    assert response.json()["content"] == "Contenido actualizado"


@pytest.mark.anyio
async def test_confirm_draft_updates_entity(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """DRF-04: Confirmar draft actualiza descripción de entidad."""
    created = await _create_draft(client, sample_collection.id, sample_entity.id)
    draft = created.json()

    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts/{draft['id']}/confirm"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == draft["content"]
    assert data["updated_at"] is not None


@pytest.mark.anyio
async def test_discard_draft(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """DRF-05: Descartar draft cambia status a discarded."""
    created = await _create_draft(client, sample_collection.id, sample_entity.id)
    draft_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts/{draft_id}/discard"
    )
    assert response.status_code == 200
    assert response.json()["status"] == "discarded"


@pytest.mark.anyio
async def test_confirm_auto_discards_other_pending(
    client, db_session, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """DRF-06: Confirmar un draft descarta automáticamente otros pending."""
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
async def test_discarded_drafts_not_in_list(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """DRF-07: Draft descartado no aparece en list."""
    created = await _create_draft(client, sample_collection.id, sample_entity.id)
    draft_id = created.json()["id"]
    await client.patch(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts/{draft_id}/discard"
    )

    listed = await client.get(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts"
    )
    ids = [item["id"] for item in listed.json()["data"]]
    assert draft_id not in ids


@pytest.mark.anyio
async def test_confirmed_drafts_in_list(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """DRF-08: Draft confirmado aparece en list con status confirmed."""
    created = await _create_draft(client, sample_collection.id, sample_entity.id)
    draft_id = created.json()["id"]
    await client.post(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts/{draft_id}/confirm"
    )

    listed = await client.get(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts"
    )
    confirmed = [d for d in listed.json()["data"] if d["id"] == draft_id]
    assert len(confirmed) == 1
    assert confirmed[0]["status"] == "confirmed"


@pytest.mark.anyio
async def test_generate_uses_entity_description_as_context(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """DRF-09: Generar draft usa descripción de entidad en el contexto del LLM."""
    response = await _create_draft(
        client, sample_collection.id, sample_entity.id, "Expande su historia"
    )
    assert response.status_code == 201

    assert len(mock_llm["invocations"]) >= 1
    payload = mock_llm["invocations"][-1]
    assert "A ranger" in payload["context"]


@pytest.mark.anyio
async def test_max_pending_drafts_409(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """DRF-10: Máximo 5 drafts pending; sexto retorna 409."""
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
async def test_generate_nonexistent_entity_404(
    client, mock_rag_engine, mock_llm, sample_collection
):
    """DRF-11: Generar draft para entidad inexistente retorna 404."""
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/entities/{uuid.uuid4()}/generate",
        json={"query": "consulta válida"},
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_confirm_nonexistent_draft_404(client, sample_collection, sample_entity):
    """DRF-12: Confirmar draft inexistente retorna 404."""
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts/{uuid.uuid4()}/confirm"
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_query_too_short_422(client, sample_collection, sample_entity):
    """DRF-13: Query muy corta retorna 422."""
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/generate",
        json={"query": "abc"},
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_soft_delete_draft(
    client, mock_rag_engine, mock_llm, db_session, sample_collection, sample_entity
):
    """DRF-15: DELETE real hace soft-delete del draft, retorna 204."""
    created = await _create_draft(client, sample_collection.id, sample_entity.id)
    draft_id = created.json()["id"]

    response = await client.delete(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts/{draft_id}"
    )
    assert response.status_code == 204

    from app.models.entity_text_draft import EntityTextDraft

    db_draft = db_session.exec(
        select(EntityTextDraft).where(EntityTextDraft.id == draft_id)
    ).first()
    assert db_draft is not None
    assert db_draft.is_deleted is True


@pytest.mark.anyio
async def test_soft_deleted_draft_not_in_list(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """DRF-16: Draft soft-deleted no aparece en listado."""
    created = await _create_draft(client, sample_collection.id, sample_entity.id)
    draft_id = created.json()["id"]

    await client.delete(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts/{draft_id}"
    )

    listed = await client.get(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts"
    )
    ids = [item["id"] for item in listed.json()["data"]]
    assert draft_id not in ids


@pytest.mark.anyio
async def test_update_confirmed_draft_404(
    client, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """DRF-14: Actualizar draft confirmado retorna 404 (solo pending)."""
    created = await _create_draft(client, sample_collection.id, sample_entity.id)
    draft_id = created.json()["id"]
    await client.post(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts/{draft_id}/confirm"
    )

    response = await client.patch(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}/drafts/{draft_id}",
        json={"content": "intento posterior"},
    )
    assert response.status_code == 404
