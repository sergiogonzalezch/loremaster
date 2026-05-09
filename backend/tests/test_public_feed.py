import pytest


def _make_shared_content(db_session, collection_id, entity_id=None):
    """Helper: inserta un EntityContent confirmed+is_shared en la colección indicada."""
    from app.models.db.entity import Entity, EntityType
    from app.models.db.entity_content import EntityContent
    from app.models.enums import ContentCategory, ContentStatus
    from app.models.db.generated_text import GeneratedText

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
        content="Shared content text for public feed",
        status=ContentStatus.confirmed,
        is_shared=True,
    )
    db_session.add(content)
    db_session.commit()
    return content


@pytest.mark.anyio
async def test_public_feed_shows_shared_content(client, db_session):
    """PUB-01: GET /public/feed devuelve items de contenido compartido con preview y content completo."""
    from app.models.db.user import User
    from app.models.db.collection import Collection

    user = User(id="feed-user-a", username="feeduser", hashed_password="hash")
    db_session.add(user)
    db_session.flush()

    col = Collection(name="My World", description="", owner_id="feed-user-a")
    hidden_col = Collection(name="Private", description="", owner_id="feed-user-a")
    db_session.add(col)
    db_session.add(hidden_col)
    db_session.flush()
    _make_shared_content(db_session, col.id)

    response = await client.get("/api/v1/public/feed")
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 1
    item = body["data"][0]
    assert item["entity_name"] == "Shared Entity"
    assert item["owner_username"] == "feeduser"
    assert "content_preview" in item
    assert "content" in item


@pytest.mark.anyio
async def test_public_feed_unshared_content_not_included(
    client, db_session, sample_collection
):
    """PUB-02: Contenido no compartido no aparece en el feed público."""
    response = await client.get("/api/v1/public/feed")
    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 0


@pytest.mark.anyio
async def test_get_public_profile_returns_shared_contents(client, db_session):
    """PUB-03: GET /users/{username}/profile devuelve shared_contents con info de entidad."""
    from app.models.db.user import User
    from app.models.db.collection import Collection

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
    assert len(data["shared_contents"]) == 1
    item = data["shared_contents"][0]
    assert item["entity_name"] == "Shared Entity"
    assert item["category"] == "backstory"
    assert "public_collections" not in data


@pytest.mark.anyio
async def test_get_profile_nonexistent_user(client):
    """PUB-04: GET /users/noexiste/profile retorna 404."""
    response = await client.get("/api/v1/users/noexiste/profile")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_get_collection_by_non_owner_returns_403(client, db_session):
    """PUB-05: GET /collections/{id} retorna 403 si el usuario no es el owner."""
    from app.models.db.collection import Collection

    other_col = Collection(name="Other World", description="", owner_id="other-user-id")
    db_session.add(other_col)
    db_session.flush()

    response = await client.get(f"/api/v1/collections/{other_col.id}")
    assert response.status_code == 403


@pytest.mark.anyio
async def test_get_collection_with_shared_content_by_non_owner_still_403(
    client, db_session
):
    """PUB-06: GET /collections/{id} retorna 403 incluso con contenido compartido si no eres owner."""
    from app.models.db.collection import Collection

    col = Collection(name="Visible", description="", owner_id="some-owner")
    db_session.add(col)
    db_session.flush()
    _make_shared_content(db_session, col.id)

    response = await client.get(f"/api/v1/collections/{col.id}")
    assert response.status_code == 403


@pytest.mark.anyio
async def test_public_images_feed_shows_shared_images(client, db_session):
    """PUB-08: GET /public/images devuelve imágenes compartidas con info de entidad y owner."""
    from app.models.db.user import User
    from app.models.db.collection import Collection
    from app.models.db.entity import Entity, EntityType
    from app.models.db.image_generation import ImageRecord, ImageGeneration

    user = User(id="img-user-a", username="imageuser", hashed_password="hash")
    db_session.add(user)
    db_session.flush()

    col = Collection(name="Image World", description="", owner_id="img-user-a")
    db_session.add(col)
    db_session.flush()

    entity = Entity(collection_id=col.id, type=EntityType.character, name="Visual Hero")
    db_session.add(entity)
    db_session.flush()

    generation = ImageGeneration(
        entity_id=entity.id,
        collection_id=col.id,
        category="extended_description",
        auto_prompt="auto",
        final_prompt="final",
        batch_size=1,
        backend="mock",
        width=512,
        height=512,
    )
    db_session.add(generation)
    db_session.flush()

    img = ImageRecord(
        generation_id=generation.id,
        entity_id=entity.id,
        collection_id=col.id,
        image_url="http://example.com/img.png",
        is_shared=True,
    )
    db_session.add(img)
    db_session.commit()

    response = await client.get("/api/v1/public/images")
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 1
    item = body["data"][0]
    assert item["entity_name"] == "Visual Hero"
    assert item["owner_username"] == "imageuser"
    assert item["image_url"] == "http://example.com/img.png"


@pytest.mark.anyio
async def test_public_profile_includes_shared_images(client, db_session):
    """PUB-09: GET /users/{username}/profile incluye shared_images además de shared_contents."""
    from app.models.db.user import User
    from app.models.db.collection import Collection
    from app.models.db.entity import Entity, EntityType
    from app.models.db.image_generation import ImageRecord, ImageGeneration

    user = User(id="prof-img-user", username="imgprofile", hashed_password="hash")
    db_session.add(user)
    db_session.flush()

    col = Collection(name="Profile World", description="", owner_id="prof-img-user")
    db_session.add(col)
    db_session.flush()

    entity = Entity(collection_id=col.id, type=EntityType.location, name="Magic Forest")
    db_session.add(entity)
    db_session.flush()

    _make_shared_content(db_session, col.id, entity_id=entity.id)

    generation = ImageGeneration(
        entity_id=entity.id,
        collection_id=col.id,
        category="extended_description",
        auto_prompt="auto",
        final_prompt="final",
        batch_size=1,
        backend="mock",
        width=512,
        height=512,
    )
    db_session.add(generation)
    db_session.flush()

    img = ImageRecord(
        generation_id=generation.id,
        entity_id=entity.id,
        collection_id=col.id,
        image_url="http://example.com/forest.png",
        is_shared=True,
    )
    db_session.add(img)
    db_session.commit()

    response = await client.get("/api/v1/users/imgprofile/profile")
    assert response.status_code == 200
    data = response.json()
    assert len(data["shared_contents"]) == 1
    assert len(data["shared_images"]) == 1
    assert data["shared_images"][0]["entity_name"] == "Magic Forest"
    assert data["shared_images"][0]["image_url"] == "http://example.com/forest.png"


@pytest.mark.anyio
async def test_patch_collection_does_not_accept_is_public(client, sample_collection):
    """PUB-07: PATCH ya no acepta is_public — el campo es ignorado."""
    response = await client.patch(
        f"/api/v1/collections/{sample_collection.id}",
        json={"is_public": True},
    )
    assert response.status_code == 200
    assert "is_public" not in response.json()
