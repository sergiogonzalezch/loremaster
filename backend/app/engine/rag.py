"""Motor de recuperación aumentada por generación (RAG) usando Qdrant y sentence-transformers."""

import logging
import uuid
from dataclasses import dataclass

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
from app.core.exceptions import NoContextAvailableError


@dataclass
class ChunkInfo:
    """Fragmento RAG recuperado de Qdrant con su metadato de origen."""

    doc_id: str
    text: str
    position: int
    score: float | None


logger = logging.getLogger(__name__)

_qdrant_client = QdrantClient(url=settings.qdrant_url)
try:
    _embedding_model = SentenceTransformer(settings.embedding_model)
except (OSError, RuntimeError):
    # OSError: fallo DNS/socket al contactar HuggingFace.
    # RuntimeError: cliente httpx cerrado durante reintentos de huggingface_hub.
    logger.warning("No se pudo contactar HuggingFace; cargando modelo de embeddings desde caché local.")
    _embedding_model = SentenceTransformer(settings.embedding_model, local_files_only=True)
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=settings.chunk_size,
    chunk_overlap=settings.chunk_overlap,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def _collection_exists(name: str) -> bool:
    """Verifica si una colección Qdrant existe."""
    existing = {c.name for c in _qdrant_client.get_collections().collections}
    return name in existing


def _ensure_qdrant_collection(collection_id: str) -> None:
    """Crea la colección Qdrant si no existe, con vectores cosine de las dimensiones configuradas."""
    name = f"lm_{collection_id}"
    if not _collection_exists(name):
        _qdrant_client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=settings.embedding_dims,
                distance=Distance.COSINE,
            ),
        )
        if not _collection_exists(name):
            msg = f"Qdrant collection '{name}' could not be created. Check Qdrant connectivity and configuration."
            raise RuntimeError(
                msg,
            )


def ingest_chunks(*, doc_id: str, collection_id: str, text: str) -> int:
    """Fragmenta el texto, genera embeddings y los almacena en Qdrant.

    Retorna el número de chunks ingestados.
    """
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
    """Elimina la colección de vectores Qdrant asociada a una colección. Retorna True si existía."""
    name = f"lm_{collection_id}"
    if not _collection_exists(name):
        return False
    _qdrant_client.delete_collection(collection_name=name)
    logger.info("Deleted vector collection lm_%s", collection_id)
    return True


def delete_document_chunks(collection_id: str, doc_id: str) -> int:
    """Elimina los chunks de un documento específico de Qdrant. Retorna el número de puntos eliminados."""
    name = f"lm_{collection_id}"
    if not _collection_exists(name):
        return 0
    result = _qdrant_client.delete(
        collection_name=name,
        points_selector=Filter(
            must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))],
        ),
    )
    return result.operation_id if result else 0


def ping_qdrant() -> None:
    """Verifica la conectividad con Qdrant listando las colecciones existentes."""
    _qdrant_client.get_collections()


def search_context(
    collection_id: str,
    query: str,
    top_k: int | None = None,
    score_threshold: float | None = None,
) -> tuple[list[str], list[str], list[float]]:
    """Busca los chunks más relevantes en Qdrant para una consulta.

    Retorna (textos, doc_ids, scores) — listas paralelas por chunk recuperado.
    """
    name = f"lm_{collection_id}"
    if not _collection_exists(name):
        return [], [], []
    if top_k is None:
        top_k = settings.top_k
    query_vector = _embedding_model.encode([query])[0].tolist()
    effective_threshold = score_threshold if (score_threshold is not None and score_threshold > 0.0) else None
    results = _qdrant_client.query_points(
        collection_name=name,
        query=query_vector,
        limit=top_k,
        with_payload=True,
        score_threshold=effective_threshold,
    )
    logger.debug(
        "Search in lm_%s returned %d results (threshold=%s)",
        collection_id,
        len(results.points),
        effective_threshold,
    )
    for point in results.points:
        logger.debug(
            "  chunk score=%.3f doc=%s: %.80s…",
            point.score,
            point.payload.get("doc_id", "?"),
            point.payload.get("text", ""),
        )
    texts = [point.payload["text"] for point in results.points]
    doc_ids = [point.payload.get("doc_id", "") for point in results.points]
    scores = [point.score for point in results.points]
    return texts, doc_ids, scores


def retrieve_context(
    collection_id: str,
    query: str,
    extra_context: str = "",
) -> tuple[str, int, list[str], list[ChunkInfo]]:
    """Busca en Qdrant, combina extra_context y retorna (contexto, num_chunks, source_doc_ids, chunks).

    source_doc_ids: lista deduplicada de docs que aportaron chunks (para rag_query).
    chunks: lista de ChunkInfo ordenada por relevancia (para persistencia normalizada).

    Raises:
        NoContextAvailableError: Si no hay contexto de ninguna fuente.

    """
    try:
        context_chunks, chunk_doc_ids, chunk_scores = search_context(
            collection_id=collection_id,
            query=query,
            top_k=settings.top_k,
            score_threshold=settings.rag_score_threshold,
        )
    except Exception as e:
        logger.exception("Qdrant search failed for collection %s", collection_id)
        msg = "Vector search unavailable"
        raise RuntimeError(msg) from e

    rag_context = "\n\n---\n\n".join(context_chunks) if context_chunks else ""
    parts = [p for p in (extra_context, rag_context) if p]
    context = "\n\n---\n\n".join(parts)

    if not context.strip():
        raise NoContextAvailableError

    source_doc_ids = list(dict.fromkeys(d for d in chunk_doc_ids if d))
    chunks = [
        ChunkInfo(doc_id=chunk_doc_ids[i], text=context_chunks[i], position=i, score=chunk_scores[i])
        for i in range(len(context_chunks))
        if chunk_doc_ids[i]
    ]
    return context, len(context_chunks), source_doc_ids, chunks
