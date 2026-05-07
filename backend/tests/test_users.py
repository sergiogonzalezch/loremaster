import pytest


@pytest.mark.anyio
async def test_get_my_profile_authenticated(client):
    """USR-01: GET /users/me autenticado retorna 200."""
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-user-id"
    assert data["username"] == "testuser"


@pytest.mark.anyio
async def test_update_my_profile_bio(client):
    """USR-02: PATCH /users/me con bio válida retorna 200."""
    response = await client.patch(
        "/api/v1/users/me",
        json={"bio": "Escritora de mundos"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["bio"] == "Escritora de mundos"


@pytest.mark.anyio
async def test_get_my_profile_fields(client):
    """USR-03: GET /users/me retorna todos los campos de perfil."""
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "username" in data
    assert "display_name" in data
    assert "bio" in data
    assert "avatar_url" in data
    assert "created_at" in data


@pytest.mark.anyio
async def test_patch_multiple_profile_fields(client):
    """USR-04: PATCH /users/me con múltiples campos actualiza todos."""
    response = await client.patch(
        "/api/v1/users/me",
        json={
            "display_name": "Tolkien Fan",
            "bio": "Amante de la fantasía épica",
            "email": "tolkien@example.com",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Tolkien Fan"
    assert data["bio"] == "Amante de la fantasía épica"
    assert data["email"] == "tolkien@example.com"
