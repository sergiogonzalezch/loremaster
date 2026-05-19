"""Harness de evaluacion para metadata en contexto RAG.

Compara tres formatos de contexto al ensamblar chunks recuperados de multiples documentos:
  baseline   — sin cabeceras de fuente (comportamiento actual)
  meta_name  — [Fuente: "archivo.txt"] por chunk
  meta_full  — [Fuente: "archivo.txt" · fragmento N · relevancia X.XX] por chunk

El corpus usa dos archivos (golden_seed.txt + golden_seed_2.txt) para que las queries
recuperen chunks de ambos documentos y el LLM pueda (o no) distinguir fuentes.

Parametros RAG fijos: chunk=400, overlap=150, threshold=0.30, top_k=4
(valores optimos de rag_params_harness 2026-05-16).

Modelos evaluados: mistral:latest, llama3.2:latest
Juez: gemma2:9b con rubrica D1-D5 (D5 = uso de informacion de fuente)

Uso:
    python evaluations/metadata_harness/runner.py \\
        --model mistral:latest \\
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

# Parametros RAG fijos (optimos de rag_params_harness)
_CHUNK_SIZE = 400
_CHUNK_OVERLAP = 150
_THRESHOLD = 0.30
_TOP_K = 4

_EVAL_TEMPERATURE = 0.7
_EVAL_NUM_PREDICT = 2000

# ── Tres configuraciones de formato de contexto ────────────────────────────────

CONFIGS: dict[str, dict] = {
    "baseline": {
        "label": "Sin cabeceras de fuente (comportamiento actual)",
        "format": "baseline",
    },
    "meta_name": {
        "label": 'Cabecera con nombre: [Fuente: "archivo.txt"]',
        "format": "meta_name",
    },
    "meta_full": {
        "label": 'Cabecera completa: [Fuente: "archivo.txt" · fragmento N · relevancia X.XX]',
        "format": "meta_full",
    },
}

# ── 10 casos de prueba ─────────────────────────────────────────────────────────
# TC-01 a TC-06: queries que recuperan chunks de AMBOS seeds (senal principal).
# TC-07 a TC-08: queries que recuperan principalmente de golden_seed.txt (control).
# TC-09 a TC-10: queries que recuperan principalmente de golden_seed_2.txt (control).

TEST_CASES: list[dict] = [
    # ── TC-01 a TC-06: queries con retrieval multi-documento verificado ─────────
    {
        "tc_id": "TC-01",
        "category": ContentCategory.extended_description,
        "entity_type": EntityType.faction,
        "entity_name": "Hermandad de la Mano Silenciosa",
        "entity_desc": "Red de espias y agentes activa en todo el reino de Valdorath.",
        "query": "Describe la Hermandad de la Mano Silenciosa: estructura, metodos y presencia en el Velo del Norte",
        "source_signal": "multi",
    },
    {
        "tc_id": "TC-02",
        "category": ContentCategory.backstory,
        "entity_type": EntityType.item,
        "entity_name": "Piedras de Enlace Umbral",
        "entity_desc": "Artefactos magicos que mantienen un vinculo activo entre dos personas a distancia.",
        "query": "La magia de vinculacion y las piedras de enlace umbral: que fuentes documentan su existencia y uso en Aetheron?",
        "source_signal": "multi",
    },
    {
        "tc_id": "TC-03",
        "category": ContentCategory.extended_description,
        "entity_type": EntityType.location,
        "entity_name": "La Torre Fracturada",
        "entity_desc": "Estructura de origen desconocido en la Llanura de las Cenizas.",
        "query": "Que se sabe sobre la Torre Fracturada en la Llanura de las Cenizas? Que dicen distintas fuentes sobre su naturaleza y fenomenos observados?",  # noqa: E501
        "source_signal": "multi",
    },
    {
        "tc_id": "TC-04",
        "category": ContentCategory.extended_description,
        "entity_type": EntityType.creature,
        "entity_name": "El Gusano del Velo",
        "entity_desc": "Criatura no registrada en los bestiarios conocidos.",
        "query": "Describe el Gusano del Velo: apariencia, comportamiento, senales de presencia y nivel de peligrosidad.",
        "source_signal": "multi",
    },
    {
        "tc_id": "TC-05",
        "category": ContentCategory.backstory,
        "entity_type": EntityType.item,
        "entity_name": "La Piedra Brasa",
        "entity_desc": "Objeto de naturaleza incierta, mencionado en varias fuentes con descripciones contradictorias.",
        "query": "Que es la Piedra Brasa? Algunas fuentes la describen como un lugar y otras como un objeto. Que se sabe con certeza?",
        "source_signal": "multi",
    },
    {
        "tc_id": "TC-06",
        "category": ContentCategory.extended_description,
        "entity_type": EntityType.location,
        "entity_name": "La Llanura de las Cenizas",
        "entity_desc": "Vasto paramo en el centro del continente, escenario de antiguas batallas.",
        "query": "Que se sabe sobre la Llanura de las Cenizas, su historia y los fenomenos actuales que ocurren en ella?",
        "source_signal": "multi",
    },
    # ── TC-07 a TC-08: queries que recuperan principalmente de golden_seed.txt ──
    {
        "tc_id": "TC-07",
        "category": ContentCategory.backstory,
        "entity_type": EntityType.location,
        "entity_name": "El Reino de Valdorath",
        "entity_desc": "Reino fundado hace tres siglos, gobernado actualmente por Aldric IV.",
        "query": "Describe la historia de fundacion del reino de Valdorath, la guerra que lo siguio y como se resolvio.",
        "source_signal": "seed1_heavy",
    },
    {
        "tc_id": "TC-08",
        "category": ContentCategory.extended_description,
        "entity_type": EntityType.location,
        "entity_name": "El Bosque Eterno de Sylvara",
        "entity_desc": "Bosque habitado por elfos del claro, actualmente afectado por una plaga.",
        "query": "Que esta ocurriendo en el Bosque Eterno de Sylvara y cuales son las teorias sobre el origen de la crisis?",
        "source_signal": "seed1_heavy",
    },
    # ── TC-09 a TC-10: queries que recuperan principalmente de golden_seed_2.txt ─
    {
        "tc_id": "TC-09",
        "category": ContentCategory.backstory,
        "entity_type": EntityType.character,
        "entity_name": "Vael Orin",
        "entity_desc": "Explorador de la Hermandad de la Mano Silenciosa activo en el Velo del Norte.",
        "query": "Quien es Vael Orin, a que organizacion pertenece y que metodologia usa en su trabajo de campo?",
        "source_signal": "seed2_heavy",
    },
    {
        "tc_id": "TC-10",
        "category": ContentCategory.scene,
        "entity_type": EntityType.character,
        "entity_name": "Kael Dawnbreaker",
        "entity_desc": "Ex-miembro de la Orden del Sol Naciente, lleva consigo la Piedra Brasa.",
        "query": "Narra la escena del primer encuentro entre Kael Dawnbreaker y Mira Solstheim junto al fuego del campamento.",
        "source_signal": "seed2_heavy",
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
D5 - Uso de fuente: Si el contexto incluye cabeceras de fuente ("[Fuente: ...]"), el texto
     distingue o atribuye informacion a distintos documentos o perspectivas? Si no hay
     cabeceras, evalua si el texto reconoce que puede haber multiples fuentes o perspectivas.

CATEGORIA: {category}
ENTIDAD: {entity_name} ({entity_type})
QUERY: {query}

CONTEXTO RAG (con formato de metadata aplicado):
---
{context}
---

TEXTO GENERADO:
---
{output}
---

Responde UNICAMENTE con JSON valido, sin texto antes ni despues:
{{"D1": <0-3>, "D1_reason": "<razon breve>", "D2": <0-3>, "D2_reason": "<razon breve>", "D3": <0-3>, "D3_reason": "<razon breve>", "D4": <0-3>, "D4_reason": "<razon breve>", "D5": <0-3>, "D5_reason": "<razon breve>"}}"""  # noqa: E501


# ── Funciones auxiliares ───────────────────────────────────────────────────────


def _load_embedding_model() -> SentenceTransformer:
    try:
        return SentenceTransformer(_EMBEDDING_MODEL_NAME)
    except (OSError, RuntimeError):
        return SentenceTransformer(_EMBEDDING_MODEL_NAME, local_files_only=True)


def _build_multi_index(
    seed_files: list[Path],
    emb_model: SentenceTransformer,
) -> tuple[list[str], list[tuple[str, int]], np.ndarray]:
    """Fragmenta multiples archivos y genera un indice combinado con metadatos de fuente.

    Returns:
        texts: lista de textos de chunk
        sources: lista de (filename, chunk_idx_within_file) para cada chunk
        embeddings: array normalizado de shape (n_chunks, dims)
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=_CHUNK_SIZE,
        chunk_overlap=_CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    all_texts: list[str] = []
    all_sources: list[tuple[str, int]] = []

    for path in seed_files:
        file_chunks = splitter.split_text(path.read_text(encoding="utf-8"))
        for idx, chunk in enumerate(file_chunks):
            all_texts.append(chunk)
            all_sources.append((path.name, idx))

    embeddings = emb_model.encode(
        all_texts, batch_size=32, show_progress_bar=False, normalize_embeddings=True
    )
    return all_texts, all_sources, np.array(embeddings)


def _retrieve(
    query: str,
    texts: list[str],
    sources: list[tuple[str, int]],
    embeddings: np.ndarray,
    emb_model: SentenceTransformer,
) -> list[tuple[str, str, int, float]]:
    """Recupera top-k chunks por encima del threshold.

    Returns list of (text, filename, chunk_idx, score), sorted by score desc.
    """
    query_emb = emb_model.encode([query], normalize_embeddings=True)[0]
    scores = embeddings @ query_emb
    candidates = [
        (float(scores[i]), texts[i], sources[i][0], sources[i][1])
        for i in range(len(texts))
        if scores[i] >= _THRESHOLD
    ]
    candidates.sort(reverse=True)
    top = candidates[:_TOP_K]
    return [(text, fname, idx, score) for score, text, fname, idx in top]


def _format_context(
    retrieved: list[tuple[str, str, int, float]],
    format_type: str,
    extra: str,
) -> str:
    """Ensambla el contexto con el formato de metadata indicado."""
    if not retrieved:
        rag_part = ""
    elif format_type == "baseline":
        rag_part = "\n\n---\n\n".join(r[0] for r in retrieved)
    elif format_type == "meta_name":
        parts = [f'[Fuente: "{r[1]}"]\n{r[0]}' for r in retrieved]
        rag_part = "\n\n---\n\n".join(parts)
    elif format_type == "meta_full":
        parts = [
            f'[Fuente: "{r[1]}" · fragmento {r[2] + 1} · relevancia {r[3]:.2f}]\n{r[0]}'
            for r in retrieved
        ]
        rag_part = "\n\n---\n\n".join(parts)
    else:
        rag_part = "\n\n---\n\n".join(r[0] for r in retrieved)

    context_parts = [p for p in (extra, rag_part) if p]
    return "\n\n---\n\n".join(context_parts) if context_parts else ""


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
        context=context[:1800],
        output=output,
    )
    llm = OllamaLLM(
        model=judge_model,
        base_url=OLLAMA_BASE_URL,
        temperature=0.1,
        num_predict=700,
    )
    raw = ""
    try:
        raw = (llm | StrOutputParser()).invoke(prompt)
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(raw[start:end])
            if all(f"D{i}" in parsed for i in range(1, 6)):
                return parsed
    except Exception:
        pass
    return {
        "D1": 0, "D1_reason": f"parse_error: {raw[:80]}",
        "D2": 0, "D2_reason": "parse_error",
        "D3": 0, "D3_reason": "parse_error",
        "D4": 0, "D4_reason": "parse_error",
        "D5": 0, "D5_reason": "parse_error",
    }


def _score_avg(scores: dict) -> float:
    return round(sum(scores.get(f"D{i}", 0) for i in range(1, 6)) / 5, 2)


# ── Runner ─────────────────────────────────────────────────────────────────────


def run_eval(
    model: str,
    config_name: str,
    judge_model: str,
    out_dir: Path,
    seed_files: list[Path],
) -> Path:
    """Ejecuta los 10 TC para un modelo y configuracion de metadata. Retorna el run_dir."""
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
    print(f"  Seeds  : {[f.name for f in seed_files]}")
    print(f"{'='*65}")

    print("  Construyendo indice multi-documento...", end=" ", flush=True)
    emb_model = _load_embedding_model()
    texts, sources, embeddings = _build_multi_index(seed_files, emb_model)
    unique_files = sorted({s[0] for s in sources})
    chunks_per_file = {f: sum(1 for s in sources if s[0] == f) for f in unique_files}
    print(f"OK ({len(texts)} chunks de {len(unique_files)} archivos: {chunks_per_file})")

    llm = _make_llm(model)
    tc_summaries = []

    for tc in TEST_CASES:
        cat = tc["category"]
        print(f"  {tc['tc_id']} [{cat.value:22}] {tc['entity_name'][:22]:<22} ...", end=" ", flush=True)

        retrieved = _retrieve(tc["query"], texts, sources, embeddings, emb_model)

        unique_sources_retrieved = sorted({r[1] for r in retrieved})
        n_chunks = len(retrieved)
        max_score = round(max(r[3] for r in retrieved), 3) if retrieved else 0.0
        multi_source = len(unique_sources_retrieved) > 1

        extra = (
            f"Descripcion de '{tc['entity_name']}' ({tc['entity_type'].value}):\n{tc['entity_desc']}\n\n"
            if tc["entity_desc"]
            else ""
        )

        context = _format_context(retrieved, cfg["format"], extra)

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
        status = "OK" if output and not error else "ERROR"
        multi_tag = "multi" if multi_source else "solo "
        print(f"{status} ({elapsed}s) chunks={n_chunks} maxsim={max_score} srcs={multi_tag} avg={avg}")

        tc_result = {
            "run_id": run_id,
            "tc_id": tc["tc_id"],
            "category": cat.value,
            "entity_type": tc["entity_type"].value,
            "source_signal": tc["source_signal"],
            "model": model,
            "config": config_name,
            "format": cfg["format"],
            "chunks_indexed": len(texts),
            "chunks_retrieved": n_chunks,
            "retrieval_scores": [r[3] for r in retrieved],
            "max_retrieval_score": max_score,
            "sources_retrieved": unique_sources_retrieved,
            "multi_source_retrieved": multi_source,
            "output": output,
            "response_time_sec": elapsed,
            "error": error,
            "scores": scores,
            "score_avg": avg,
        }
        (run_dir / f"{tc['tc_id'].lower()}_result.json").write_text(
            json.dumps(tc_result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        tc_summaries.append({
            "tc_id": tc["tc_id"],
            "status": status,
            "source_signal": tc["source_signal"],
            "response_time_sec": elapsed,
            "error": error,
            "score_avg": avg,
            "d5": scores.get("D5", 0) if scores else 0,
            "chunks_retrieved": n_chunks,
            "max_retrieval_score": max_score,
            "multi_source_retrieved": multi_source,
            "sources_retrieved": unique_sources_retrieved,
        })

    summary = {
        "run_id": run_id,
        "model": model,
        "config": config_name,
        "config_label": cfg["label"],
        "judge_model": judge_model,
        "seed_files": [f.name for f in seed_files],
        "chunks_indexed": len(texts),
        "chunks_per_file": chunks_per_file,
        "results": tc_summaries,
    }
    (run_dir / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    global_avg = round(sum(s["score_avg"] for s in tc_summaries) / len(tc_summaries), 2)
    d5_avg = round(sum(s["d5"] for s in tc_summaries) / len(tc_summaries), 2)
    errors = sum(1 for s in tc_summaries if s["status"] == "ERROR")
    multi_tcs = sum(1 for s in tc_summaries if s["multi_source_retrieved"])
    print(f"\n  -> {run_id}")
    print(f"  -> Score global: {global_avg}/3.0  |  D5 avg: {d5_avg}/3.0  |  Errores: {errors}/{len(TEST_CASES)}  |  TCs multi-fuente: {multi_tcs}/{len(TEST_CASES)}")  # noqa: E501
    return run_dir


# ── CLI ────────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evalua formatos de metadata en contexto RAG multi-documento.",
    )
    parser.add_argument("--model", required=True, help="Modelo Ollama a evaluar")
    parser.add_argument("--config", required=True, choices=list(CONFIGS))
    parser.add_argument("--judge", default="gemma2:9b", help="Modelo juez (default: gemma2:9b)")
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).parent / "results")
    parser.add_argument(
        "--seeds",
        type=str,
        default=",".join([
            str(Path(__file__).parent.parent / "dataset" / "golden_seed.txt"),
            str(Path(__file__).parent.parent / "dataset" / "golden_seed_2.txt"),
        ]),
        help="Rutas a los seed files separadas por coma",
    )
    args = parser.parse_args()

    seed_files = [Path(p.strip()) for p in args.seeds.split(",") if p.strip()]
    missing = [p for p in seed_files if not p.exists()]
    if missing:
        print(f"ERROR: seeds no encontrados: {missing}")
        sys.exit(1)

    run_eval(
        model=args.model,
        config_name=args.config,
        judge_model=args.judge,
        out_dir=args.out_dir,
        seed_files=seed_files,
    )


if __name__ == "__main__":
    main()
