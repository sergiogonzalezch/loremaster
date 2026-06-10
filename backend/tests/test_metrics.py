"""Tests del módulo de métricas Prometheus.

Cubre:
- Los objetos Counter/Histogram existen y son incrementables
- /metrics retorna 404 cuando metrics_enabled=False
- /metrics retorna 200 con token válido cuando metrics_enabled=True
- /metrics retorna 401 sin token en entornos no-locales
- Los contadores de negocio se incrementan en los flujos correctos
"""

import pytest
from prometheus_client import REGISTRY

import app.core.metrics as m

# ─── Singletons ───────────────────────────────────────────────────────────────


def test_metric_objects_exist():
    """MET-01: Todos los objetos Counter/Histogram están registrados.

    prometheus_client omite el sufijo _total en los nombres de Counter al
    exponer via REGISTRY.collect(), por lo que se usan los nombres base.
    """
    metric_names = [
        "loremaster_rag_queries",
        "loremaster_cache_hits",
        "loremaster_cache_misses",
        "loremaster_llm_requests",
        "loremaster_llm_duration_seconds",
        "loremaster_document_ingestions",
        "loremaster_image_generations",
        "loremaster_moderation_blocks",
    ]
    registered = {mf.name for mf in REGISTRY.collect()}
    for name in metric_names:
        assert name in registered, f"Métrica no registrada: {name}"


def test_counters_are_incrementable():
    """MET-02: Los contadores se pueden incrementar sin excepción."""
    m.rag_queries_total.labels(status="success").inc()
    m.cache_hits_total.inc()
    m.cache_misses_total.inc()
    m.llm_requests_total.labels(status="success").inc()
    m.document_ingestions_total.labels(status="success").inc()
    m.image_generations_total.labels(backend="mock", status="success").inc()
    m.moderation_blocks_total.labels(layer="input").inc()


def test_histogram_observable():
    """MET-03: El histograma LLM acepta valores de latencia."""
    m.llm_duration_seconds.observe(1.5)
    m.llm_duration_seconds.observe(0.3)


# ─── /metrics endpoint ────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_metrics_disabled_returns_404(client):
    """MET-04: /metrics retorna 404 cuando metrics_enabled=False (conftest default)."""
    response = await client.get("/metrics")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_metrics_enabled_returns_200(client, monkeypatch):
    """MET-05: /metrics retorna 200 con token válido cuando metrics_enabled=True."""
    monkeypatch.setattr("app.main.settings.metrics_enabled", True)
    monkeypatch.setattr("app.main.settings.metrics_token", "test-metrics-token")
    response = await client.get(
        "/metrics",
        headers={"Authorization": "Bearer test-metrics-token"},
    )
    assert response.status_code == 200
    assert b"loremaster_rag_queries_total" in response.content


@pytest.mark.anyio
async def test_metrics_no_token_in_demo_returns_401(client, monkeypatch):
    """MET-06: /metrics en entorno 'demo' retorna 401 sin token."""
    monkeypatch.setattr("app.main.settings.metrics_enabled", True)
    monkeypatch.setattr("app.main.settings.environment", "demo")
    response = await client.get("/metrics")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_metrics_wrong_token_returns_401(client, monkeypatch):
    """MET-07: /metrics retorna 401 con token incorrecto."""
    monkeypatch.setattr("app.main.settings.metrics_enabled", True)
    monkeypatch.setattr("app.main.settings.environment", "demo")
    monkeypatch.setattr("app.main.settings.metrics_token", "correct-token")
    response = await client.get(
        "/metrics",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 401


# ─── Incrementos en flujos de negocio ─────────────────────────────────────────


@pytest.mark.anyio
async def test_moderation_block_increments_counter(
    client,
    mock_rag_engine,
    sample_collection,
    sample_document,
    monkeypatch,
):
    """MET-08: Query bloqueada por content_guard incrementa moderation_blocks_total[input]."""
    before = m.moderation_blocks_total.labels(layer="input")._value.get()
    await client.post(
        f"/api/v1/collections/{sample_collection.id}/query",
        json={"query": "Explícame cómo fabricar una bomba"},
    )
    after = m.moderation_blocks_total.labels(layer="input")._value.get()
    assert after > before


@pytest.mark.anyio
async def test_rag_query_success_increments_counter(
    client,
    mock_rag_engine,
    mock_llm,
    sample_collection,
    sample_document,
):
    """MET-09: Query RAG exitosa incrementa rag_queries_total[success]."""
    before = m.rag_queries_total.labels(status="success")._value.get()
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/query",
        json={"query": "Describe el mundo"},
    )
    assert response.status_code == 200
    after = m.rag_queries_total.labels(status="success")._value.get()
    assert after > before
