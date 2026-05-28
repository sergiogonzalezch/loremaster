"""Tests para la capa semántica de moderación — Llama Guard 3.

Todos los tests mockean httpx.AsyncClient para no depender de Ollama real.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.exceptions import GeneratedContentBlockedError
from app.domain.llama_guard import _build_guard_prompt, check_with_llama_guard

# ── Helpers ──────────────────────────────────────────────────────────────────


def _mock_ollama_response(response_text: str) -> MagicMock:
    """Crea un mock de httpx.Response con el texto dado."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": response_text}
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


# ── LG-01: guard desactivado ──────────────────────────────────────────────────


@pytest.mark.anyio
async def test_lg_01_guard_disabled_skips_call(override_settings):
    """Guard desactivado: no llama a Ollama y pasa sin error."""
    override_settings(llama_guard_enabled=False)
    with patch("app.domain.llama_guard.httpx.AsyncClient") as mock_client:
        await check_with_llama_guard("cualquier query", "cualquier respuesta")
        mock_client.assert_not_called()


# ── LG-02: respuesta safe ─────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_lg_02_safe_response_passes(override_settings):
    """Guard activo + Ollama responde 'safe' → sin excepción."""
    override_settings(llama_guard_enabled=True)
    mock_resp = _mock_ollama_response("safe")
    mock_post = AsyncMock(return_value=mock_resp)
    with patch("app.domain.llama_guard.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = mock_post
        await check_with_llama_guard("¿quién es el rey?", "El rey es Arturo.")


# ── LG-03: respuesta unsafe ───────────────────────────────────────────────────


@pytest.mark.anyio
async def test_lg_03_unsafe_response_raises(override_settings):
    """Guard activo + Ollama responde 'unsafe\\nS1' → GeneratedContentBlockedError."""
    override_settings(llama_guard_enabled=True)
    mock_resp = _mock_ollama_response("unsafe\nS1")
    mock_post = AsyncMock(return_value=mock_resp)
    with patch("app.domain.llama_guard.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = mock_post
        with pytest.raises(GeneratedContentBlockedError):
            await check_with_llama_guard("query", "respuesta con contenido violento")


@pytest.mark.anyio
async def test_lg_03b_unsafe_multiple_categories(override_settings):
    """Guard activo + múltiples categorías violadas → GeneratedContentBlockedError."""
    override_settings(llama_guard_enabled=True)
    mock_resp = _mock_ollama_response("unsafe\nS1,S4,S10")
    mock_post = AsyncMock(return_value=mock_resp)
    with patch("app.domain.llama_guard.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = mock_post
        with pytest.raises(GeneratedContentBlockedError):
            await check_with_llama_guard("query", "respuesta bloqueada")


# ── LG-04: timeout ────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_lg_04_timeout_is_fail_open(override_settings):
    """Guard activo + timeout de Ollama → fail-open (sin excepción)."""
    import httpx

    override_settings(llama_guard_enabled=True)
    mock_post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
    with patch("app.domain.llama_guard.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = mock_post
        await check_with_llama_guard("query", "respuesta larga")


# ── LG-05: Ollama caído ───────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_lg_05_connection_error_is_fail_open(override_settings):
    """Guard activo + Ollama caído → fail-open (sin excepción)."""
    import httpx

    override_settings(llama_guard_enabled=True)
    mock_post = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
    with patch("app.domain.llama_guard.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = mock_post
        await check_with_llama_guard("query", "respuesta")


# ── LG-06: respuesta vacía ───────────────────────────────────────────────────


@pytest.mark.anyio
async def test_lg_06_empty_response_is_fail_open(override_settings):
    """Guard activo + respuesta vacía del modelo → fail-open (no es 'unsafe')."""
    override_settings(llama_guard_enabled=True)
    mock_resp = _mock_ollama_response("")
    mock_post = AsyncMock(return_value=mock_resp)
    with patch("app.domain.llama_guard.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = mock_post
        await check_with_llama_guard("query", "respuesta")


# ── LG-07: prompt builder ────────────────────────────────────────────────────


def test_lg_07_prompt_contains_required_sections():
    """El prompt generado contiene todas las secciones requeridas por Llama Guard 3."""
    prompt = _build_guard_prompt("¿cómo hacer una bomba?", "No puedo responder eso.")
    assert "<BEGIN UNSAFE CONTENT CATEGORIES>" in prompt
    assert "<END UNSAFE CONTENT CATEGORIES>" in prompt
    assert "<BEGIN CONVERSATION>" in prompt
    assert "<END CONVERSATION>" in prompt
    assert "S1: Violent Crimes." in prompt
    assert "S13: Elections." in prompt
    assert "¿cómo hacer una bomba?" in prompt
    assert "No puedo responder eso." in prompt


def test_lg_07b_prompt_contains_agent_role():
    """El prompt evalúa el rol 'Agent' (salida del LLM), no el usuario."""
    prompt = _build_guard_prompt("query", "response")
    assert "'Agent'" in prompt
    assert "ONLY THE LAST 'Agent' turn" in prompt


# ── Fixture ───────────────────────────────────────────────────────────────────


@pytest.fixture
def override_settings():
    """Permite sobrescribir settings en tests sin modificar el objeto global."""
    from app.core.config import settings

    def _override(**kwargs):
        for key, value in kwargs.items():
            object.__setattr__(settings, key, value)

    original = {
        "llama_guard_enabled": settings.llama_guard_enabled,
        "llama_guard_model": settings.llama_guard_model,
        "llama_guard_timeout": settings.llama_guard_timeout,
    }
    yield _override
    for key, value in original.items():
        object.__setattr__(settings, key, value)
