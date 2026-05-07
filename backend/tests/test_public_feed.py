import pytest


@pytest.mark.anyio
async def test_list_public_collections_without_auth(client, db_session):
    """PUB-01: GET /collections/public sin auth retorna 200."""
    from app.models.collections import Collection

    public_col = Collection(
        name="Public World", description="Public", owner_id="user-a", is_public=True
    )
    private_col = Collection(
        name="Private World", description="Private", owner_id="user-a", is_public=False
    )
    db_session.add(public_col)
    db_session.add(private_col)
    db_session.commit()

    response = await client.get("/api/v1/collections/public")
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["name"] == "Public World"


@pytest.mark.anyio
async def test_private_collection_not_in_public_list(client, db_session, sample_collection):
    """PUB-02: Colección privada no aparece en /public."""
    from app.models.collections import Collection

    public_collection = Collection(
        name="Public", description="", owner_id="test-user-id", is_public=True
    )
    db_session.add(public_collection)
    db_session.commit()

    response = await client.get("/api/v1/collections/public")
    names = [item["name"] for item in response.json()["data"]]
    assert "Public" in names
    assert "Test World" not in names


@pytest.mark.anyio
async def test_get_public_profile(client, db_session):
    """PUB-03: GET /users/{username}/profile retorna 200 con colecciones públicas."""
    from app.models.users import User
    from app.models.collections import Collection

    user = User(id="pub-user-id", username="worldbuilder", hashed_password="hash")
    db_session.add(user)
    db_session.flush()

    public_col = Collection(
        name="My Public World",
        description="Public world",
        owner_id="pub-user-id",
        is_public=True,
    )
    private_col = Collection(
        name="My Private World",
        description="Private world",
        owner_id="pub-user-id",
        is_public=False,
    )
    db_session.add(public_col)
    db_session.add(private_col)
    db_session.commit()

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
async def test_get_private_collection_without_token(client, db_session, sample_collection):
    """PUB-05: GET /collections/{id_privada} sin token retorna 403."""
    response = await client.get(f"/api/v1/collections/{sample_collection.id}")
    assert response.status_code == 403


@pytest.mark.anyio
async def test_get_public_collection_without_token(client, db_session):
    """PUB-06: GET /collections/{id_publica} sin token retorna 200."""
    from app.models.collections import Collection

    public = Collection(
        name="Public", description="", owner_id="some-owner", is_public=True
    )
    db_session.add(public)
    db_session.commit()
    db_session.refresh(public)

    response = await client.get(f"/api/v1/collections/{public.id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Public"


@pytest.mark.anyio
async def test_update_is_public_field(client, sample_collection):
    """PUB-07: PATCH actualizar is_public retorna 200."""
    response = await client.patch(
        f"/api/v1/collections/{sample_collection.id}",
        json={"is_public": True},
    )
    assert response.status_code == 200
    assert response.json()["is_public"] is True