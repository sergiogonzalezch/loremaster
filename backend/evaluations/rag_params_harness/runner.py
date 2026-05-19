"""Harness de evaluación para parámetros RAG: chunk_size, chunk_overlap y rag_score_threshold.

Compara cuatro configuraciones contra el baseline actual:
  baseline        — chunk=512, overlap=50, threshold=0.30
  chunks_only     — chunk=400, overlap=150, threshold=0.30
  threshold_only  — chunk=512, overlap=50, threshold=0.45
  both            — chunk=400, overlap=150, threshold=0.45

El retrieval es in-memory (sentence-transformers + cosine similarity) para no depender
de Qdrant, replicando fielmente la lógica de producción (app/engine/rag.py).

Uso:
    python evaluations/rag_params_harness/runner.py \\
        --model llama3.2:latest \\
        --config baseline \\
        --judge gemma2:9b
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_BACKEND_DIR))

from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import OllamaLLM
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

from app.domain.prompt_templates import render_prompt
from app.models.db.entity import EntityType
from app.models.enums import ContentCategory

OLLAMA_BASE_URL = "http://localhost:11434"
_EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
_TOP_K = 4
_EVAL_TEMPERATURE = 0.7
_EVAL_NUM_PREDICT = 2000

# ── Cuatro configuraciones a comparar ─────────────────────────────────────────

CONFIGS: dict[str, dict] = {
    "baseline": {
        "label": "Baseline (chunk=512, overlap=50, threshold=0.30)",
        "chunk_size": 512,
        "chunk_overlap": 50,
        "rag_score_threshold": 0.30,
    },
    "chunks_only": {
        "label": "Solo chunking (chunk=400, overlap=150, threshold=0.30)",
        "chunk_size": 400,
        "chunk_overlap": 150,
        "rag_score_threshold": 0.30,
    },
    "threshold_only": {
        "label": "Solo threshold (chunk=512, overlap=50, threshold=0.45)",
        "chunk_size": 512,
        "chunk_overlap": 50,
        "rag_score_threshold": 0.45,
    },
    "both": {
        "label": "Chunking + threshold (chunk=400, overlap=150, threshold=0.45)",
        "chunk_size": 400,
        "chunk_overlap": 150,
        "rag_score_threshold": 0.45,
    },
    "threshold_035": {
        "label": "Threshold intermedio (chunk=512, overlap=50, threshold=0.35)",
        "chunk_size": 512,
        "chunk_overlap": 50,
        "rag_score_threshold": 0.35,
    },
    "both_035": {
        "label": "Chunking + threshold intermedio (chunk=400, overlap=150, threshold=0.35)",
        "chunk_size": 400,
        "chunk_overlap": 150,
        "rag_score_threshold": 0.35,
    },
}

# ── 10 casos de prueba ─────────────────────────────────────────────────────────
# Usan entidades documentadas en golden_seed.txt (Kael, Torre Fracturada, Pacto
# de Hierro) para que el retrieval sea significativo, mas casos sparse/irrelevant
# para medir el comportamiento del threshold.

TEST_CASES: list[dict] = [
    {
        "tc_id": "TC-01",
        "category": ContentCategory.backstory,
        "entity_type": EntityType.character,
        "entity_name": "Kael Dawnbreaker",
        "entity_desc": "Ex-paladin de la Orden del Alba, excomulgado tras el Juramento Oscuro.",
        "query": "Cual fue el evento que llevo a Kael a traicionar a su orden y que consecuencias tuvo?",
        "context_quality": "rich",
    },
    {
        "tc_id": "TC-02",
        "category": ContentCategory.extended_description,
        "entity_type": EntityType.location,
        "entity_name": "La Torre Fracturada",
        "entity_desc": "Antigua torre de poder arcano en Valdorath.",
        "query": "Describe el estado actual de la Torre Fracturada: apariencia exterior, interior y ambiente.",
        "context_quality": "rich",
    },
    {
        "tc_id": "TC-03",
        "category": ContentCategory.backstory,
        "entity_type": EntityType.faction,
        "entity_name": "El Pacto de Hierro",
        "entity_desc": "Organizacion mercenaria fundada hace 200 anos con un codigo de honor estricto.",
        "query": "Escribe la historia de fundacion del Pacto de Hierro y los principios de su codigo.",
        "context_quality": "rich",
    },
    {
        "tc_id": "TC-04",
        "category": ContentCategory.scene,
        "entity_type": EntityType.creature,
        "entity_name": "El Gusano del Velo",
        "entity_desc": "Criatura de origen desconocido que habita zonas de transito entre planos.",
        "query": "Narra la escena en que un explorador encuentra al Gusano del Velo por primera vez.",
        "context_quality": "sparse",
    },
    {
        "tc_id": "TC-05",
        "category": ContentCategory.backstory,
        "entity_type": EntityType.item,
        "entity_name": "La Piedra Brasa",
        "entity_desc": "Artefacto de origen incierto con propiedades de calor persistente.",
        "query": "Cual es el origen de la Piedra Brasa y quien la creo?",
        "context_quality": "irrelevant",
    },
    {
        "tc_id": "TC-06",
        "category": ContentCategory.backstory,
        "entity_type": EntityType.character,
        "entity_name": "Kael Dawnbreaker",
        "entity_desc": "Ex-paladin excomulgado, ligado al Pacto de Hierro.",
        "query": "Que conexion existe entre la Torre Fracturada y la traicion de Kael a su orden?",
        "context_quality": "rich",
    },
    {
        "tc_id": "TC-07",
        "category": ContentCategory.extended_description,
        "entity_type": EntityType.character,
        "entity_name": "Kael Dawnbreaker",
        "entity_desc": "Ex-paladin, fue Templado del Pacto de Hierro durante 6 anos.",
        "query": "Como ve actualmente el Pacto de Hierro a Kael y que opiniones existen dentro de la organizacion?",
        "context_quality": "rich",
    },
    {
        "tc_id": "TC-08",
        "category": ContentCategory.scene,
        "entity_type": EntityType.character,
        "entity_name": "Kael Dawnbreaker",
        "entity_desc": "Ex-paladin que regresa a Velmoor por primera vez desde su exilio.",
        "query": "Narra la escena en que Kael regresa a Velmoor por primera vez desde la noche del Juramento.",
        "context_quality": "rich",
    },
    {
        "tc_id": "TC-09",
        "category": ContentCategory.extended_description,
        "entity_type": EntityType.creature,
        "entity_name": "El Gusano del Velo",
        "entity_desc": "Criatura con forma alargada sin contorno fijo, emite distorsion visual violacea.",
        "query": "Describe los rasgos fisicos y el comportamiento observable del Gusano del Velo.",
        "context_quality": "sparse",
    },
    {
        "tc_id": "TC-10",
        "category": ContentCategory.scene,
        "entity_type": EntityType.character,
        "entity_name": "Mira Solstheim",
        "entity_desc": "Alquimista del Gremio Oscuro especializada en compuestos ficticios de Valdorath.",
        "query": "Narra la escena en que Mira prepara el veneno de Sombra Profunda para infiltrar el banquete del lord traidor.",
        "context_quality": "rich",
    },
]

# ── Prompt del juez ────────────────────────────────────────────────────────────

_JUDGE_PROMPT = """\
Eres un evaluador experto en narrativa de worldbuilding. Evalua el texto generado.

ESCALA: 0=Deficiente  1=Basico  2=Bueno  3=Excelente

DIMENSIONES:
D1 - Adherencia al contexto: Usa informacion concreta del contexto RAG proporcionado?
D2 - Especificidad narrativa: Tiene detalles concretos (nombres, lugares, eventos especificos)?
D3 - Cumplimiento de categoria: Respeta extension, tiempo verbal y scope de la categoria?
D4 - Completitud: El texto esta completo, sin corte abrupto y con cierre coherente?

CATEGORIA: {category}
ENTIDAD: {entity_name} ({entity_type})
QUERY: {query}

CONTEXTO RAG (extracto):
---
{context}
---

TEXTO GENERADO:
---
{output}
---

Responde UNICAMENTE con JSON valido, sin texto antes ni despues:
{{"D1": <0-3>, "D1_reason": "<razon breve>", "D2": <0-3>, "D2_reason": "<razon breve>", "D3": <0-3>, "D3_reason": "<razon breve>", "D4": <0-3>, "D4_reason": "<razon breve>"}}"""  # noqa: E501


# ── Funciones auxiliares ───────────────────────────────────────────────────────


def _load_embedding_model() -> SentenceTransformer:
    try:
        return SentenceTransformer(_EMBEDDING_MODEL_NAME)
    except (OSError, RuntimeError):
        return SentenceTransformer(_EMBEDDING_MODEL_NAME, local_files_only=True)


def _build_index(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    emb_model: SentenceTransformer,
) -> tuple[list[str], np.ndarray]:
    """Fragmenta el texto y genera embeddings normalizados (cosine sim = dot product)."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(text)
    embeddings = emb_model.encode(
        chunks, batch_size=32, show_progress_bar=False, normalize_embeddings=True
    )
    return chunks, np.array(embeddings)


def _retrieve(
    query: str,
    chunks: list[str],
    embeddings: np.ndarray,
    emb_model: SentenceTransformer,
    threshold: float,
) -> tuple[list[str], list[float]]:
    """Recupera top-k chunks por encima del threshold. Replica app/engine/rag.py."""
    query_emb = emb_model.encode([query], normalize_embeddings=True)[0]
    scores = embeddings @ query_emb  # dot product of normalized vectors = cosine sim
    pairs = sorted(
        [(float(scores[i]), chunks[i]) for i in range(len(chunks)) if scores[i] >= threshold],
        reverse=True,
    )[:_TOP_K]
    return [c for _, c in pairs], [s for s, _ in pairs]


def _make_llm(model: str) -> OllamaLLM:
    return OllamaLLM(
        model=model,
        base_url=OLLAMA_BASE_URL,
        temperature=_EVAL_TEMPERATURE,
        num_predict=_EVAL_NUM_PREDICT,
    )


def _score_with_judge(judge_model: str, tc: dict, context: str, output: str) -> dict:
    prompt = _JUDGE_PROMPT.format(
        category=tc["category"].value,
        entity_name=tc["entity_name"],
        entity_type=tc["entity_type"].value,
        query=tc["query"],
        context=context[:1500],
        output=output,
    )
    llm = OllamaLLM(
        model=judge_model,
        base_url=OLLAMA_BASE_URL,
        temperature=0.1,
        num_predict=600,
    )
    raw = ""
    try:
        raw = (llm | StrOutputParser()).invoke(prompt)
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(raw[start:end])
            if all(f"D{i}" in parsed for i in range(1, 5)):
                return parsed
    except Exception:
        pass
    return {
        "D1": 0, "D1_reason": f"parse_error: {raw[:80]}",
        "D2": 0, "D2_reason": "parse_error",
        "D3": 0, "D3_reason": "parse_error",
        "D4": 0, "D4_reason": "parse_error",
    }


def _score_avg(scores: dict) -> float:
    return round(sum(scores.get(f"D{i}", 0) for i in range(1, 5)) / 4, 2)


# ── Runner ─────────────────────────────────────────────────────────────────────


def run_eval(
    model: str,
    config_name: str,
    judge_model: str,
    out_dir: Path,
    seed_text: str,
) -> Path:
    """Ejecuta los 10 TC para un modelo y configuracion RAG. Retorna el directorio del run."""
    cfg = CONFIGS[config_name]
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    model_slug = model.replace(":", "_").replace(".", "")
    run_id = f"{ts}_{model_slug}_{config_name}"
    run_dir = out_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*65}")
    print(f"  Modelo : {model}")
    print(f"  Config : {config_name}  --  {cfg['label']}")
    print(f"  Juez   : {judge_model}")
    print(f"{'='*65}")

    print("  Cargando modelo de embeddings...", end=" ", flush=True)
    emb_model = _load_embedding_model()
    chunks, embeddings = _build_index(seed_text, cfg["chunk_size"], cfg["chunk_overlap"], emb_model)
    print(f"OK ({len(chunks)} chunks indexados)")

    llm = _make_llm(model)
    tc_summaries = []

    for tc in TEST_CASES:
        cat = tc["category"]
        print(f"  {tc['tc_id']} [{cat.value:22}] {tc['entity_name'][:22]:<22} ...", end=" ", flush=True)

        retrieved_chunks, retrieval_scores = _retrieve(
            tc["query"], chunks, embeddings, emb_model, cfg["rag_score_threshold"]
        )

        extra = (
            f"Descripcion de '{tc['entity_name']}' ({tc['entity_type'].value}):\n{tc['entity_desc']}\n\n"
            if tc["entity_desc"]
            else ""
        )
        rag_context = "\n\n---\n\n".join(retrieved_chunks) if retrieved_chunks else ""
        parts = [p for p in (extra, rag_context) if p]
        context = "\n\n---\n\n".join(parts) if parts else ""

        rendered = render_prompt(
            category=cat,
            entity_name=tc["entity_name"],
            entity_type=tc["entity_type"].value,
            context=context,
            query=tc["query"],
        )

        t0 = time.monotonic()
        output, error = "", None
        try:
            output = (llm | StrOutputParser()).invoke(rendered)
        except Exception as exc:
            error = str(exc)
        elapsed = round(time.monotonic() - t0, 2)

        scores: dict = {}
        if output:
            scores = _score_with_judge(judge_model, tc, context, output)

        avg = _score_avg(scores) if scores else 0.0
        n_chunks = len(retrieved_chunks)
        max_score = round(max(retrieval_scores), 3) if retrieval_scores else 0.0
        status = "OK" if output and not error else "ERROR"
        print(f"{status} ({elapsed}s) chunks={n_chunks} maxsim={max_score} avg={avg}")

        tc_result = {
            "run_id": run_id,
            "tc_id": tc["tc_id"],
            "category": cat.value,
            "entity_type": tc["entity_type"].value,
            "context_quality": tc["context_quality"],
            "model": model,
            "config": config_name,
            "chunk_size": cfg["chunk_size"],
            "chunk_overlap": cfg["chunk_overlap"],
            "rag_score_threshold": cfg["rag_score_threshold"],
            "chunks_indexed": len(chunks),
            "chunks_retrieved": n_chunks,
            "retrieval_scores": retrieval_scores,
            "max_retrieval_score": max_score,
            "output": output,
            "response_time_sec": elapsed,
            "error": error,
            "scores": scores,
        }
        (run_dir / f"{tc['tc_id'].lower()}_result.json").write_text(
            json.dumps(tc_result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        tc_summaries.append({
            "tc_id": tc["tc_id"],
            "status": status,
            "response_time_sec": elapsed,
            "error": error,
            "score_avg": avg,
            "chunks_retrieved": n_chunks,
            "max_retrieval_score": max_score,
        })

    summary = {
        "run_id": run_id,
        "model": model,
        "config": config_name,
        "config_label": cfg["label"],
        "judge_model": judge_model,
        "chunk_size": cfg["chunk_size"],
        "chunk_overlap": cfg["chunk_overlap"],
        "rag_score_threshold": cfg["rag_score_threshold"],
        "chunks_indexed": len(chunks),
        "results": tc_summaries,
    }
    (run_dir / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    global_avg = round(sum(s["score_avg"] for s in tc_summaries) / len(tc_summaries), 2)
    errors = sum(1 for s in tc_summaries if s["status"] == "ERROR")
    avg_chunks = round(sum(s["chunks_retrieved"] for s in tc_summaries) / len(tc_summaries), 1)
    print(f"\n  -> {run_id}")
    print(f"  -> Score global: {global_avg}/3.0  |  Errores: {errors}/{len(TEST_CASES)}  |  Chunks/query (avg): {avg_chunks}")
    return run_dir


# ── CLI ────────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evalua parametros RAG (chunking + threshold) con un modelo dado.",
    )
    parser.add_argument("--model", required=True, help="Modelo Ollama a evaluar")
    parser.add_argument("--config", required=True, choices=list(CONFIGS))
    parser.add_argument("--judge", default="gemma2:9b", help="Modelo juez (default: gemma2:9b)")
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).parent / "results")
    parser.add_argument(
        "--seed",
        type=Path,
        default=Path(__file__).parent.parent / "dataset" / "golden_seed.txt",
    )
    args = parser.parse_args()

    if not args.seed.exists():
        print(f"ERROR: seed no encontrado: {args.seed}")
        sys.exit(1)

    seed_text = args.seed.read_text(encoding="utf-8")
    run_dir = run_eval(
        model=args.model,
        config_name=args.config,
        judge_model=args.judge,
        out_dir=args.out_dir,
        seed_text=seed_text,
    )
    print(f"\nResultados en: {run_dir}")


if __name__ == "__main__":
    main()
