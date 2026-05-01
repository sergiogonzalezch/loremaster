import pytest

from app.services import deletion_service


def test_delete_vectors_with_retry_retries_until_success(monkeypatch):
    """DEL-01: Reintenta hasta éxito dentro del límite configurado."""
    calls = {"count": 0}

    def _flaky(_collection_id: str):
        calls["count"] += 1
        if calls["count"] < 3:
            raise RuntimeError("temporary qdrant error")
        return True

    monkeypatch.setattr(deletion_service, "delete_collection_vectors", _flaky)
    monkeypatch.setattr(deletion_service.time, "sleep", lambda _x: None)

    ok = deletion_service._delete_vectors_with_retry("col-1")

    assert ok is True
    assert calls["count"] == 3


def test_delete_vectors_with_retry_logs_orphans_on_final_failure(monkeypatch, caplog):
    """DEL-02: Si todos los intentos fallan, retorna False y loguea orphans."""

    def _always_fail(_collection_id: str):
        raise RuntimeError("qdrant down")

    monkeypatch.setattr(deletion_service, "delete_collection_vectors", _always_fail)
    monkeypatch.setattr(deletion_service.time, "sleep", lambda _x: None)

    with caplog.at_level("ERROR"):
        ok = deletion_service._delete_vectors_with_retry("col-2")

    assert ok is False
    assert "Orphan vectors remain in Qdrant" in caplog.text
