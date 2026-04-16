import uuid

import pytest
from sqlmodel import select

from app.models.collections import Collection
from app.models.entities import Entity
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
    """ENT-02: Listar entidades retorna count=3."""
    payloads = [
        {"type": "character", "name": "A", "description": "a"},
        {"type": "scene", "name": "B", "description": "b"},
        {"type": "faction", "name": "C", "description": "c"},
    ]
    for payload in payloads:
        await client.post(f"/api/v1/collections/{sample_collection.id}/entities", json=payload)

    response = await client.get(f"/api/v1/collections/{sample_collection.id}/entities")
    assert response.status_code == 200
    assert response.json()["count"] == 3


@pytest.mark.anyio
async def test_get_entity_by_id(client, sample_collection, sample_entity):
    """ENT-03: Obtener entidad por id retorna 200."""
    response = await client.get(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}"
    )
    assert response.status_code == 200
    assert response.json()["id"] == sample_entity.id


@pytest.mark.anyio
async def test_update_entity(client, sample_collection, sample_entity):
    """ENT-04: Actualizar entidad retorna 200 y updated_at seteado."""
    response = await client.put(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}",
        json={"type": "character", "name": "Aragorn II", "description": "King"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Aragorn II"
    assert data["updated_at"] is not None


@pytest.mark.anyio
async def test_delete_entity(client, sample_collection, sample_entity):
    """ENT-05: Eliminar entidad retorna 200 y luego GET 404."""
    response = await client.delete(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}"
    )
    assert response.status_code == 200

    get_response = await client.get(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}"
    )
    assert get_response.status_code == 404


@pytest.mark.anyio
async def test_delete_entity_discards_pending_drafts(client, db_session, sample_collection, sample_entity):
    """ENT-06: Eliminar entidad descarta sus drafts pending."""
    d1 = EntityTextDraft(
        entity_id=sample_entity.id,
        collection_id=sample_collection.id,
        query="q1 lorem",
        content="draft 1",
        status=DraftStatus.pending,
    )
    d2 = EntityTextDraft(
        entity_id=sample_entity.id,
        collection_id=sample_collection.id,
        query="q2 lorem",
        content="draft 2",
        status=DraftStatus.pending,
    )
    db_session.add(d1)
    db_session.add(d2)
    db_session.commit()

    response = await client.delete(
        f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}"
    )
    assert response.status_code == 200

    drafts = db_session.exec(
        select(EntityTextDraft).where(EntityTextDraft.entity_id == sample_entity.id)
    ).all()
    assert len(drafts) == 2
    assert all(d.status == DraftStatus.discarded for d in drafts)


@pytest.mark.anyio
async def test_deleted_entity_not_in_list(client, sample_collection, sample_entity):
    """ENT-07: Entidad eliminada no aparece en list."""
    await client.delete(f"/api/v1/collections/{sample_collection.id}/entities/{sample_entity.id}")

    response = await client.get(f"/api/v1/collections/{sample_collection.id}/entities")
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["data"]]
    assert sample_entity.id not in ids


@pytest.mark.anyio
async def test_all_entity_types(client, sample_collection):
    """ENT-08: Todos los tipos válidos de entidad se crean correctamente."""
    for entity_type in ("character", "scene", "faction", "item"):
        response = await client.post(
            f"/api/v1/collections/{sample_collection.id}/entities",
            json={"type": entity_type, "name": f"{entity_type}-name", "description": "ok"},
        )
        assert response.status_code == 201


@pytest.mark.anyio
async def test_create_invalid_type_422(client, sample_collection):
    """ENT-09: Crear entidad con type inválido retorna 422."""
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/entities",
        json={"type": "weapon", "name": "Sword", "description": "invalid"},
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_get_nonexistent_entity_404(client, sample_collection):
    """ENT-10: GET entidad inexistente retorna 404."""
    response = await client.get(f"/api/v1/collections/{sample_collection.id}/entities/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_nonexistent_404(client, sample_collection):
    """ENT-11: PUT entidad inexistente retorna 404."""
    response = await client.put(
        f"/api/v1/collections/{sample_collection.id}/entities/{uuid.uuid4()}",
        json={"type": "character", "name": "Ghost", "description": "none"},
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_entity_wrong_collection_404(client, db_session, sample_entity):
    """ENT-12: Obtener entidad desde otra colección retorna 404."""
    col_b = Collection(name="World B", description="B")
    db_session.add(col_b)
    db_session.commit()
    db_session.refresh(col_b)

    response = await client.get(f"/api/v1/collections/{col_b.id}/entities/{sample_entity.id}")
    assert response.status_code == 404
