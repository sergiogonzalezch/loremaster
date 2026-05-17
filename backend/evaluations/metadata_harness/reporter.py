"""Generador de reporte markdown para el harness de metadata en contexto RAG.

Uso:
    python evaluations/metadata_harness/reporter.py
    python evaluations/metadata_harness/reporter.py \\
        --results-dir results/ --output docs/reportes/metadata_eval.md
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_RESULTS_DIR = Path(__file__).parent / "results"
_DEFAULT_OUTPUT = Path(__file__).resolve().parents[3] / "docs" / "reportes" / "metadata_eval.md"

CONFIG_ORDER = ["baseline", "meta_name", "meta_full"]
CONFIG_LABELS = {
    "baseline": "Baseline (sin headers)",
    "meta_name": "meta_name [Fuente: archivo]",
    "meta_full": "meta_full [Fuente: archivo · frag · rel]",
}
SOURCE_SIGNALS = ["multi", "seed1_heavy", "seed2_heavy"]


def _load_run(run_dir: Path) -> dict | None:
    summary_path = run_dir / "run_summary.json"
    if not summary_path.exists():
        return None
    run = json.loads(summary_path.read_text(encoding="utf-8"))
    run["tc_results"] = {}
    for tc_file in sorted(run_dir.glob("tc-*_result.json")):
        data = json.loads(tc_file.read_text(encoding="utf-8"))
        run["tc_results"][data["tc_id"]] = data
    return run


def _global_avg(run: dict) -> float:
    avgs = [r["score_avg"] for r in run["results"] if r.get("score_avg") is not None]
    return round(sum(avgs) / len(avgs), 2) if avgs else 0.0


def _dim_avg(run: dict, dim: str) -> float:
    vals = [tc["scores"].get(dim, 0) for tc in run["tc_results"].values() if tc.get("scores")]
    return round(sum(vals) / len(vals), 2) if vals else 0.0


def _signal_avg(run: dict, signal: str, dim: str | None = None) -> float:
    tcs = [
        tc for tc in run["tc_results"].values()
        if tc.get("source_signal") == signal and tc.get("scores")
    ]
    if not tcs:
        return 0.0
    if dim:
        vals = [tc["scores"].get(dim, 0) for tc in tcs]
    else:
        vals = [tc.get("score_avg", 0) for tc in tcs]
    return round(sum(vals) / len(vals), 2) if vals else 0.0


def _multi_source_count(run: dict) -> int:
    return sum(1 for r in run["results"] if r.get("multi_source_retrieved"))


def _delta(val: float, base: float) -> str:
    d = round(val - base, 2)
    if d >= 0.2:
        return f"+{d} [+]"
    if d <= -0.2:
        return f"{d} [-]"
    if d > 0:
        return f"+{d}"
    if d < 0:
        return f"{d}"
    return "0.00"


def _load_all_runs(results_dir: Path) -> dict[str, dict[str, dict]]:
    """Retorna {model: {config: run_data}}."""
    runs: dict[str, dict[str, dict]] = {}
    for run_dir in sorted(results_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        run = _load_run(run_dir)
        if not run:
            continue
        model = run["model"]
        config = run["config"]
        if model not in runs:
            runs[model] = {}
        # Ultimo run gana si hay duplicados
        if config not in runs[model] or run_dir.name > list(runs[model].values())[-1].get("_dir", ""):
            run["_dir"] = run_dir.name
            runs[model][config] = run
    return runs


def generate_report(results_dir: Path, output: Path, title: str) -> None:
    runs = _load_all_runs(results_dir)
    if not runs:
        print(f"ERROR: No se encontraron runs en {results_dir}")
        return

    models = sorted(runs.keys())
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: list[str] = []

    lines += [f"# {title}", "", f"*Generado: {now}*", ""]

    # ── Indice ─────────────────────────────────────────────────────────────────
    lines += [
        "## Indice", "",
        "1. [Corpus y configuraciones](#1-corpus-y-configuraciones)",
        "2. [Score global por config y modelo](#2-score-global-por-config-y-modelo)",
        "3. [D5 — uso de fuente por config](#3-d5--uso-de-fuente-por-config)",
        "4. [Multi-source vs single-source TCs](#4-multi-source-vs-single-source-tcs)",
        "5. [Dimensiones D1-D5 por config (todos los modelos)](#5-dimensiones-d1-d5-por-config)",
        "6. [Detalle por modelo](#6-detalle-por-modelo)",
        "7. [Decision](#7-decision)",
        "",
    ]

    # ── 1. Corpus y configuraciones ─────────────────────────────────────────────
    lines += ["## 1. Corpus y configuraciones", ""]

    # Tomar info de cualquier run disponible
    sample_run = next(iter(next(iter(runs.values())).values()))
    seed_files = sample_run.get("seed_files", [])
    chunks_per_file = sample_run.get("chunks_per_file", {})
    total_chunks = sample_run.get("chunks_indexed", 0)

    lines += [
        "**Corpus multi-documento:**",
        "",
    ]
    for f in seed_files:
        c = chunks_per_file.get(f, "?")
        lines.append(f"- `{f}` — {c} chunks")
    lines += [f"- Total indexado: {total_chunks} chunks (chunk=400, overlap=150, threshold=0.30, top_k=4)", ""]

    lines += [
        "**Configuraciones evaluadas:**",
        "",
        "| Config | Descripcion |",
        "|---|---|",
    ]
    for cfg_key in CONFIG_ORDER:
        label = CONFIG_LABELS.get(cfg_key, cfg_key)
        lines.append(f"| `{cfg_key}` | {label} |")
    lines += [""]

    lines += [
        "**Modelos evaluados:** " + ", ".join(f"`{m}`" for m in models),
        "",
        "**Juez:** `gemma2:9b` (D1-D5, escala 0-3)",
        "",
        "**Rubrica D5 (uso de fuente):** Evalua si el texto generado distingue o atribuye",
        "informacion a distintos documentos cuando el contexto incluye cabeceras de fuente.",
        "Para baseline (sin cabeceras), mide si el LLM muestra conciencia de multiples perspectivas.",
        "",
    ]

    # ── 2. Score global ─────────────────────────────────────────────────────────
    lines += ["## 2. Score global por config y modelo", ""]

    header = "| Config |" + "".join(f" {m} |" for m in models) + " Avg modelos |"
    sep = "|---|" + "---|" * (len(models) + 1)
    lines += [header, sep]

    config_model_scores: dict[str, dict[str, float]] = {}
    for cfg_key in CONFIG_ORDER:
        label = CONFIG_LABELS.get(cfg_key, cfg_key)
        row_scores: list[float] = []
        cells: list[str] = []
        for model in models:
            run = runs.get(model, {}).get(cfg_key)
            if run:
                s = _global_avg(run)
                row_scores.append(s)
                cells.append(f" {s} |")
            else:
                cells.append(" — |")
        avg_across = round(sum(row_scores) / len(row_scores), 2) if row_scores else 0.0
        config_model_scores.setdefault(cfg_key, {})
        for model, run in runs.items():
            if cfg_key in run:
                config_model_scores[cfg_key][model] = _global_avg(run[cfg_key])
        lines.append(f"| **{label}** |" + "".join(cells) + f" **{avg_across}** |")
    lines += [""]

    # Fila de delta vs baseline
    baseline_avgs = {
        m: _global_avg(runs[m]["baseline"]) for m in models if "baseline" in runs.get(m, {})
    }
    if baseline_avgs:
        lines += ["**Delta vs baseline:**", "", "| Config |" + "".join(f" {m} |" for m in models) + "|", sep]
        for cfg_key in CONFIG_ORDER:
            if cfg_key == "baseline":
                continue
            label = CONFIG_LABELS.get(cfg_key, cfg_key)
            cells = []
            for model in models:
                run = runs.get(model, {}).get(cfg_key)
                base = baseline_avgs.get(model)
                if run and base is not None:
                    cells.append(f" {_delta(_global_avg(run), base)} |")
                else:
                    cells.append(" — |")
            lines.append(f"| **{label}** |" + "".join(cells) + "|")
        lines += [""]

    # ── 3. D5 por config ───────────────────────────────────────────────────────
    lines += ["## 3. D5 — uso de fuente por config", ""]
    lines += [
        "D5 es la dimension clave del harness: mide si el LLM usa las cabeceras de fuente",
        "para distinguir informacion de distintos documentos.",
        "",
        "| Config |" + "".join(f" {m} (D5) |" for m in models) + " Avg D5 |",
        sep,
    ]

    for cfg_key in CONFIG_ORDER:
        label = CONFIG_LABELS.get(cfg_key, cfg_key)
        d5_scores: list[float] = []
        cells: list[str] = []
        for model in models:
            run = runs.get(model, {}).get(cfg_key)
            if run:
                d5 = _dim_avg(run, "D5")
                d5_scores.append(d5)
                cells.append(f" {d5} |")
            else:
                cells.append(" — |")
        avg_d5 = round(sum(d5_scores) / len(d5_scores), 2) if d5_scores else 0.0
        lines.append(f"| **{label}** |" + "".join(cells) + f" **{avg_d5}** |")
    lines += [""]

    # ── 4. Multi-source vs single-source ───────────────────────────────────────
    lines += ["## 4. Multi-source vs single-source TCs", ""]
    lines += [
        "Separacion de TCs segun si el retrieval recupero chunks de ambos archivos (multi)",
        "o de un unico archivo. Los TCs multi-source son el escenario donde las cabeceras",
        "aportan mas valor.",
        "",
    ]

    for cfg_key in CONFIG_ORDER:
        label = CONFIG_LABELS.get(cfg_key, cfg_key)
        lines += [f"**{label}:**", ""]
        lines += [
            "| Modelo | Multi-source score | Single-source score | D5 (multi) | TCs multi |",
            "|---|---|---|---|---|",
        ]
        for model in models:
            run = runs.get(model, {}).get(cfg_key)
            if not run:
                lines.append(f"| {model} | — | — | — | — |")
                continue
            multi_avg = _signal_avg(run, "multi")
            single_avg_s1 = _signal_avg(run, "seed1_only")
            single_avg_s2 = _signal_avg(run, "seed2_only")
            single_all = [
                tc for tc in run["tc_results"].values()
                if tc.get("source_signal") in ("seed1_heavy", "seed2_heavy") and tc.get("scores")
            ]
            single_avg = round(
                sum(tc.get("score_avg", 0) for tc in single_all) / len(single_all), 2
            ) if single_all else 0.0
            d5_multi = _signal_avg(run, "multi", "D5")
            n_multi = _multi_source_count(run)
            lines.append(
                f"| {model} | {multi_avg} | {single_avg} | {d5_multi} | {n_multi}/10 |"
            )
        lines += [""]

    # ── 5. Dimensiones D1-D5 ──────────────────────────────────────────────────
    lines += ["## 5. Dimensiones D1-D5 por config", ""]

    for cfg_key in CONFIG_ORDER:
        label = CONFIG_LABELS.get(cfg_key, cfg_key)
        lines += [f"**{label}:**", ""]
        lines += [
            "| Modelo | D1 | D2 | D3 | D4 | D5 | Avg |",
            "|---|---|---|---|---|---|---|",
        ]
        for model in models:
            run = runs.get(model, {}).get(cfg_key)
            if not run:
                lines.append(f"| {model} | — | — | — | — | — | — |")
                continue
            dims = [_dim_avg(run, f"D{i}") for i in range(1, 6)]
            avg = _global_avg(run)
            cells = " | ".join(str(d) for d in dims)
            lines.append(f"| {model} | {cells} | **{avg}** |")
        lines += [""]

    # ── 6. Detalle por modelo ──────────────────────────────────────────────────
    lines += ["## 6. Detalle por modelo", ""]

    for model in models:
        model_runs = runs.get(model, {})
        if not model_runs:
            continue
        lines += [f"### {model}", ""]

        # Tabla de TCs con scores por config
        tc_ids = [tc["tc_id"] for tc in sorted(
            next(iter(model_runs.values()))["tc_results"].values(),
            key=lambda x: x["tc_id"]
        )]

        header_parts = ["TC", "source_signal"]
        for cfg_key in CONFIG_ORDER:
            if cfg_key in model_runs:
                header_parts.append(f"{cfg_key} (avg)")
                header_parts.append(f"{cfg_key} (D5)")
        header_parts += ["chunks", "multi_src"]

        lines += ["| " + " | ".join(header_parts) + " |"]
        lines += ["|" + "---|" * len(header_parts)]

        for tc_id in tc_ids:
            row = [tc_id]
            signal = ""
            chunks_info = ""
            multi_info = ""
            for cfg_key in CONFIG_ORDER:
                run = model_runs.get(cfg_key)
                if not run:
                    continue
                tc = run["tc_results"].get(tc_id, {})
                if not signal:
                    signal = tc.get("source_signal", "?")
                    chunks_info = str(tc.get("chunks_retrieved", "?"))
                    multi_info = "si" if tc.get("multi_source_retrieved") else "no"
                avg = tc.get("score_avg", "?")
                d5 = tc.get("scores", {}).get("D5", "?") if tc.get("scores") else "?"
                row += [str(avg), str(d5)]

            lines.append("| " + tc_id + " | " + signal + " | " + " | ".join(str(x) for x in row[1:]) + f" | {chunks_info} | {multi_info} |")

        lines += [""]

    # ── 7. Decision ───────────────────────────────────────────────────────────
    lines += [
        "## 7. Decision",
        "",
        "> *Seccion a completar manualmente tras analizar los resultados.*",
        "",
        "**Pregunta principal:** ¿Añadir cabeceras de fuente al contexto RAG mejora la calidad",
        "de la generacion cuando el corpus es multi-documento?",
        "",
        "**Opciones de implementacion (si la evaluacion es positiva):**",
        "",
        "- **Opcion A — filename en payload Qdrant (ingest time):**",
        "  Almacenar `filename` junto con `doc_id` al indexar chunks. Retrieve recupera el",
        "  nombre directamente sin query adicional. Simple, sin overhead en query time.",
        "  Tradeoff: si el documento se renombra despues de la ingesta, el payload queda desactualizado.",
        "",
        "- **Opcion B — lookup DB en query time:**",
        "  `search_context` recibe los `doc_id` UUID de los resultados Qdrant y hace un",
        "  SELECT a la tabla `documents` para recuperar el `filename`. Siempre actualizado.",
        "  Tradeoff: una query DB adicional por llamada RAG.",
        "",
        "**Umbral de adopcion sugerido:** Δ D1 >= +0.2 O Δ D5 >= +0.5 respecto a baseline",
        "en TCs multi-source, con al menos un modelo fiable (mistral o llama3.2).",
        "",
        "| Metrica | Resultado | Umbral | Decision |",
        "|---|---|---|---|",
        "| Δ D1 (meta_name vs baseline, multi-source) | _pendiente_ | >= +0.2 | _pendiente_ |",
        "| Δ D1 (meta_full vs baseline, multi-source) | _pendiente_ | >= +0.2 | _pendiente_ |",
        "| Δ D5 (meta_name vs baseline) | _pendiente_ | >= +0.5 | _pendiente_ |",
        "| Δ D5 (meta_full vs baseline) | _pendiente_ | >= +0.5 | _pendiente_ |",
        "",
    ]

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Reporte generado: {output}")
    print(f"     Modelos: {models}")
    print(f"     Configs: {CONFIG_ORDER}")
    total_runs = sum(len(v) for v in runs.values())
    print(f"     Runs cargados: {total_runs}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera reporte markdown del metadata_harness.",
    )
    parser.add_argument("--results-dir", type=Path, default=_RESULTS_DIR)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument(
        "--title",
        default="Evaluacion de Metadata en Contexto RAG -- cabeceras de fuente",
    )
    args = parser.parse_args()
    generate_report(args.results_dir, args.output, args.title)


if __name__ == "__main__":
    main()