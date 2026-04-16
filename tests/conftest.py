import importlib
import os
import sys
from collections.abc import Generator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

# Ensure backend package imports resolve as `app.*`
ROOT = os.path.dirname(os.path.dirname(__file__))
BACKEND_DIR = os.path.join(ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import types

# Prevent heavy external model loading during app import.
if "app.core.rag_engine" not in sys.modules:
    rag_stub = types.ModuleType("app.core.rag_engine")

    def _stub_ingest_chunks(*args, **kwargs):
        return 1

    def _stub_search_context(*args, **kwargs):
        return ["stub context"]

    def _stub_delete_document_chunks(*args, **kwargs):
        return 0

    def _stub_delete_collection_vectors(*args, **kwargs):
        return True

    rag_stub.ingest_chunks = _stub_ingest_chunks
    rag_stub.search_context = _stub_search_context
    rag_stub.delete_document_chunks = _stub_delete_document_chunks
    rag_stub.delete_collection_vectors = _stub_delete_collection_vectors
    sys.modules["app.core.rag_engine"] = rag_stub

from app.database import get_session
from app.main import app
from app.models.collections import Collection
from app.models.documents import Document, DocumentStatus
from app.models.entities import Entity, EntityType


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """FX-01: SQLite in-memory session with fresh schema per test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    SQLModel.metadata.drop_all(engine)


@pytest.fixture
async def client(db_session: Session) -> Generator[AsyncClient, None, None]:
    """FX-02: Async test client with DB session override."""

    def _get_test_session() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_session] = _get_test_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as async_client:
        yield async_client

    app.dependency_overrides.clear()


@pytest.fixture
def mock_rag_engine(monkeypatch: pytest.MonkeyPatch) -> dict:
    """FX-03: Monkeypatch rag engine functions with deterministic mocks."""
    calls = {
        "ingest_chunks": [],
        "search_context": [],
        "delete_document_chunks": [],
        "delete_collection_vectors": [],
    }

    def _ingest_chunks(*, doc_id: str, collection_id: str, text: str) -> int:
        calls["ingest_chunks"].append(
            {"doc_id": doc_id, "collection_id": collection_id, "text": text}
        )
        return 5

    def _search_context(*, collection_id: str, query: str, top_k: int | None = None) -> list[str]:
        calls["search_context"].append(
            {"collection_id": collection_id, "query": query, "top_k": top_k}
        )
        return ["contexto 1", "contexto 2"]

    def _delete_document_chunks(collection_id: str, doc_id: str) -> int:
        calls["delete_document_chunks"].append(
            {"collection_id": collection_id, "doc_id": doc_id}
        )
        return 0

    def _delete_collection_vectors(collection_id: str) -> bool:
        calls["delete_collection_vectors"].append({"collection_id": collection_id})
        return True

    rag_engine_mod = importlib.import_module("app.core.rag_engine")
    monkeypatch.setattr(rag_engine_mod, "ingest_chunks", _ingest_chunks)
    monkeypatch.setattr(rag_engine_mod, "search_context", _search_context)
    monkeypatch.setattr(rag_engine_mod, "delete_document_chunks", _delete_document_chunks)
    monkeypatch.setattr(rag_engine_mod, "delete_collection_vectors", _delete_collection_vectors)

    # Patch service/import sites too (functions imported directly there).
    monkeypatch.setattr("app.services.documents_service.ingest_chunks", _ingest_chunks)
    monkeypatch.setattr("app.services.documents_service.delete_document_chunks", _delete_document_chunks)
    monkeypatch.setattr("app.core.rag_generate.search_context", _search_context)
    monkeypatch.setattr("app.services.collection_service.delete_collection_vectors", _delete_collection_vectors)

    return calls


@pytest.fixture
def mock_llm(monkeypatch: pytest.MonkeyPatch) -> dict:
    """FX-04: Monkeypatch get_chain with deterministic invoke output."""
    state = {"invocations": []}

    class MockChain:
        def invoke(self, payload: dict) -> str:
            state["invocations"].append(payload)
            return "Texto generado por el LLM mock"

    def _get_chain() -> MockChain:
        return MockChain()

    monkeypatch.setattr("app.core.llm_client.get_chain", _get_chain)
    monkeypatch.setattr("app.core.rag_generate.get_chain", _get_chain)
    return state


@pytest.fixture
def mock_text_extractor(monkeypatch: pytest.MonkeyPatch):
    """Mock extractor for PDF/text ingestion."""

    def _extract_text(file_bytes: bytes, content_type: str) -> str:
        return "Texto extraído simulado"

    monkeypatch.setattr("app.core.text_extractor.extract_text", _extract_text)
    monkeypatch.setattr("app.services.documents_service.extract_text", _extract_text)


@pytest.fixture
def sample_collection(db_session: Session) -> Collection:
    """FX-05: Persisted sample collection."""
    collection = Collection(name="Test World", description="A test world")
    db_session.add(collection)
    db_session.commit()
    db_session.refresh(collection)
    return collection


@pytest.fixture
def sample_document(db_session: Session, sample_collection: Collection) -> Document:
    """FX-06: Persisted sample document."""
    document = Document(
        collection_id=sample_collection.id,
        filename="test.txt",
        file_type="text/plain",
        chunk_count=5,
        status=DocumentStatus.completed,
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    return document


@pytest.fixture
def sample_entity(db_session: Session, sample_collection: Collection) -> Entity:
    """FX-07: Persisted sample entity."""
    entity = Entity(
        collection_id=sample_collection.id,
        type=EntityType.character,
        name="Aragorn",
        description="A ranger",
    )
    db_session.add(entity)
    db_session.commit()
    db_session.refresh(entity)
    return entity
