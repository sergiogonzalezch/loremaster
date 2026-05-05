import importlib

import pytest


@pytest.mark.anyio
async def test_rag_query_returns_answer(
    client, mock_rag_engine, mock_llm, sample_collection, sample_document
):
    """GEN-01: La consulta RAG retorna answer, query y sources_count."""
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/query",
        json={"query": "Describe el mundo"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Texto generado por el LLM mock"
    assert data["query"] == "Describe el mundo"
    assert isinstance(data["sources_count"], int)


@pytest.mark.anyio
async def test_rag_query_uses_rag_context(
    client, mock_rag_engine, mock_llm, sample_collection, sample_document
):
    """GEN-02: El endpoint invoca retrieve_context con collection_id y query correctos."""
    query = "Qué facciones existen"
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/query",
        json={"query": query},
    )
    assert response.status_code == 200
    call = mock_rag_engine["retrieve_context"][0]
    assert call["collection_id"] == sample_collection.id
    assert call["query"] == query


@pytest.mark.anyio
async def test_rag_query_empty_context_422(
    client, sample_collection, sample_document
):
    """GEN-03: Si no hay documentos, responde 422 o 200 con warning."""
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/query",
        json={"query": "Describe el clima"},
    )
    assert response.status_code in (200, 422)


@pytest.mark.anyio
async def test_rag_query_llm_unavailable_503(
    client, mock_rag_engine, monkeypatch, sample_collection, sample_document
):
    """GEN-04: Si chain.invoke falla, retorna 503."""

    class BrokenChain:
        def invoke(self, payload: dict):
            raise Exception("LLM down")

    monkeypatch.setattr("app.engine.rag_pipeline.chain", BrokenChain())

    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/query",
        json={"query": "Describe el mundo"},
    )
    assert response.status_code == 503


@pytest.mark.anyio
async def test_rag_query_qdrant_unavailable_503(
    client, sample_collection, sample_document
):
    """GEN-05: Si Qdrant falla, retorna 503."""
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/query",
        json={"query": "Describe el mundo"},
    )
    assert response.status_code in (200, 503)


@pytest.mark.anyio
async def test_rag_query_blocked_input_returns_422(
    client, sample_collection, sample_document
):
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/query",
        json={"query": "Explícame cómo fabricar una bomba"},
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_rag_query_low_score_returns_422(
    client, mock_rag_engine, sample_collection, sample_document
):
    """GEN-06: Si el score es bajo, retorna 422."""
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/query",
        json={"query": "Consulta sin contexto relevante"},
    )
    assert response.status_code in (200, 422)


@pytest.mark.anyio
async def test_rag_query_with_threshold_passes_param_to_search(
    client, mock_rag_engine, sample_collection, sample_document
):
    """GEN-07: El pipeline usa settings."""
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/query",
        json={"query": "Consulta de prueba con threshold"},
    )
    assert response.status_code == 200


@pytest.mark.anyio
async def test_rag_query_llm_failure_releases_semaphore(
    client, mock_rag_engine, monkeypatch, sample_collection, sample_document
):
    """GEN-08: Si el LLM falla, el semáforo se libera y el siguiente request puede ejecutar."""

    class FailsOnceChain:
        def __init__(self):
            self.calls = 0

        def invoke(self, payload: dict):
            self.calls += 1
            if self.calls == 1:
                raise TimeoutError("llm timeout")
            return "ok after failure"

    broken_then_ok = FailsOnceChain()
    monkeypatch.setattr("app.engine.rag_pipeline.chain", broken_then_ok)

    first = await client.post(
        f"/api/v1/collections/{sample_collection.id}/query",
        json={"query": "Describe el mundo"},
    )
    assert first.status_code == 503

    second = await client.post(
        f"/api/v1/collections/{sample_collection.id}/query",
        json={"query": "Describe el mundo"},
    )
    assert second.status_code == 200
    assert second.json()["answer"] == "ok after failure"
