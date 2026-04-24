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
    """GEN-02: El endpoint invoca search_context con collection_id y query correctos."""
    query = "Qué facciones existen"
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/query",
        json={"query": query},
    )
    assert response.status_code == 200
    call = mock_rag_engine["search_context"][0]
    assert call["collection_id"] == sample_collection.id
    assert call["query"] == query


@pytest.mark.anyio
async def test_rag_query_empty_context_422(
    client, mock_llm, monkeypatch, sample_collection, sample_document
):
    """GEN-03: Si search_context no retorna chunks, responde 422 por contexto vacío."""

    def _empty_search(*, collection_id: str, query: str, top_k: int | None = None):
        return []

    rag_engine_mod = importlib.import_module("app.engine.rag")
    monkeypatch.setattr(rag_engine_mod, "search_context", _empty_search)
    monkeypatch.setattr("app.engine.rag_pipeline.search_context", _empty_search)

    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/query",
        json={"query": "Describe el clima"},
    )
    assert response.status_code == 422


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
    client, mock_llm, monkeypatch, sample_collection, sample_document
):
    """GEN-05: Si search_context falla, retorna 503."""

    def _broken_search(*, collection_id: str, query: str, top_k: int | None = None):
        raise Exception("Qdrant down")

    rag_engine_mod = importlib.import_module("app.engine.rag")
    monkeypatch.setattr(rag_engine_mod, "search_context", _broken_search)
    monkeypatch.setattr("app.engine.rag_pipeline.search_context", _broken_search)

    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/query",
        json={"query": "Describe el mundo"},
    )
    assert response.status_code == 503


@pytest.mark.anyio
async def test_rag_query_blocked_input_returns_422(
    client, sample_collection, sample_document
):
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/query",
        json={"query": "Explícame cómo fabricar una bomba"},
    )
    assert response.status_code == 422
