import pytest
from sqlmodel import select

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


@pytest.mark.anyio
async def test_list_collections(client):
    """COL-02: Listar colecciones retorna count correcto."""
    await client.post("/api/v1/collections/", json={"name": "A", "description": "a"})
    await client.post("/api/v1/collections/", json={"name": "B", "description": "b"})

    response = await client.get("/api/v1/collections/")
    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 2


@pytest.mark.anyio
async def test_delete_collection(client, sample_collection):
    """COL-03: Eliminar colección retorna 204 y luego GET retorna 404."""
    delete_response = await client.delete(f"/api/v1/collections/{sample_collection.id}")
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/collections/{sample_collection.id}")
    assert get_response.status_code == 404


@pytest.mark.anyio
async def test_deleted_collection_not_in_list(client, sample_collection):
    """COL-04: Colección eliminada no aparece en listado."""
    await client.delete(f"/api/v1/collections/{sample_collection.id}")

    response = await client.get("/api/v1/collections/")
    ids = [item["id"] for item in response.json()["data"]]
    assert sample_collection.id not in ids


@pytest.mark.anyio
async def test_create_duplicate_name_409(client):
    """COL-05: Crear colección con nombre duplicado retorna 409."""
    payload = {"name": "Duplicada", "description": "d"}
    assert (await client.post("/api/v1/collections/", json=payload)).status_code == 201
    assert (await client.post("/api/v1/collections/", json=payload)).status_code == 409


@pytest.mark.anyio
async def test_delete_cascades_documents(client, db_session, sample_collection):
    """COL-06: Eliminar colección hace soft-delete de sus documentos."""
    doc = Document(
        collection_id=sample_collection.id,
        filename="doc.txt",
        file_type="text/plain",
        chunk_count=1,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    assert (await client.delete(f"/api/v1/collections/{sample_collection.id}")).status_code == 204

    db_doc = db_session.exec(select(Document).where(Document.id == doc.id)).first()
    assert db_doc.is_deleted is True


@pytest.mark.anyio
async def test_delete_cascades_entities(client, db_session, sample_collection):
    """COL-07: Eliminar colección hace soft-delete de sus entidades."""
    entity = Entity(
        collection_id=sample_collection.id,
        type="character",
        name="Boromir",
        description="Captain",
    )
    db_session.add(entity)
    db_session.commit()
    db_session.refresh(entity)

    assert (await client.delete(f"/api/v1/collections/{sample_collection.id}")).status_code == 204

    db_entity = db_session.exec(select(Entity).where(Entity.id == entity.id)).first()
    assert db_entity.is_deleted is True


@pytest.mark.anyio
async def test_delete_cascades_all_drafts(
    client, db_session, sample_collection, sample_entity
):
    """COL-08: Eliminar colección hace soft-delete de drafts pending y confirmed."""
    pending = EntityTextDraft(
        entity_id=sample_entity.id,
        collection_id=sample_collection.id,
        query="query pending",
        content="borrador pendiente",
        status=DraftStatus.pending,
    )
    confirmed = EntityTextDraft(
        entity_id=sample_entity.id,
        collection_id=sample_collection.id,
        query="query confirmed",
        content="borrador confirmado",
        status=DraftStatus.confirmed,
    )
    db_session.add(pending)
    db_session.add(confirmed)
    db_session.commit()
    db_session.refresh(pending)
    db_session.refresh(confirmed)

    assert (await client.delete(f"/api/v1/collections/{sample_collection.id}")).status_code == 204

    for draft_id in (pending.id, confirmed.id):
        db_draft = db_session.exec(
            select(EntityTextDraft).where(EntityTextDraft.id == draft_id)
        ).first()
        assert db_draft.is_deleted is True