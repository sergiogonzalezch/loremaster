"""Tests del endpoint GET /api/v1/models."""

import httpx
import pytest

_OLLAMA_RESPONSE = {
    "models": [
        {"name": "llama3.2:latest", "size": 2_019_393_189},
        {"name": "mistral:latest", "size": 4_109_854_720},
    ]
}


class _MockOkResponse:
    status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return _OLLAMA_RESPONSE


@pytest.mark.anyio
async def test_list_models_returns_installed_models(client, monkeypatch):
    """Retorna la lista de modelos con is_default marcado correctamente."""
    monkeypatch.setattr(
        "app.api.routes.models.models.httpx.get",
        lambda url, **kwargs: _MockOkResponse(),
    )

    resp = await client.get("/api/v1/models")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2

    llama = next(m for m in data if m["name"] == "llama3.2:latest")
    mistral = next(m for m in data if m["name"] == "mistral:latest")

    assert llama["is_default"] is True
    assert mistral["is_default"] is False
    assert llama["size"] == 2_019_393_189


@pytest.mark.anyio
async def test_list_models_returns_503_when_ollama_unavailable(client, monkeypatch):
    """Retorna 503 cuando Ollama no responde."""

    def _fail(url, **kwargs):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr("app.api.routes.models.models.httpx.get", _fail)

    resp = await client.get("/api/v1/models")

    assert resp.status_code == 503
    assert "disponible" in resp.json()["detail"]


@pytest.mark.anyio
async def test_list_models_requires_auth(monkeypatch):
    """Sin autenticación retorna 401 o 403."""
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    monkeypatch.setattr(
        "app.api.routes.models.models.httpx.get",
        lambda url, **kwargs: _MockOkResponse(),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as unauthenticated_client:
        resp = await unauthenticated_client.get("/api/v1/models")

    assert resp.status_code in (401, 403)
