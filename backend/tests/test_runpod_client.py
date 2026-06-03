"""Tests unitarios del cliente RunPod (sin GPU ni red real).

Cubren la lógica pura de extracción/validación añadida en el hardening:
- decodificación base64 y tope de tamaño,
- rechazo de URLs no-https (defensa SSRF),
- polling de estado (COMPLETED / FAILED).
"""

import base64

import pytest

from app.engine import runpod_client
from app.engine.runpod_client import RunPodClient


def _client() -> RunPodClient:
    return RunPodClient(api_key="k", endpoint_id="e")


def test_extract_base64_ok():
    """RP-01: decodifica imágenes base64 del output."""
    raw = b"hello-image-bytes"
    job = {"output": {"images": [{"type": "base64", "data": base64.b64encode(raw).decode()}]}}
    assert _client().extract_image_bytes(job) == [raw]


def test_extract_no_images_raises():
    """RP-02: job completado sin imágenes → RuntimeError."""
    with pytest.raises(RuntimeError):
        _client().extract_image_bytes({"output": {"images": []}})


def test_extract_oversized_base64_raises(monkeypatch):
    """RP-03: imagen base64 que excede el tope → RuntimeError."""
    monkeypatch.setattr(runpod_client, "_MAX_IMAGE_BYTES", 4)
    raw = b"too-large-payload"
    job = {"output": {"images": [{"type": "base64", "data": base64.b64encode(raw).decode()}]}}
    with pytest.raises(RuntimeError, match="tamaño máximo"):
        _client().extract_image_bytes(job)


def test_download_non_https_raises():
    """RP-04: URL de imagen no-https (p.ej. metadata interna) → RuntimeError."""
    with pytest.raises(RuntimeError, match="no es https"):
        _client()._download_image_url("http://169.254.169.254/latest/meta-data/")


def test_wait_for_completion_returns_on_completed(monkeypatch):
    """RP-05: wait_for_completion devuelve el resultado cuando status=COMPLETED."""
    client = _client()
    monkeypatch.setattr(client, "get_status", lambda _jid: {"status": "COMPLETED", "output": {}})
    assert client.wait_for_completion("job1")["status"] == "COMPLETED"


def test_wait_for_completion_raises_on_failed(monkeypatch):
    """RP-06: wait_for_completion lanza RuntimeError si el job termina en FAILED."""
    client = _client()
    monkeypatch.setattr(client, "get_status", lambda _jid: {"status": "FAILED", "error": "boom"})
    with pytest.raises(RuntimeError, match="FAILED"):
        client.wait_for_completion("job1")
