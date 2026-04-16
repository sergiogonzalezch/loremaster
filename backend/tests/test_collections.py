import uuid

import pytest
from sqlmodel import select

from app.models.collections import Collection
from app.models.documents import Document
from app.models.entities import Entity
from app.models.entity_text_draft import DraftStatus, EntityTextDraft


@pytest.mark.anyio
async def test_create_collection(client):
    """COL-01: Crear colección retorna 201."""
    response = await client.post(
        "/api/v1/collections/",
        json={"name": "World A", "description": "Desc A"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"]
    assert data["name"] == "World A"
    assert data["description"] == "Desc A"
    assert data["created_at"] is not None


@pytest.mark.anyio
async def test_list_collections(client):
    """COL-02: Listar 2 colecciones retorna count=2."""
    await client.post("/api/v1/collections/", json={"name": "A", "description": "a"})
    await client.post("/api/v1/collections/", json={"name": "B", "description": "b"})

    response = await client.get("/api/v1/collections/")
    assert response.status_code == 200
    assert response.json()["count"] == 2


@pytest.mark.anyio
async def test_get_collection_by_id(client, sample_collection):
    """COL-03: Obtener colección por id retorna 200."""
    response = await client.get(f"/api/v1/collections/{sample_collection.id}")
    assert response.status_code == 200
    assert response.json()["id"] == sample_collection.id


@pytest.mark.anyio
async def test_delete_collection(client, sample_collection):
    """COL-04: Eliminar colección y luego GET retorna 404."""
    delete_response = await client.delete(f"/api/v1/collections/{sample_collection.id}")
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/collections/{sample_collection.id}")
    assert get_response.status_code == 404


@pytest.mark.anyio
async def test_delete_cascades_documents(client, db_session, sample_collection):
    """COL-05: Eliminar colección marca documentos con is_deleted=True."""
    doc = Document(
        collection_id=sample_collection.id,
        filename="doc.txt",
        file_type="text/plain",
        chunk_count=1,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    response = await client.delete(f"/api/v1/collections/{sample_collection.id}")
    assert response.status_code == 204

    db_doc = db_session.exec(select(Document).where(Document.id == doc.id)).first()
    assert db_doc is not None
    assert db_doc.is_deleted is True


@pytest.mark.anyio
async def test_delete_cascades_entities(client, db_session, sample_collection):
    """COL-06: Eliminar colección marca entidades con is_deleted=True."""
    entity = Entity(
        collection_id=sample_collection.id,
        type="character",
        name="Boromir",
        description="Captain",
    )
    db_session.add(entity)
    db_session.commit()
    db_session.refresh(entity)

    response = await client.delete(f"/api/v1/collections/{sample_collection.id}")
    assert response.status_code == 204

    db_entity = db_session.exec(select(Entity).where(Entity.id == entity.id)).first()
    assert db_entity is not None
    assert db_entity.is_deleted is True


@pytest.mark.anyio
async def test_delete_cascades_pending_drafts(
    client, db_session, sample_collection, sample_entity
):
    """COL-07: Eliminar colección descarta drafts pending."""
    draft = EntityTextDraft(
        entity_id=sample_entity.id,
        collection_id=sample_collection.id,
        query="Expandir lore",
        content="Borrador pendiente",
        status=DraftStatus.pending,
    )
    db_session.add(draft)
    db_session.commit()
    db_session.refresh(draft)

    response = await client.delete(f"/api/v1/collections/{sample_collection.id}")
    assert response.status_code == 204

    db_draft = db_session.exec(
        select(EntityTextDraft).where(EntityTextDraft.id == draft.id)
    ).first()
    assert db_draft is not None
    assert db_draft.status == DraftStatus.discarded


@pytest.mark.anyio
async def test_deleted_collection_not_in_list(client, sample_collection):
    """COL-08: Colección eliminada no aparece en listado."""
    await client.delete(f"/api/v1/collections/{sample_collection.id}")

    response = await client.get("/api/v1/collections/")
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["data"]]
    assert sample_collection.id not in ids


@pytest.mark.anyio
async def test_create_duplicate_name_409(client):
    """COL-09: Crear colección duplicada retorna 409."""
    payload = {"name": "Duplicada", "description": "d"}
    first = await client.post("/api/v1/collections/", json=payload)
    assert first.status_code == 201

    second = await client.post("/api/v1/collections/", json=payload)
    assert second.status_code == 409


@pytest.mark.anyio
async def test_get_nonexistent_404(client):
    """COL-10: GET colección inexistente retorna 404."""
    response = await client.get(f"/api/v1/collections/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_delete_nonexistent_404(client):
    """COL-11: DELETE colección inexistente retorna 404."""
    response = await client.delete(f"/api/v1/collections/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_get_deleted_collection_404(client, sample_collection):
    """COL-12: GET colección eliminada retorna 404."""
    await client.delete(f"/api/v1/collections/{sample_collection.id}")
    response = await client.get(f"/api/v1/collections/{sample_collection.id}")
    assert response.status_code == 404
