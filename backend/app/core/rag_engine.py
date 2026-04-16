import logging
import uuid

from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)
from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = logging.getLogger(__name__)

_qdrant_client = QdrantClient(url=settings.qdrant_url)
_embedding_model = SentenceTransformer(settings.embedding_model)
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=settings.chunk_size,
    chunk_overlap=settings.chunk_overlap,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def _collection_exists(name: str) -> bool:
    existing = {c.name for c in _qdrant_client.get_collections().collections}
    return name in existing


def _ensure_qdrant_collection(collection_id: str) -> None:
    name = f"lm_{collection_id}"
    if not _collection_exists(name):
        _qdrant_client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=settings.embedding_dims, distance=Distance.COSINE
            ),
        )


def ingest_chunks(*, doc_id: str, collection_id: str, text: str) -> int:
    chunks = _splitter.split_text(text)
    if not chunks:
        return 0
    _ensure_qdrant_collection(collection_id)
    vectors = _embedding_model.encode(chunks, batch_size=32, show_progress_bar=False)
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vectors[i].tolist(),
            payload={
                "doc_id": doc_id,
                "collection_id": collection_id,
                "chunk_idx": i,
                "text": chunks[i],
            },
        )
        for i in range(len(chunks))
    ]
    _qdrant_client.upsert(collection_name=f"lm_{collection_id}", points=points)
    logger.info(
        "Ingested %d chunks for doc %s into collection %s",
        len(chunks),
        doc_id,
        collection_id,
    )
    return len(chunks)


def delete_collection_vectors(collection_id: str) -> bool:
    name = f"lm_{collection_id}"
    if not _collection_exists(name):
        return False
    _qdrant_client.delete_collection(collection_name=name)
    logger.info("Deleted vector collection lm_%s", collection_id)
    return True


def delete_document_chunks(collection_id: str, doc_id: str) -> int:
    name = f"lm_{collection_id}"
    if not _collection_exists(name):
        return 0
    result = _qdrant_client.delete(
        collection_name=name,
        points_selector=Filter(
            must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
        ),
    )
    return result.operation_id if result else 0


def ping_qdrant() -> None:
    _qdrant_client.get_collections()


def search_context(
    collection_id: str, query: str, top_k: int | None = None
) -> list[str]:
    name = f"lm_{collection_id}"
    if not _collection_exists(name):
        return []
    if top_k is None:
        top_k = settings.top_k
    query_vector = _embedding_model.encode([query])[0].tolist()
    results = _qdrant_client.query_points(
        collection_name=name, query=query_vector, limit=top_k, with_payload=True
    )
    logger.debug(
        "Search in lm_%s returned %d results", collection_id, len(results.points)
    )
    return [point.payload["text"] for point in results.points]
