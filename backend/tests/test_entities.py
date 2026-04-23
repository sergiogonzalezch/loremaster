import pytest
from sqlmodel import select

from app.models.collections import Collection
from app.models.entity_text_draft import DraftStatus, EntityTextDraft


@pytest.mark.anyio
async def test_create_entity(client, sample_collection):
    """ENT-01: Crear entidad character retorna 201."""
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/entities",
        json={"type": "character", "name": "Gandalf", "description": "Wizard"},
    )
    assert response.status_code == 201


@pytest.mark.anyio
async def test_list_entities(client, sample_collection):
    """ENT-02: Listar entidades retorna count correcto."""
    payloads = [
        {"type": "character", "name": "A", "description": "a"},
        {"type": "creature", "name": "B", "description": "b"},
        {"type": "faction", "name": "C", "description": "c"},
    ]
    for payload in payloads:
        await client.post(
            f"/api/v1/collections/{sample_collection.id}/entities", json=payload
        )

    response = await client.get(f"/api/v1/collections/{sample_collection.id}/entities")
    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 3


@pytest.mark.anyio
async def test_update_entity(client, sample_collection, sample_entity):
    """ENT-03: Actualizar entidad retorna 200 con datos actualizados."""
    response = await client.patch(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}",
        json={"type": "character", "name": "Aragorn II", "description": "King"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Aragorn II"


@pytest.mark.anyio
async def test_partial_update_entity(client, sample_collection, sample_entity):
    """ENT-04: Actualización parcial solo modifica campos enviados."""
    response = await client.patch(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}",
        json={"description": "King of Gondor"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Aragorn"
    assert data["type"] == "character"
    assert data["description"] == "King of Gondor"


@pytest.mark.anyio
async def test_delete_entity(client, sample_collection, sample_entity):
    """ENT-05: Eliminar entidad retorna 204 y luego GET retorna 404."""
    assert (
        await client.delete(
            f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}"
        )
    ).status_code == 204

    assert (
        await client.get(
            f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}"
        )
    ).status_code == 404


@pytest.mark.anyio
async def test_delete_entity_cascades_all_drafts(
    client, db_session, sample_collection, sample_entity
):
    """ENT-06: Eliminar entidad hace soft-delete de drafts pending y confirmed."""
    pending = EntityTextDraft(
        entity_id=sample_entity.id,
        collection_id=sample_collection.id,
        query="q1 lorem",
        content="draft pending",
        status=DraftStatus.pending,
    )
    confirmed = EntityTextDraft(
        entity_id=sample_entity.id,
        collection_id=sample_collection.id,
        query="q2 lorem",
        content="draft confirmed",
        status=DraftStatus.confirmed,
    )
    db_session.add(pending)
    db_session.add(confirmed)
    db_session.commit()

    assert (
        await client.delete(
            f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}"
        )
    ).status_code == 204

    drafts = db_session.exec(
        select(EntityTextDraft).where(EntityTextDraft.entity_id == sample_entity.id)
    ).all()
    assert len(drafts) == 2
    assert all(d.is_deleted is True for d in drafts)


@pytest.mark.anyio
async def test_all_entity_types(client, sample_collection):
    """ENT-07: Todos los tipos válidos de entidad se crean correctamente."""
    for entity_type in ("character", "creature", "faction", "location", "item"):
        response = await client.post(
            f"/api/v1/collections/{sample_collection.id}/entities",
            json={"type": entity_type, "name": f"{entity_type}-name", "description": "ok"},
        )
        assert response.status_code == 201


@pytest.mark.anyio
async def test_entity_wrong_collection_404(client, db_session, sample_entity):
    """ENT-08: Obtener entidad desde colección incorrecta retorna 404."""
    col_b = Collection(name="World B", description="B")
    db_session.add(col_b)
    db_session.commit()
    db_session.refresh(col_b)

    response = await client.get(
        f"/api/v1/collections/{col_b.id}/entities/{sample_entity.id}"
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_filter_entities_by_name(client, sample_collection):
    """ENT-09: Filtrar entidades por nombre retorna solo las que coinciden."""
    for payload in [
        {"type": "character", "name": "Gandalf the Grey", "description": ""},
        {"type": "character", "name": "Gandalf the White", "description": ""},
        {"type": "faction", "name": "Fellowship", "description": ""},
    ]:
        await client.post(
            f"/api/v1/collections/{sample_collection.id}/entities", json=payload
        )

    response = await client.get(
        f"/api/v1/collections/{sample_collection.id}/entities?name=gandalf"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 2
    names = [e["name"] for e in body["data"]]
    assert "Gandalf the Grey" in names
    assert "Gandalf the White" in names
    assert "Fellowship" not in names


@pytest.mark.anyio
async def test_filter_entities_by_type(client, sample_collection):
    """ENT-10: Filtrar entidades por tipo retorna solo las de ese tipo."""
    for payload in [
        {"type": "character", "name": "Frodo", "description": ""},
        {"type": "character", "name": "Sam", "description": ""},
        {"type": "item", "name": "One Ring", "description": ""},
    ]:
        await client.post(
            f"/api/v1/collections/{sample_collection.id}/entities", json=payload
        )

    response = await client.get(
        f"/api/v1/collections/{sample_collection.id}/entities?type=character"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 2
    assert all(e["type"] == "character" for e in body["data"])


@pytest.mark.anyio
async def test_filter_entities_name_and_type_combined(client, sample_collection):
    """ENT-11: Filtrar por nombre y tipo combinados retorna solo el cruce exacto."""
    for payload in [
        {"type": "character", "name": "Arwen", "description": ""},
        {"type": "location", "name": "Arwen's Camp", "description": ""},
        {"type": "character", "name": "Aragorn", "description": ""},
    ]:
        await client.post(
            f"/api/v1/collections/{sample_collection.id}/entities", json=payload
        )

    response = await client.get(
        f"/api/v1/collections/{sample_collection.id}/entities?name=arwen&type=character"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["name"] == "Arwen"


@pytest.mark.anyio
async def test_filter_entities_created_after_future(client, sample_collection):
    """ENT-12: created_after en el futuro retorna lista vacía."""
    await client.post(
        f"/api/v1/collections/{sample_collection.id}/entities",
        json={"type": "character", "name": "Legolas", "description": ""},
    )

    response = await client.get(
        f"/api/v1/collections/{sample_collection.id}/entities?created_after=2099-01-01T00:00:00"
    )
    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 0