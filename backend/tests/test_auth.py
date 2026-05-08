import pytest
from sqlmodel import select
from app.core.auth import hash_password
from app.models.users import User


@pytest.mark.anyio
async def test_register_with_email(client, db_session):
    """AUTH-01: Registro con email retorna 200 y crea usuario con email."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    user = db_session.exec(select(User).where(User.username == "newuser")).first()
    assert user is not None
    assert user.email == "newuser@example.com"


@pytest.mark.anyio
async def test_register_duplicate_email_400(client, db_session):
    """AUTH-02: Registro con email duplicado retorna 400."""
    user = User(
        username="existinguser",
        email="test@example.com",
        hashed_password=hash_password("password123"),
    )
    db_session.add(user)
    db_session.commit()

    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "email": "test@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 400
    assert "correo" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_register_duplicate_username_400(client, db_session):
    """AUTH-03: Registro con username duplicado retorna 400."""
    user = User(
        username="existinguser",
        hashed_password=hash_password("password123"),
    )
    db_session.add(user)
    db_session.commit()

    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "existinguser",
            "email": "new@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 400
    assert "usuario" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_login_with_username(client, db_session):
    """AUTH-04: Login con username funciona."""
    user = User(
        username="testuser2",
        email="test2@example.com",
        hashed_password=hash_password("password123"),
    )
    db_session.add(user)
    db_session.commit()

    response = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "testuser2", "password": "password123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.anyio
async def test_login_with_email(client, db_session):
    """AUTH-05: Login con email funciona."""
    user = User(
        username="testuser3",
        email="test3@example.com",
        hashed_password=hash_password("password123"),
    )
    db_session.add(user)
    db_session.commit()

    response = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "test3@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.anyio
async def test_login_invalid_credentials_401(client, db_session):
    """AUTH-06: Login con credenciales inválidas retorna 401."""
    user = User(
        username="testuser4",
        email="test4@example.com",
        hashed_password=hash_password("password123"),
    )
    db_session.add(user)
    db_session.commit()

    response = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "testuser4", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert "incorrectas" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_login_nonexistent_user_401(client):
    """AUTH-07: Login con usuario inexistente retorna 401."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "nonexistent", "password": "password123"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_register_invalid_email_422(client):
    """AUTH-08: Registro con email inválido retorna 422."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "email": "not-an-email",
            "password": "password123",
        },
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_register_short_password_422(client):
    """AUTH-09: Registro con contraseña muy corta retorna 422."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "short",
        },
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_register_missing_email_422(client):
    """AUTH-10: Registro sin email retorna 422."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "password": "password123",
        },
    )
    assert response.status_code == 422
