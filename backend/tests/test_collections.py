import pytest
from sqlmodel import select

from app.models.documents import Document
from app.models.entities import Entity
from app.models.entity_content import EntityContent
from app.models.enums import ContentStatus
from app.models.generated_texts import GeneratedText


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

    assert (
        await client.delete(f"/api/v1/collections/{sample_collection.id}")
    ).status_code == 204

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

    assert (
        await client.delete(f"/api/v1/collections/{sample_collection.id}")
    ).status_code == 204

    db_entity = db_session.exec(select(Entity).where(Entity.id == entity.id)).first()
    assert db_entity.is_deleted is True


@pytest.mark.anyio
async def test_delete_cascades_all_contents(
    client, db_session, sample_collection, sample_entity
):
    """COL-08: Eliminar colección hace soft-delete de EntityContent pending y confirmed."""
    from app.models.enums import ContentCategory

    gt = GeneratedText(
        entity_id=sample_entity.id,
        collection_id=sample_collection.id,
        category="backstory",
        query="query cascade test",
        raw_content="contenido pendiente",
        sources_count=1,
    )
    db_session.add(gt)
    db_session.flush()

    pending = EntityContent(
        entity_id=sample_entity.id,
        collection_id=sample_collection.id,
        generated_text_id=gt.id,
        category=ContentCategory.backstory,
        content="contenido pendiente",
        status=ContentStatus.pending,
    )
    confirmed = EntityContent(
        entity_id=sample_entity.id,
        collection_id=sample_collection.id,
        generated_text_id=gt.id,
        category=ContentCategory.backstory,
        content="contenido confirmado",
        status=ContentStatus.confirmed,
    )
    db_session.add(pending)
    db_session.add(confirmed)
    db_session.commit()
    db_session.refresh(pending)
    db_session.refresh(confirmed)

    assert (
        await client.delete(f"/api/v1/collections/{sample_collection.id}")
    ).status_code == 204

    for content_id in (pending.id, confirmed.id):
        row = db_session.exec(
            select(EntityContent).where(EntityContent.id == content_id)
        ).first()
        assert row.is_deleted is True


@pytest.mark.anyio
async def test_filter_collections_by_name(client):
    """COL-09: Filtrar colecciones por nombre retorna solo las que coinciden."""
    await client.post(
        "/api/v1/collections/", json={"name": "Middle Earth", "description": ""}
    )
    await client.post(
        "/api/v1/collections/", json={"name": "Westeros", "description": ""}
    )
    await client.post(
        "/api/v1/collections/", json={"name": "Middle Ages Lore", "description": ""}
    )

    response = await client.get("/api/v1/collections/?name=middle")
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 2
    names = [item["name"] for item in body["data"]]
    assert "Middle Earth" in names
    assert "Middle Ages Lore" in names
    assert "Westeros" not in names


@pytest.mark.anyio
async def test_filter_collections_by_created_after(client):
    """COL-10: Filtrar colecciones con created_after en el futuro retorna lista vacía."""
    await client.post(
        "/api/v1/collections/", json={"name": "World X", "description": ""}
    )

    response = await client.get(
        "/api/v1/collections/?created_after=2099-01-01T00:00:00"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 0
    assert body["data"] == []


@pytest.mark.anyio
async def test_filter_collections_by_created_before(client):
    """COL-11: Filtrar colecciones con created_before en el pasado retorna lista vacía."""
    await client.post(
        "/api/v1/collections/", json={"name": "World Y", "description": ""}
    )

    response = await client.get(
        "/api/v1/collections/?created_before=2000-01-01T00:00:00"
    )
    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 0


@pytest.mark.anyio
async def test_filter_and_pagination_combined(client):
    """COL-12: Filtro por nombre y paginación combinados funcionan correctamente."""
    for i in range(5):
        await client.post(
            "/api/v1/collections/", json={"name": f"Lore World {i}", "description": ""}
        )
    await client.post(
        "/api/v1/collections/", json={"name": "Unrelated", "description": ""}
    )

    response = await client.get("/api/v1/collections/?name=lore&page=1&page_size=3")
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 5
    assert body["meta"]["page_size"] == 3
    assert len(body["data"]) == 3


@pytest.mark.anyio
async def test_update_collection_name(client, sample_collection):
    """COL-13: PATCH nombre → 200 con datos actualizados."""
    response = await client.patch(
        f"/api/v1/collections/{sample_collection.id}",
        json={"name": "Updated World"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated World"
    assert data["description"] == sample_collection.description
    assert data["updated_at"] is not None


@pytest.mark.anyio
async def test_update_collection_duplicate_name_409(client, sample_collection):
    """COL-14: PATCH con nombre de otra colección activa retorna 409."""
    await client.post(
        "/api/v1/collections/", json={"name": "Other World", "description": ""}
    )

    response = await client.patch(
        f"/api/v1/collections/{sample_collection.id}",
        json={"name": "Other World"},
    )
    assert response.status_code == 409


@pytest.mark.anyio
async def test_update_collection_only_description(client, sample_collection):
    """COL-15: PATCH solo descripción → nombre permanece igual."""
    response = await client.patch(
        f"/api/v1/collections/{sample_collection.id}",
        json={"description": "Nueva descripción"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == sample_collection.name
    assert data["description"] == "Nueva descripción"


@pytest.mark.anyio
async def test_update_collection_not_found(client):
    """COL-16: PATCH colección inexistente retorna 404."""
    response = await client.patch(
        "/api/v1/collections/00000000-0000-0000-0000-000000000000",
        json={"name": "Ghost"},
    )
    assert response.status_code == 404
