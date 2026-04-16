import importlib
import uuid

import pytest
from sqlmodel import select

from app.models.collections import Collection
from app.models.documents import Document, DocumentStatus


@pytest.mark.anyio
async def test_ingest_txt(client, mock_rag_engine, sample_collection):
    """DOC-01: Ingesta TXT retorna 201 y chunk_count > 0."""
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/documents",
        files={"file": ("lore.txt", b"contenido de lore", "text/plain")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["chunk_count"] > 0


@pytest.mark.anyio
async def test_ingest_pdf(client, mock_rag_engine, mock_text_extractor, sample_collection):
    """DOC-02: Ingesta PDF retorna 201 con extractor mock."""
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/documents",
        files={"file": ("lore.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert response.status_code == 201
    assert response.json()["filename"] == "lore.pdf"


@pytest.mark.anyio
async def test_list_documents(client, mock_rag_engine, sample_collection):
    """DOC-03: Listar documentos retorna count=2."""
    for name in ("a.txt", "b.txt"):
        resp = await client.post(
            f"/api/v1/collections/{sample_collection.id}/documents",
            files={"file": (name, b"txt", "text/plain")},
        )
        assert resp.status_code == 201

    response = await client.get(f"/api/v1/collections/{sample_collection.id}/documents")
    assert response.status_code == 200
    assert response.json()["count"] == 2


@pytest.mark.anyio
async def test_get_document_by_id(client, sample_collection, sample_document):
    """DOC-04: Obtener documento por id retorna 200."""
    response = await client.get(
        f"/api/v1/collections/{sample_collection.id}/documents/{sample_document.id}"
    )
    assert response.status_code == 200
    assert response.json()["filename"] == "test.txt"


@pytest.mark.anyio
async def test_delete_document(client, mock_rag_engine, sample_collection, sample_document):
    """DOC-05: Eliminar documento retorna 200, GET 404 y borra chunks mock."""
    response = await client.delete(
        f"/api/v1/collections/{sample_collection.id}/documents/{sample_document.id}"
    )
    assert response.status_code == 200

    get_response = await client.get(
        f"/api/v1/collections/{sample_collection.id}/documents/{sample_document.id}"
    )
    assert get_response.status_code == 404
    assert len(mock_rag_engine["delete_document_chunks"]) == 1


@pytest.mark.anyio
async def test_deleted_doc_not_in_list(client, sample_collection, sample_document):
    """DOC-06: Documento eliminado no aparece en listado."""
    await client.delete(f"/api/v1/collections/{sample_collection.id}/documents/{sample_document.id}")

    response = await client.get(f"/api/v1/collections/{sample_collection.id}/documents")
    assert response.status_code == 200
    assert response.json()["count"] == 0


@pytest.mark.anyio
async def test_ingest_qdrant_failure_marks_failed(client, monkeypatch, db_session, sample_collection):
    """DOC-07: Falla en ingest_chunks retorna 502 y status failed en DB."""

    def _raise_ingest(*args, **kwargs):
        raise Exception("Qdrant down")

    rag_engine_mod = importlib.import_module("app.core.rag_engine")
    monkeypatch.setattr(rag_engine_mod, "ingest_chunks", _raise_ingest)
    monkeypatch.setattr("app.services.documents_service.ingest_chunks", _raise_ingest)

    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/documents",
        files={"file": ("broken.txt", b"contenido", "text/plain")},
    )
    assert response.status_code == 502

    doc = db_session.exec(
        select(Document).where(Document.filename == "broken.txt")
    ).first()
    assert doc is not None
    assert doc.status == DocumentStatus.failed


@pytest.mark.anyio
async def test_ingest_unsupported_type_400(client, sample_collection):
    """DOC-08: Ingesta con tipo no soportado retorna 400."""
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/documents",
        files={"file": ("lore.doc", b"doc content", "application/msword")},
    )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_ingest_no_filename_400(client, sample_collection):
    """DOC-09: Ingesta sin filename retorna 400."""
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/documents",
        files={"file": ("", b"sin nombre", "text/plain")},
    )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_ingest_oversized_file_400(client, sample_collection):
    """DOC-10: Ingesta de archivo >50MB retorna 400."""
    oversized = b"a" * (50 * 1024 * 1024 + 1)
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}/documents",
        files={"file": ("big.txt", oversized, "text/plain")},
    )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_ingest_nonexistent_collection_404(client, mock_rag_engine):
    """DOC-11: Ingesta en colección inexistente retorna 404."""
    response = await client.post(
        f"/api/v1/collections/{uuid.uuid4()}/documents",
        files={"file": ("lore.txt", b"contenido", "text/plain")},
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_get_doc_wrong_collection_404(client, db_session, sample_document):
    """DOC-12: Documento de otra colección retorna 404."""
    another = Collection(name="Other", description="Other col")
    db_session.add(another)
    db_session.commit()
    db_session.refresh(another)

    response = await client.get(
        f"/api/v1/collections/{another.id}/documents/{sample_document.id}"
    )
    assert response.status_code == 404
