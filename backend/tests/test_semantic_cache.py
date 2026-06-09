"""Tests del módulo de caché semántica RAG.

Cubre:
- Lookup con hit (similitud >= threshold)
- Lookup con miss (similitud < threshold)
- Store almacena con TTL
- Fail-open si Redis no responde
- Comportamiento cuando caché está desactivada
"""

import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

import app.engine.semantic_cache as cache_mod


@pytest.fixture()
def mock_redis_client():
    """Fixture: cliente Redis falso con scan_iter y get/set en memoria."""
    store: dict[bytes, bytes] = {}

    client = MagicMock()
    client.ping.return_value = True

    def _set(key, value, ex=None):
        store[key.encode() if isinstance(key, str) else key] = (
            value.encode() if isinstance(value, str) else value
        )

    def _get(key):
        return store.get(key.encode() if isinstance(key, str) else key)

    def _scan_iter(pattern):
        prefix = pattern.replace("*", "").encode()
        return [k for k in store if k.startswith(prefix)]

    client.set.side_effect = _set
    client.get.side_effect = _get
    client.scan_iter.side_effect = _scan_iter
    return client, store


@pytest.fixture(autouse=True)
def reset_module_client():
    """Resetea el cliente global entre tests para evitar estado compartido."""
    original = cache_mod._client
    cache_mod._client = None
    yield
    cache_mod._client = original


def _make_vec(value: float, dims: int = 384) -> np.ndarray:
    v = np.zeros(dims, dtype=np.float32)
    v[0] = value
    return v


# ─── lookup ───────────────────────────────────────────────────────────────────

def test_lookup_returns_none_when_disabled(monkeypatch):
    """CACHE-01: Lookup devuelve None si caché está desactivada."""
    monkeypatch.setattr(cache_mod.settings, "semantic_cache_enabled", False)
    result = cache_mod.lookup("col-1", _make_vec(1.0))
    assert result is None


def test_lookup_returns_none_on_redis_failure(monkeypatch):
    """CACHE-02: Lookup devuelve None (fail-open) si Redis no responde."""
    monkeypatch.setattr(cache_mod.settings, "semantic_cache_enabled", True)

    def _fail(*_a, **_kw):
        raise ConnectionError("Redis down")

    with patch.object(cache_mod._redis_lib, "from_url", side_effect=_fail):
        result = cache_mod.lookup("col-1", _make_vec(1.0))
    assert result is None


def test_lookup_hit_identical_vectors(monkeypatch, mock_redis_client):
    """CACHE-03: Lookup devuelve respuesta cacheada si similitud == 1.0."""
    client, _ = mock_redis_client
    monkeypatch.setattr(cache_mod.settings, "semantic_cache_enabled", True)
    monkeypatch.setattr(cache_mod.settings, "semantic_cache_threshold", 0.95)
    cache_mod._client = client

    vec = _make_vec(1.0)
    entry = json.dumps({"embedding": vec.tolist(), "answer": "Respuesta cacheada"}).encode()
    client.scan_iter.side_effect = lambda _pattern: [b"scache:col-1:some-uuid"]
    client.get.side_effect = lambda _key: entry

    result = cache_mod.lookup("col-1", vec)
    assert result == "Respuesta cacheada"


def test_lookup_miss_low_similarity(monkeypatch, mock_redis_client):
    """CACHE-04: Lookup devuelve None si similitud < threshold."""
    client, _ = mock_redis_client
    monkeypatch.setattr(cache_mod.settings, "semantic_cache_enabled", True)
    monkeypatch.setattr(cache_mod.settings, "semantic_cache_threshold", 0.95)
    cache_mod._client = client

    stored_vec = _make_vec(1.0)
    query_vec = _make_vec(0.0)
    query_vec[1] = 1.0  # ortogonal → similitud 0

    entry = json.dumps({"embedding": stored_vec.tolist(), "answer": "Respuesta lejana"}).encode()
    client.scan_iter.side_effect = lambda _pattern: [b"scache:col-1:some-uuid"]
    client.get.side_effect = lambda _key: entry

    result = cache_mod.lookup("col-1", query_vec)
    assert result is None


def test_lookup_empty_cache(monkeypatch, mock_redis_client):
    """CACHE-05: Lookup devuelve None si no hay entradas para la colección."""
    client, _ = mock_redis_client
    monkeypatch.setattr(cache_mod.settings, "semantic_cache_enabled", True)
    cache_mod._client = client

    client.scan_iter.side_effect = lambda _pattern: []
    result = cache_mod.lookup("col-1", _make_vec(1.0))
    assert result is None


# ─── store ────────────────────────────────────────────────────────────────────

def test_store_is_noop_when_disabled(monkeypatch, mock_redis_client):
    """CACHE-06: Store no escribe en Redis si caché está desactivada."""
    client, store = mock_redis_client
    monkeypatch.setattr(cache_mod.settings, "semantic_cache_enabled", False)
    cache_mod._client = client

    cache_mod.store("col-1", _make_vec(1.0), "respuesta")
    assert len(store) == 0


def test_store_writes_entry_with_ttl(monkeypatch, mock_redis_client):
    """CACHE-07: Store escribe embedding + answer con el TTL configurado."""
    client, store = mock_redis_client
    monkeypatch.setattr(cache_mod.settings, "semantic_cache_enabled", True)
    monkeypatch.setattr(cache_mod.settings, "semantic_cache_ttl", 3600)
    cache_mod._client = client

    vec = _make_vec(1.0)
    cache_mod.store("col-1", vec, "mi respuesta")

    assert client.set.called
    call_kwargs = client.set.call_args
    assert call_kwargs.kwargs.get("ex") == 3600 or (len(call_kwargs.args) >= 3 and call_kwargs.args[2] == 3600)

    raw = list(store.values())[0]
    entry = json.loads(raw)
    assert entry["answer"] == "mi respuesta"
    assert len(entry["embedding"]) == 384


def test_store_survives_redis_failure(monkeypatch):
    """CACHE-08: Store no lanza excepción si Redis falla (fail-open)."""
    monkeypatch.setattr(cache_mod.settings, "semantic_cache_enabled", True)

    broken = MagicMock()
    broken.set.side_effect = ConnectionError("Redis down")
    cache_mod._client = broken

    cache_mod.store("col-1", _make_vec(1.0), "respuesta")  # debe silenciarse


# ─── round-trip ───────────────────────────────────────────────────────────────

def test_store_then_lookup_hit(monkeypatch, mock_redis_client):
    """CACHE-09: Store seguido de lookup con mismo vector devuelve la respuesta."""
    client, _ = mock_redis_client
    monkeypatch.setattr(cache_mod.settings, "semantic_cache_enabled", True)
    monkeypatch.setattr(cache_mod.settings, "semantic_cache_threshold", 0.95)
    monkeypatch.setattr(cache_mod.settings, "semantic_cache_ttl", 3600)
    cache_mod._client = client

    vec = _make_vec(1.0)
    cache_mod.store("col-1", vec, "respuesta original")
    result = cache_mod.lookup("col-1", vec)
    assert result == "respuesta original"


def test_store_then_lookup_different_collection(monkeypatch, mock_redis_client):
    """CACHE-10: Lookup en colección diferente no devuelve entradas de otra colección."""
    client, _ = mock_redis_client
    monkeypatch.setattr(cache_mod.settings, "semantic_cache_enabled", True)
    monkeypatch.setattr(cache_mod.settings, "semantic_cache_threshold", 0.95)
    monkeypatch.setattr(cache_mod.settings, "semantic_cache_ttl", 3600)
    cache_mod._client = client

    vec = _make_vec(1.0)
    cache_mod.store("col-A", vec, "respuesta de col-A")
    result = cache_mod.lookup("col-B", vec)
    assert result is None
