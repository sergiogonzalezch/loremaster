import importlib
import os
import sys
import types
from collections.abc import AsyncGenerator, Generator

# 1. Variables de entorno ANTES de cualquier import de app (Settings se instancia al importar)
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-not-for-prod")

# 2. Stub de app.engine.rag ANTES de importar app.main (evita carga de modelos pesados)
if "app.engine.rag" not in sys.modules:
    rag_stub = types.ModuleType("app.engine.rag")

    def _stub_ingest_chunks(*args, **kwargs):
        return 1

    def _stub_search_context(*args, **kwargs):
        return ["stub context"]

    def _stub_retrieve_context(*args, **kwargs):
        return ("stub context", 1)

    def _stub_delete_document_chunks(*args, **kwargs):
        return 0

    def _stub_delete_collection_vectors(*args, **kwargs):
        return True

    def _stub_ping_qdrant(*args, **kwargs):
        return None

    rag_stub.ingest_chunks = _stub_ingest_chunks
    rag_stub.search_context = _stub_search_context
    rag_stub.retrieve_context = _stub_retrieve_context
    rag_stub.delete_document_chunks = _stub_delete_document_chunks
    rag_stub.delete_collection_vectors = _stub_delete_collection_vectors
    rag_stub.ping_qdrant = _stub_ping_qdrant
    sys.modules["app.engine.rag"] = rag_stub

# 3. Imports de app (con env vars y stubs ya en su lugar)
import pytest
from app.core.auth.dependencies import get_current_user
from app.database import get_session
from app.main import _csrf_for_unsafe, app
from app.models.db.collection import Collection
from app.models.db.document import Document, DocumentStatus
from app.models.db.entity import Entity, EntityType
from app.models.db.entity_content import EntityContent
from app.models.db.user import User
from app.models.enums import ContentCategory, ContentStatus
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


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
async def client(db_session: Session) -> AsyncGenerator[AsyncClient, None]:
    """FX-02: Async test client with DB session override."""

    def _get_test_session():
        yield db_session

    test_user = User(
        id="test-user-id",
        username="testuser",
        hashed_password="hashed_not_for_tests",
        is_admin=False,
    )
    db_session.add(test_user)
    db_session.commit()

    def _stub_user():
        return {"sub": "test-user-id", "username": "testuser"}

    app.dependency_overrides[get_session] = _get_test_session
    app.dependency_overrides[get_current_user] = _stub_user
    app.dependency_overrides[_csrf_for_unsafe] = lambda: None

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
        "retrieve_context": [],
        "delete_document_chunks": [],
        "delete_collection_vectors": [],
    }

    def _ingest_chunks(*, doc_id: str, collection_id: str, text: str) -> int:
        calls["ingest_chunks"].append(
            {"doc_id": doc_id, "collection_id": collection_id, "text": text},
        )
        return 5

    def _search_context(
        *,
        collection_id: str,
        query: str,
        top_k: int | None = None,
        score_threshold: float | None = None,
    ) -> list[str]:
        calls["search_context"].append(
            {
                "collection_id": collection_id,
                "query": query,
                "top_k": top_k,
                "score_threshold": score_threshold,
            },
        )
        return ["contexto 1", "contexto 2"]

    def _retrieve_context(
        collection_id: str,
        query: str,
        extra_context: str = "",
    ) -> tuple[str, int]:
        calls["retrieve_context"].append(
            {
                "collection_id": collection_id,
                "query": query,
                "extra_context": extra_context,
            },
        )
        return ("contexto 1\n\n---\n\ncontexto 2", 2)

    def _delete_document_chunks(collection_id: str, doc_id: str) -> int:
        calls["delete_document_chunks"].append(
            {"collection_id": collection_id, "doc_id": doc_id},
        )
        return 0

    def _delete_collection_vectors(collection_id: str) -> bool:
        calls["delete_collection_vectors"].append({"collection_id": collection_id})
        return True

    rag_engine_mod = importlib.import_module("app.engine.rag")
    monkeypatch.setattr(rag_engine_mod, "ingest_chunks", _ingest_chunks)
    monkeypatch.setattr(rag_engine_mod, "search_context", _search_context)
    monkeypatch.setattr(rag_engine_mod, "retrieve_context", _retrieve_context)
    monkeypatch.setattr(
        rag_engine_mod, "delete_document_chunks", _delete_document_chunks,
    )
    monkeypatch.setattr(
        rag_engine_mod, "delete_collection_vectors", _delete_collection_vectors,
    )

    monkeypatch.setattr(
        "app.services.document.document_service.ingest_chunks", _ingest_chunks,
    )
    monkeypatch.setattr(
        "app.services.document.document_service.delete_document_chunks",
        _delete_document_chunks,
    )
    monkeypatch.setattr("app.engine.rag_pipeline.retrieve_context", _retrieve_context)
    monkeypatch.setattr(
        "app.services.deletion_service.delete_collection_vectors",
        _delete_collection_vectors,
    )

    return calls


@pytest.fixture
def mock_llm(monkeypatch: pytest.MonkeyPatch) -> dict:
    """FX-04: Monkeypatch chain and generation_chain with deterministic invoke output."""
    state = {"invocations": []}

    class MockChain:
        def invoke(self, payload) -> str:
            state["invocations"].append(payload)
            return "Texto generado por el LLM mock"

    monkeypatch.setattr("app.engine.rag_pipeline.chain", MockChain())
    monkeypatch.setattr("app.engine.rag_pipeline.generation_chain", MockChain())
    return state


@pytest.fixture
def mock_text_extractor(monkeypatch: pytest.MonkeyPatch):
    """Mock extractor for PDF/text ingestion."""

    def _extract_text(file_bytes: bytes, content_type: str) -> str:
        return "Texto extraído simulado"

    monkeypatch.setattr("app.engine.extractor.extract_text", _extract_text)
    monkeypatch.setattr(
        "app.services.document.document_service.extract_text", _extract_text,
    )


@pytest.fixture
def mock_image_backend(monkeypatch: pytest.MonkeyPatch):
    """FX-09: Forces image_backend='mock' regardless of .env for tests that verify mock behavior."""
    import app.services.image.image_generation_service as svc

    monkeypatch.setattr(svc.settings, "image_backend", "mock")


@pytest.fixture
def sample_collection(db_session: Session) -> Collection:
    """FX-05: Persisted sample collection."""
    collection = Collection(
        name="Test World", description="A test world", owner_id="test-user-id",
    )
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


@pytest.fixture
def sample_entity_content_confirmed(
    db_session: Session, sample_entity: Entity,
) -> "EntityContent":
    """FX-08: Persisted confirmed sample entity content for image generation."""
    content = EntityContent(
        entity_id=sample_entity.id,
        collection_id=sample_entity.collection_id,
        generated_text_id="gen-test-001",
        category=ContentCategory.backstory,
        content="En las montañas nevadas del norte nació un héroe valeroso.",
        status=ContentStatus.confirmed,
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(content)
    return content
