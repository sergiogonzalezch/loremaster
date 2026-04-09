from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import uuid
from config import settings

EMBEDDING_DIMS = 384  # Adjust based on the model used

_qdrant_client = QdrantClient(":memory:")
_embedding_model = settings.embedding_model
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=settings.chunk_size,
    chunk_overlap=settings.chunk_overlap,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def _ensure_qdrant_collection(collection_id: str):
    name = f"lm_{collection_id}"
    exiting_collections = {c.name for c in _qdrant_client.get_collections().collections}
    if name not in exiting_collections:
        _qdrant_client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=EMBEDDING_DIMS, distance=Distance.COSINE),
        )


def ingest_chunks(doc_id: str, collection_id: str, text: str):
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
    _qdrant_client.upsert(
        collection_name=f"lm_{collection_id}",
        points=points,
    )

    return len(chunks)

def search_context(collection_id:str, query:str, top_k:int=4)-> list[str]:
    name = f"lm_{collection_id}"
    existing_collections = {c.name for c in _qdrant_client.get_collections().collections}
    if name not in existing_collections:
        return []
    
    query_vector = _embedding_model.encode([query])[0].tolist()

    results = _qdrant_client.search(
        collection_name=name,
        query_vector=query_vector,
        limit=top_k,
        with_payload=True
    )

    return [hit.payload["text"] for hit in results]