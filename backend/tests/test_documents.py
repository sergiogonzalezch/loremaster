import importlib

import pytest
from sqlmodel import select

from app.models.collections import Collection
from app.models.documents import Document, DocumentStatus


@pytest.mark.anyio
async def test_ingest_txt(client, db_session, mock_rag_engine, sample_collection):
    """DOC-01: Ingesta TXT retorna 202; background task completa con chunk_count > 0."""
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/documents",
        files={"file": ("lore.txt", b"contenido de lore", "text/plain")},
    )
    assert response.status_code == 202
    doc_id = response.json()["id"]
    # Background task ran before httpx returned the response; verify final state via DB.
    doc = db_session.exec(select(Document).where(Document.id == doc_id)).first()
    assert doc.chunk_count > 0
    assert doc.status == DocumentStatus.completed


@pytest.mark.anyio
async def test_ingest_pdf(
    client, mock_rag_engine, mock_text_extractor, sample_collection
):
    """DOC-02: Ingesta PDF retorna 202 con extractor mock."""
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/documents",
        files={"file": ("lore.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert response.status_code == 202
    assert response.json()["filename"] == "lore.pdf"


@pytest.mark.anyio
async def test_list_documents(client, mock_rag_engine, sample_collection):
    """DOC-03: Listar documentos retorna count correcto."""
    for name in ("a.txt", "b.txt"):
        assert (
            await client.post(
                f"/api/v1/collections/{sample_collection.id}/documents",
                files={"file": (name, b"txt", "text/plain")},
            )
        ).status_code == 202

    response = await client.get(f"/api/v1/collections/{sample_collection.id}/documents")
    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 2


@pytest.mark.anyio
async def test_delete_document(
    client, mock_rag_engine, sample_collection, sample_document
):
    """DOC-04: Eliminar documento retorna 204, GET→404 y limpia chunks en Qdrant."""
    response = await client.delete(
        f"/api/v1/collections/{sample_collection.id}/documents/{sample_document.id}"
    )
    assert response.status_code == 204

    get_response = await client.get(
        f"/api/v1/collections/{sample_collection.id}/documents/{sample_document.id}"
    )
    assert get_response.status_code == 404
    assert len(mock_rag_engine["delete_document_chunks"]) == 1


@pytest.mark.anyio
async def test_ingest_qdrant_failure_marks_failed(
    client, monkeypatch, db_session, sample_collection
):
    """DOC-05: Falla en ingest_chunks retorna 202 y marca el documento como failed."""

    def _raise_ingest(*args, **kwargs):
        raise Exception("Qdrant down")

    rag_engine_mod = importlib.import_module("app.engine.rag")
    monkeypatch.setattr(rag_engine_mod, "ingest_chunks", _raise_ingest)
    monkeypatch.setattr("app.services.documents_service.ingest_chunks", _raise_ingest)

    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/documents",
        files={"file": ("broken.txt", b"contenido", "text/plain")},
    )
    assert response.status_code == 202
    # Background task ran and failed; verify final status via DB.
    doc = db_session.exec(
        select(Document).where(Document.filename == "broken.txt")
    ).first()
    assert doc.status == DocumentStatus.failed


@pytest.mark.anyio
async def test_ingest_unsupported_type_400(client, sample_collection):
    """DOC-06: Ingesta con tipo no soportado retorna 400."""
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/documents",
        files={"file": ("lore.doc", b"doc content", "application/msword")},
    )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_ingest_oversized_file_400(client, sample_collection):
    """DOC-07: Ingesta de archivo >50MB retorna 400."""
    oversized = b"a" * (50 * 1024 * 1024 + 1)
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/documents",
        files={"file": ("big.txt", oversized, "text/plain")},
    )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_get_doc_wrong_collection_404(client, db_session, sample_document):
    """DOC-08: Documento solicitado desde colección incorrecta retorna 404."""
    another = Collection(name="Other", description="Other col")
    db_session.add(another)
    db_session.commit()
    db_session.refresh(another)

    response = await client.get(
        f"/api/v1/collections/{another.id}/documents/{sample_document.id}"
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_filter_documents_by_filename(client, mock_rag_engine, sample_collection):
    """DOC-09: Filtrar documentos por nombre de archivo retorna solo los que coinciden."""
    for name in ("alpha.txt", "beta.txt", "alpha_v2.txt"):
        await client.post(
            f"/api/v1/collections/{sample_collection.id}/documents",
            files={"file": (name, b"contenido", "text/plain")},
        )

    response = await client.get(
        f"/api/v1/collections/{sample_collection.id}/documents?filename=alpha"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 2
    filenames = [d["filename"] for d in body["data"]]
    assert "alpha.txt" in filenames
    assert "alpha_v2.txt" in filenames
    assert "beta.txt" not in filenames


@pytest.mark.anyio
async def test_filter_documents_by_status(client, mock_rag_engine, sample_collection):
    """DOC-10: Filtrar documentos por status completed retorna solo los completados."""
    await client.post(
        f"/api/v1/collections/{sample_collection.id}/documents",
        files={"file": ("ok.txt", b"contenido", "text/plain")},
    )

    response = await client.get(
        f"/api/v1/collections/{sample_collection.id}/documents?status=completed"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["status"] == "completed"


@pytest.mark.anyio
async def test_filter_documents_by_file_type(
    client, mock_rag_engine, sample_collection
):
    """DOC-11: Filtrar documentos por file_type retorna solo los de ese tipo."""
    await client.post(
        f"/api/v1/collections/{sample_collection.id}/documents",
        files={"file": ("plain.txt", b"txt content", "text/plain")},
    )

    response = await client.get(
        f"/api/v1/collections/{sample_collection.id}/documents?file_type=text%2Fplain"
    )
    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 1


@pytest.mark.anyio
async def test_filter_documents_created_after_future(
    client, mock_rag_engine, sample_collection
):
    """DOC-12: created_after en el futuro retorna lista vacía."""
    await client.post(
        f"/api/v1/collections/{sample_collection.id}/documents",
        files={"file": ("future.txt", b"content", "text/plain")},
    )

    response = await client.get(
        f"/api/v1/collections/{sample_collection.id}/documents?created_after=2099-01-01T00:00:00"
    )
    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 0


@pytest.mark.anyio
async def test_ingest_blocked_document_returns_422(client, sample_collection):
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/documents",
        files={"file": ("bad.txt", b"contenido porno xxx", "text/plain")},
    )
    assert response.status_code == 422
