import pytest


def _make_shared_content(db_session, collection_id, entity_id=None):
    """Helper: inserta un EntityContent confirmed+is_shared para que la colección aparezca en el feed."""
    from app.models.entities import Entity, EntityType
    from app.models.entity_content import EntityContent
    from app.models.enums import ContentCategory, ContentStatus
    from app.models.generated_texts import GeneratedText

    if entity_id is None:
        entity = Entity(
            collection_id=collection_id,
            type=EntityType.character,
            name="Shared Entity",
        )
        db_session.add(entity)
        db_session.flush()
        entity_id = entity.id

    gt = GeneratedText(
        entity_id=entity_id,
        collection_id=collection_id,
        category=ContentCategory.backstory,
        raw_content="content",
        query="q",
        sources_count=0,
        token_count=0,
    )
    db_session.add(gt)
    db_session.flush()

    content = EntityContent(
        entity_id=entity_id,
        collection_id=collection_id,
        generated_text_id=gt.id,
        category=ContentCategory.backstory,
        content="Shared content text",
        status=ContentStatus.confirmed,
        is_shared=True,
    )
    db_session.add(content)
    db_session.commit()
    return content


@pytest.mark.anyio
async def test_list_public_collections_without_auth(client, db_session):
    """PUB-01: Colección con contenido compartido aparece en /public; sin contenido compartido no."""
    from app.models.collections import Collection

    visible_col = Collection(
        name="Public World", description="Public", owner_id="user-a"
    )
    hidden_col = Collection(
        name="Private World", description="Private", owner_id="user-a"
    )
    db_session.add(visible_col)
    db_session.add(hidden_col)
    db_session.flush()
    _make_shared_content(db_session, visible_col.id)

    response = await client.get("/api/v1/collections/public")
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["name"] == "Public World"


@pytest.mark.anyio
async def test_private_collection_not_in_public_list(
    client, db_session, sample_collection
):
    """PUB-02: Colección sin contenido compartido no aparece en /public."""
    from app.models.collections import Collection

    visible_col = Collection(name="Public", description="", owner_id="test-user-id")
    db_session.add(visible_col)
    db_session.flush()
    _make_shared_content(db_session, visible_col.id)

    response = await client.get("/api/v1/collections/public")
    names = [item["name"] for item in response.json()["data"]]
    assert "Public" in names
    assert "Test World" not in names


@pytest.mark.anyio
async def test_get_public_profile(client, db_session):
    """PUB-03: GET /users/{username}/profile retorna colecciones con contenido compartido."""
    from app.models.users import User
    from app.models.collections import Collection

    user = User(id="pub-user-id", username="worldbuilder", hashed_password="hash")
    db_session.add(user)
    db_session.flush()

    visible_col = Collection(
        name="My Public World", description="Public world", owner_id="pub-user-id"
    )
    hidden_col = Collection(
        name="My Private World", description="Private world", owner_id="pub-user-id"
    )
    db_session.add(visible_col)
    db_session.add(hidden_col)
    db_session.flush()
    _make_shared_content(db_session, visible_col.id)

    response = await client.get("/api/v1/users/worldbuilder/profile")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "worldbuilder"
    assert len(data["public_collections"]) == 1
    assert data["public_collections"][0]["name"] == "My Public World"


@pytest.mark.anyio
async def test_get_profile_nonexistent_user(client):
    """PUB-04: GET /users/noexiste/profile retorna 404."""
    response = await client.get("/api/v1/users/noexiste/profile")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_get_private_collection_without_token(
    client, db_session, sample_collection
):
    """PUB-05: GET /collections/{id} sin token y sin contenido compartido retorna 403."""
    response = await client.get(f"/api/v1/collections/{sample_collection.id}")
    assert response.status_code == 403


@pytest.mark.anyio
async def test_get_collection_with_shared_content_without_token(client, db_session):
    """PUB-06: GET /collections/{id} sin token retorna 200 si tiene contenido compartido."""
    from app.models.collections import Collection

    col = Collection(name="Visible", description="", owner_id="some-owner")
    db_session.add(col)
    db_session.flush()
    _make_shared_content(db_session, col.id)
    db_session.refresh(col)

    response = await client.get(f"/api/v1/collections/{col.id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Visible"


@pytest.mark.anyio
async def test_patch_collection_does_not_accept_is_public(client, sample_collection):
    """PUB-07: PATCH ya no acepta is_public — el campo es ignorado (extra fields ignored by default)."""
    response = await client.patch(
        f"/api/v1/collections/{sample_collection.id}",
        json={"is_public": True},
    )
    assert response.status_code == 200
    assert "is_public" not in response.json()
