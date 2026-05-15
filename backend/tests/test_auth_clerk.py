"""Tests de integración para los endpoints de autenticación Clerk.

CLERK-01 a CLERK-06 — POST /auth/clerk/sync y GET /auth/clerk/verify
"""

import os
import sys
import types
from collections.abc import AsyncGenerator

# Stub de rag antes de importar app (igual que conftest.py)
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-not-for-prod")

if "app.engine.rag" not in sys.modules:
    rag_stub = types.ModuleType("app.engine.rag")
    rag_stub.ingest_chunks = lambda *a, **k: 1
    rag_stub.search_context = lambda *a, **k: ["stub"]
    rag_stub.retrieve_context = lambda *a, **k: ("stub", 1)
    rag_stub.delete_document_chunks = lambda *a, **k: 0
    rag_stub.delete_collection_vectors = lambda *a, **k: True
    rag_stub.ping_qdrant = lambda *a, **k: None
    sys.modules["app.engine.rag"] = rag_stub

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlmodel import Session

from app.database import get_session
from app.main import _csrf_for_unsafe, app
from app.models.db.user import User


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
async def clerk_client(db_session: Session) -> AsyncGenerator[AsyncClient, None]:
    """Client sin stub de get_current_user — usa el flujo real de auth + cookies."""

    def _get_test_session():
        yield db_session

    app.dependency_overrides[get_session] = _get_test_session
    app.dependency_overrides[_csrf_for_unsafe] = lambda: None

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as async_client:
        yield async_client

    app.dependency_overrides.clear()


# Payload Clerk simulado reutilizable en varios tests
_CLERK_PAYLOAD = {
    "sub": "user_clerk_123",
    "email": "clerk@example.com",
    "username": "clerkuser",
}


# ---------------------------------------------------------------------------
# POST /auth/clerk/sync
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_sync_missing_authorization_header(clerk_client):
    """CLERK-01: /sync sin header Authorization retorna 401."""
    response = await clerk_client.post("/api/v1/auth/clerk/sync")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_sync_invalid_clerk_token(clerk_client):
    """CLERK-02: /sync con token Clerk inválido retorna 401."""
    with patch(
        "app.api.routes.auth.auth_clerk.decode_clerk_token",
        side_effect=HTTPException(status_code=401, detail="Token inválido"),
    ):
        response = await clerk_client.post(
            "/api/v1/auth/clerk/sync",
            headers={"Authorization": "Bearer bad-token"},
        )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_sync_new_user_creates_and_sets_cookies(clerk_client, db_session):
    """CLERK-03: /sync con token válido crea el User local y setea cookies."""
    with patch(
        "app.api.routes.auth.auth_clerk.decode_clerk_token",
        return_value=_CLERK_PAYLOAD,
    ):
        response = await clerk_client.post(
            "/api/v1/auth/clerk/sync",
            headers={"Authorization": "Bearer valid-clerk-token"},
        )

    assert response.status_code == 200
    assert response.json()["username"] == "clerkuser"

    # Cookie de sesión seteada
    assert "access_token" in response.cookies

    # User creado en BD con el sub de Clerk como ID
    user = db_session.get(User, "user_clerk_123")
    assert user is not None
    assert user.email == "clerk@example.com"
    assert user.username == "clerkuser"
    assert user.hashed_password == ""


@pytest.mark.anyio
async def test_sync_existing_user_is_idempotent(clerk_client, db_session):
    """CLERK-04: /sync con user ya existente retorna 200 sin duplicar el registro."""
    existing = User(
        id="user_clerk_123",
        username="clerkuser",
        email="clerk@example.com",
        hashed_password="",
    )
    db_session.add(existing)
    db_session.commit()

    with patch(
        "app.api.routes.auth.auth_clerk.decode_clerk_token",
        return_value=_CLERK_PAYLOAD,
    ):
        response = await clerk_client.post(
            "/api/v1/auth/clerk/sync",
            headers={"Authorization": "Bearer valid-clerk-token"},
        )

    assert response.status_code == 200

    # Solo existe un user con ese ID
    from sqlmodel import select
    users = db_session.exec(select(User).where(User.id == "user_clerk_123")).all()
    assert len(users) == 1


@pytest.mark.anyio
async def test_sync_uses_email_prefix_when_no_username(clerk_client, db_session):
    """CLERK-03b: cuando el payload Clerk no trae 'username', usa el prefijo del email."""
    payload_no_username = {"sub": "user_clerk_456", "email": "noname@example.com"}

    with patch(
        "app.api.routes.auth.auth_clerk.decode_clerk_token",
        return_value=payload_no_username,
    ):
        response = await clerk_client.post(
            "/api/v1/auth/clerk/sync",
            headers={"Authorization": "Bearer valid-clerk-token"},
        )

    assert response.status_code == 200
    user = db_session.get(User, "user_clerk_456")
    assert user is not None
    assert user.username == "noname"


# ---------------------------------------------------------------------------
# GET /auth/clerk/verify
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_verify_valid_token_and_existing_user(clerk_client, db_session):
    """CLERK-05: /verify con token válido y user en BD retorna {valid: True}."""
    user = User(
        id="user_clerk_789",
        username="verifyuser",
        email="verify@example.com",
        hashed_password="",
    )
    db_session.add(user)
    db_session.commit()

    with patch(
        "app.api.routes.auth.auth_clerk.decode_clerk_token",
        return_value={"sub": "user_clerk_789"},
    ):
        response = await clerk_client.get(
            "/api/v1/auth/clerk/verify",
            headers={"Authorization": "Bearer valid-clerk-token"},
        )

    assert response.status_code == 200
    assert response.json() == {"valid": True, "user_id": "user_clerk_789"}


@pytest.mark.anyio
async def test_verify_soft_deleted_user_returns_401(clerk_client, db_session):
    """CLERK-06: /verify con user soft-deleted retorna 401."""
    from datetime import UTC, datetime

    user = User(
        id="user_clerk_deleted",
        username="deleteduser",
        email="deleted@example.com",
        hashed_password="",
        is_deleted=True,
        deleted_at=datetime.now(UTC),
    )
    db_session.add(user)
    db_session.commit()

    with patch(
        "app.api.routes.auth.auth_clerk.decode_clerk_token",
        return_value={"sub": "user_clerk_deleted"},
    ):
        response = await clerk_client.get(
            "/api/v1/auth/clerk/verify",
            headers={"Authorization": "Bearer valid-clerk-token"},
        )

    assert response.status_code == 401
