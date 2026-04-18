import importlib

import pytest


@pytest.mark.anyio
async def test_generate_text(
    client, mock_rag_engine, mock_llm, sample_collection, sample_document
):
    """GEN-01: Generación de texto retorna answer, query y sources_count."""
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/generate/text",
        json={"query": "Describe el mundo"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Texto generado por el LLM mock"
    assert data["query"] == "Describe el mundo"
    assert isinstance(data["sources_count"], int)


@pytest.mark.anyio
async def test_generate_uses_rag_context(
    client, mock_rag_engine, mock_llm, sample_collection, sample_document
):
    """GEN-02: generate invoca search_context con collection_id y query correctos."""
    query = "Qué facciones existen"
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/generate/text",
        json={"query": query},
    )
    assert response.status_code == 200
    call = mock_rag_engine["search_context"][0]
    assert call["collection_id"] == sample_collection.id
    assert call["query"] == query


@pytest.mark.anyio
async def test_generate_empty_rag_results_422(
    client, mock_llm, monkeypatch, sample_collection, sample_document
):
    """GEN-03: Si search_context no retorna chunks, responde 422 por contexto vacío."""

    def _empty_search(*, collection_id: str, query: str, top_k: int | None = None):
        return []

    rag_engine_mod = importlib.import_module("app.core.rag_engine")
    monkeypatch.setattr(rag_engine_mod, "search_context", _empty_search)
    monkeypatch.setattr("app.core.rag_generate.search_context", _empty_search)

    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/generate/text",
        json={"query": "Describe el clima"},
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_generate_llm_unavailable_503(
    client, mock_rag_engine, monkeypatch, sample_collection, sample_document
):
    """GEN-04: Si chain.invoke falla, retorna 503."""

    class BrokenChain:
        def invoke(self, payload: dict):
            raise Exception("LLM down")

    monkeypatch.setattr("app.core.rag_generate.chain", BrokenChain())

    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/generate/text",
        json={"query": "Describe el mundo"},
    )
    assert response.status_code == 503


@pytest.mark.anyio
async def test_generate_qdrant_unavailable_503(
    client, mock_llm, monkeypatch, sample_collection, sample_document
):
    """GEN-05: Si search_context falla, retorna 503."""

    def _broken_search(*, collection_id: str, query: str, top_k: int | None = None):
        raise Exception("Qdrant down")

    rag_engine_mod = importlib.import_module("app.core.rag_engine")
    monkeypatch.setattr(rag_engine_mod, "search_context", _broken_search)
    monkeypatch.setattr("app.core.rag_generate.search_context", _broken_search)

    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/generate/text",
        json={"query": "Describe el mundo"},
    )
    assert response.status_code == 503