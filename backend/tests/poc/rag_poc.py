#!/usr/bin/env python3
"""
POC: Pipeline RAG con SQLite + Qdrant
======================================
Valida el flujo completo antes de integrarlo en los endpoints reales.

Flujo:
  1. Crea las tablas en SQLite desde los modelos SQLModel
  2. Registra una Collection y un Document en SQLite
  3. Carga un archivo (PDF o TXT)
  4. Chunking con RecursiveCharacterTextSplitter
  5. Embeddings con paraphrase-multilingual-MiniLM-L12-v2
  6. Almacena los chunks en Qdrant (colección por collection_id)
  7. Query RAG: embed -> búsqueda Qdrant -> prompt -> Ollama -> respuesta

Uso (desde backend/):
    python tests/poc/rag_poc.py ingest tests/poc/sample.txt
    python tests/poc/rag_poc.py query "¿Quién fundó Valdoria?" --collection-id <id>
    python tests/poc/rag_poc.py demo   tests/poc/sample.txt
    python tests/poc/rag_poc.py list
"""

import argparse
import io
import json
import sys
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Añadir backend/ al path para importar los módulos del proyecto
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer
from sqlmodel import Session, SQLModel, create_engine, select

# ── Importar modelos del proyecto (tablas reales) ─────────────────────────────
from app.models.collections import Collection
from app.models.documents import Document
from app.models.entities import Entity  # noqa: F401 — necesario para create_all

# ── Config ────────────────────────────────────────────────────────────────────

SQLITE_URL = "sqlite:///./poc_database.db"
QDRANT_URL = "http://localhost:6333"
QDRANT_API_KEY = "test_key_dev"
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:latest"

EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIMS = 384
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
TOP_K = 4

SUPPORTED_EXTENSIONS = {".txt", ".pdf"}

# ── DB Setup ──────────────────────────────────────────────────────────────────

engine = create_engine(SQLITE_URL, echo=False)


def init_db() -> None:
    """Crea todas las tablas definidas en los modelos SQLModel."""
    SQLModel.metadata.create_all(engine)
    print("  [sqlite] Tablas inicializadas desde modelos SQLModel.")


# ── Qdrant helpers ────────────────────────────────────────────────────────────

def get_qdrant() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


def qdrant_collection_name(collection_id: str) -> str:
    return f"loremaster_{collection_id}"


def ensure_qdrant_collection(client: QdrantClient, collection_id: str) -> None:
    name = qdrant_collection_name(collection_id)
    existing = {c.name for c in client.get_collections().collections}
    if name not in existing:
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=EMBEDDING_DIMS, distance=Distance.COSINE),
        )
        print(f"  [qdrant] Colección '{name}' creada.")
    else:
        print(f"  [qdrant] Colección '{name}' ya existe.")


# ── File helpers ──────────────────────────────────────────────────────────────

def load_file(path: Path) -> tuple[str, str]:
    """Devuelve (texto, mime_type). Usa pypdf para PDFs."""
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        print(f"[error] Tipo no soportado: {path.suffix}. Usa .txt o .pdf")
        sys.exit(1)

    if path.suffix.lower() == ".pdf":
        reader = PdfReader(io.BytesIO(path.read_bytes()))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text, "application/pdf"

    return path.read_text(encoding="utf-8", errors="replace"), "text/plain"


# ── Ingestión ─────────────────────────────────────────────────────────────────

def ingest(file_path: str, collection_name: str = "poc-collection") -> dict:
    path = Path(file_path)
    if not path.exists():
        print(f"[error] Archivo no encontrado: {file_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"INGESTIÓN: {path.name}")
    print(f"{'='*60}")

    init_db()

    with Session(engine) as session:
        # Verificar unicidad de nombre
        existing = session.exec(
            select(Collection).where(Collection.name == collection_name)
        ).first()
        if existing:
            print(f"  [sqlite] Colección '{collection_name}' ya existe -> reutilizando (id={existing.id[:8]}...)")
            collection = existing
        else:
            collection = Collection(name=collection_name)
            session.add(collection)
            session.commit()
            session.refresh(collection)
            print(f"  [sqlite] Colección creada: '{collection_name}' (id={collection.id[:8]}...)")

        # Cargar y chunkear el archivo
        raw_text, file_type = load_file(path)
        print(f"  [archivo] {path.name} — {len(raw_text):,} chars ({file_type})")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = splitter.split_text(raw_text)
        print(f"  [chunking] {len(chunks)} chunks (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")

        if not chunks:
            print("[error] No se pudo extraer texto del archivo.")
            sys.exit(1)

        # Generar embeddings
        print(f"  [embeddings] Cargando '{EMBEDDING_MODEL}'...")
        model = SentenceTransformer(EMBEDDING_MODEL)
        vectors = model.encode(chunks, show_progress_bar=True, batch_size=32)
        print(f"  [embeddings] Shape: {vectors.shape}")

        # Almacenar en Qdrant
        qdrant = get_qdrant()
        ensure_qdrant_collection(qdrant, collection.id)

        doc_id = str(uuid.uuid4())
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vectors[i].tolist(),
                payload={
                    "doc_id": doc_id,
                    "collection_id": collection.id,
                    "chunk_index": i,
                    "text": chunks[i],
                    "filename": path.name,
                },
            )
            for i in range(len(chunks))
        ]
        qdrant.upsert(
            collection_name=qdrant_collection_name(collection.id),
            points=points,
        )
        print(f"  [qdrant] {len(points)} chunks almacenados.")

        # Registrar documento en SQLite
        document = Document(
            id=doc_id,
            collection_id=collection.id,
            filename=path.name,
            file_type=file_type,
            chunk_count=len(chunks),
        )
        session.add(document)
        session.commit()
        session.refresh(document)
        print(f"  [sqlite] Documento registrado (id={document.id[:8]}...)")

    result = {
        "collection_id": collection.id,
        "collection_name": collection.name,
        "doc_id": doc_id,
        "filename": path.name,
        "chunk_count": len(chunks),
    }
    print(f"\n  [ok] Ingestión completa -> collection_id={collection.id}")
    return result


# ── Query RAG ─────────────────────────────────────────────────────────────────

def query_rag(question: str, collection_id: str) -> str:
    print(f"\n{'='*60}")
    print(f"QUERY RAG")
    print(f"{'='*60}")
    print(f"  Pregunta  : {question}")
    print(f"  Colección : {collection_id[:8]}...")

    # Verificar que la colección existe en SQLite
    with Session(engine) as session:
        collection = session.get(Collection, collection_id)
        if not collection:
            print(f"[error] Colección {collection_id} no encontrada en SQLite.")
            return ""
        docs = session.exec(
            select(Document).where(Document.collection_id == collection_id)
        ).all()
        print(f"  [sqlite] Colección: '{collection.name}' — {len(docs)} documento(s)")

    # Embed de la query
    model = SentenceTransformer(EMBEDDING_MODEL)
    query_vector = model.encode(question).tolist()

    # Búsqueda semántica en Qdrant
    qdrant = get_qdrant()
    results = qdrant.search(
        collection_name=qdrant_collection_name(collection_id),
        query_vector=query_vector,
        limit=TOP_K,
        with_payload=True,
    )

    if not results:
        print("  [qdrant] No se encontraron chunks relevantes.")
        return "No se encontró información relevante."

    print(f"\n  [qdrant] Top {len(results)} chunks recuperados:")
    context_parts = []
    for i, hit in enumerate(results):
        score = round(hit.score, 4)
        preview = hit.payload["text"][:100].replace("\n", " ")
        print(f"    [{i+1}] score={score} | {preview}...")
        context_parts.append(hit.payload["text"])

    context = "\n\n---\n\n".join(context_parts)

    # Prompt RAG
    prompt = (
        "Eres un asistente experto en narrativa y worldbuilding.\n"
        "Responde usando ÚNICAMENTE la información del contexto proporcionado.\n"
        "Si el contexto no contiene suficiente información, indícalo claramente.\n\n"
        f"CONTEXTO:\n{context}\n\n"
        f"PREGUNTA: {question}\n\n"
        "RESPUESTA:"
    )

    # Llamada a Ollama
    print(f"\n  [llm] Consultando {OLLAMA_MODEL}...")
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 500},
    }).encode()

    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            answer = data.get("response", "").strip()
    except urllib.error.URLError as e:
        answer = f"[error conexión Ollama] {e.reason} — ¿está corriendo en {OLLAMA_BASE_URL}?"
    except Exception as e:
        answer = f"[error llm] {e}"

    print(f"\n  [respuesta]\n{answer}\n")
    return answer


# ── Listar colecciones ────────────────────────────────────────────────────────

def list_collections() -> None:
    init_db()
    with Session(engine) as session:
        collections = session.exec(select(Collection)).all()

    if not collections:
        print("No hay colecciones registradas.")
        return

    print(f"\n{'='*60}")
    print("COLECCIONES EN SQLITE")
    print(f"{'='*60}")
    for c in collections:
        with Session(engine) as session:
            doc_count = len(session.exec(
                select(Document).where(Document.collection_id == c.id)
            ).all())
        print(f"  {c.id[:8]}...  |  {c.name:<25}  |  docs={doc_count}  |  {c.status}  |  {c.created_at.strftime('%Y-%m-%d %H:%M')}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="POC RAG — Lore Master",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ingest = sub.add_parser("ingest", help="Ingestar un archivo en una colección nueva")
    p_ingest.add_argument("file", help="Ruta al archivo (PDF o TXT)")
    p_ingest.add_argument("--collection", default="poc-collection", help="Nombre de la colección")

    p_query = sub.add_parser("query", help="Consulta RAG sobre una colección existente")
    p_query.add_argument("question", help="Pregunta a realizar")
    p_query.add_argument("--collection-id", required=True, help="ID de la colección")

    p_demo = sub.add_parser("demo", help="Ingestar + consultas interactivas")
    p_demo.add_argument("file", help="Ruta al archivo")
    p_demo.add_argument("--collection", default="poc-demo", help="Nombre de la colección")

    sub.add_parser("list", help="Listar colecciones en SQLite")

    args = parser.parse_args()

    if args.cmd == "ingest":
        ingest(args.file, args.collection)

    elif args.cmd == "query":
        query_rag(args.question, args.collection_id)

    elif args.cmd == "list":
        list_collections()

    elif args.cmd == "demo":
        result = ingest(args.file, args.collection)
        print(f"\n{'='*60}")
        print("MODO DEMO — escribe preguntas sobre el documento cargado")
        print("Línea vacía para salir.")
        print(f"{'='*60}")
        while True:
            try:
                q = input("\nPregunta: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not q:
                break
            query_rag(q, result["collection_id"])


if __name__ == "__main__":
    main()
