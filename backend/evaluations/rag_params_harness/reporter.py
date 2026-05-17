"""Generador de reporte markdown para el harness de parametros RAG.

Uso:
    python evaluations/rag_params_harness/reporter.py
    python evaluations/rag_params_harness/reporter.py --results-dir results/ --output docs/reportes/rag_params_eval.md
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_RESULTS_DIR = Path(__file__).parent / "results"
_DEFAULT_OUTPUT = Path(__file__).resolve().parents[3] / "docs" / "reportes" / "rag_params_eval.md"

CONFIG_ORDER = ["baseline", "chunks_only", "threshold_only", "both"]
CONFIG_LABELS = {
    "baseline": "Baseline",
    "chunks_only": "Solo chunks",
    "threshold_only": "Solo threshold",
    "both": "Chunks + threshold",
}
CATEGORIES = ["backstory", "extended_description", "scene"]


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


def _dim_avg(run: dict, dim: str) -> float:
    vals = [tc["scores"].get(dim, 0) for tc in run["tc_results"].values() if tc.get("scores")]
    return round(sum(vals) / len(vals), 2) if vals else 0.0


def _global_avg(run: dict) -> float:
    avgs = [r["score_avg"] for r in run["results"] if r.get("score_avg") is not None]
    return round(sum(avgs) / len(avgs), 2) if avgs else 0.0


def _retrieval_stats(run: dict) -> dict:
    chunks = [r["chunks_retrieved"] for r in run["results"]]
    scores = [r.get("max_retrieval_score", 0) for r in run["results"]]
    if not chunks:
        return {"avg_chunks": 0.0, "min_chunks": 0, "max_chunks": 0, "avg_max_sim": 0.0}
    return {
        "avg_chunks": round(sum(chunks) / len(chunks), 1),
        "min_chunks": min(chunks),
        "max_chunks": max(chunks),
        "avg_max_sim": round(sum(scores) / len(scores), 3),
    }


def _category_scores(run: dict, category: str) -> dict:
    tcs = [tc for tc in run["tc_results"].values() if tc.get("category") == category and tc.get("scores")]
    if not tcs:
        return {"D1": 0.0, "D2": 0.0, "D3": 0.0, "D4": 0.0, "avg": 0.0}
    dims = {f"D{i}": round(sum(t["scores"].get(f"D{i}", 0) for t in tcs) / len(tcs), 2) for i in range(1, 5)}
    dims["avg"] = round(sum(dims.values()) / 4, 2)
    return dims


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
    return "="


def generate_report(runs: list[dict], title: str) -> str:
    lines: list[str] = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    judges = ", ".join(sorted({r.get("judge_model", "?") for r in runs}))

    lines += [f"# {title}", f"**Generado:** {now}  ", f"**Juez:** {judges}  ", f"**Runs:** {len(runs)}", ""]

    models = list(dict.fromkeys(r["model"] for r in runs))
    configs_present = [c for c in CONFIG_ORDER if any(r["config"] == c for r in runs)]

    # ── Resumen ejecutivo ──────────────────────────────────────────────────────
    lines += ["---", "## Resumen ejecutivo", ""]
    lines.append("> La dimension clave es **D1 (Adherencia al contexto)**: mide si el RAG aporta informacion util.")
    lines.append("> Un threshold mas alto (0.45) recupera menos chunks pero mas relevantes.")
    lines.append("> Un chunk mas pequeno (400) preserva mejor el semantico ante el limite de 128 tokens del modelo de embeddings.")
    lines.append("")

    for model in models:
        model_runs = {r["config"]: r for r in runs if r["model"] == model}
        baseline = model_runs.get("baseline")
        if not baseline:
            continue
        base_score = _global_avg(baseline)
        candidates = [(cfg, _global_avg(r)) for cfg, r in model_runs.items() if cfg != "baseline"]
        if not candidates:
            continue
        best_cfg, best_score = max(candidates, key=lambda x: x[1])
        delta = round(best_score - base_score, 2)
        verdict = "[OK]" if delta >= 0.1 else ("[~]" if abs(delta) < 0.1 else "[X]")
        lines.append(
            f"- **{model}**: mejor config = `{best_cfg}` -> avg={best_score}/3.0 "
            f"(D{delta:+.2f} vs baseline) {verdict}"
        )
    lines.append("")

    # ── 1. Ranking global ──────────────────────────────────────────────────────
    lines += ["---", "## 1. Ranking global", ""]
    lines.append("| # | Config | Modelo | D1 | D2 | D3 | D4 | Promedio | Chunks/q | MaxSim |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    sorted_runs = sorted(runs, key=lambda r: -_global_avg(r))
    for i, run in enumerate(sorted_runs, 1):
        d1, d2, d3, d4 = (_dim_avg(run, f"D{j}") for j in range(1, 5))
        avg = _global_avg(run)
        rs = _retrieval_stats(run)
        label = CONFIG_LABELS.get(run["config"], run["config"])
        lines.append(
            f"| {i} | `{label}` | {run['model']} | {d1} | {d2} | {d3} | {d4} "
            f"| **{avg}** | {rs['avg_chunks']} | {rs['avg_max_sim']} |"
        )
    lines.append("")

    # ── 2. Estadisticas de recuperacion ───────────────────────────────────────
    lines += ["---", "## 2. Estadisticas de recuperacion RAG", ""]
    lines.append("> `threshold_only` y `both` deben recuperar menos chunks (filtro mas estricto).")
    lines.append("> Si `chunks_only` mejora D1, confirma que chunks mas pequenos preservan mejor el semantico.")
    lines.append("")
    lines.append("| Config | Modelo | Chunks indexados | Chunks/query (avg) | Min | Max | MaxSim avg |")
    lines.append("|---|---|---|---|---|---|---|")
    for run in sorted(runs, key=lambda r: (CONFIG_ORDER.index(r["config"]) if r["config"] in CONFIG_ORDER else 99, r["model"])):
        rs = _retrieval_stats(run)
        label = CONFIG_LABELS.get(run["config"], run["config"])
        n_indexed = run.get("chunks_indexed", "?")
        lines.append(
            f"| `{label}` | {run['model']} | {n_indexed} "
            f"| {rs['avg_chunks']} | {rs['min_chunks']} | {rs['max_chunks']} | {rs['avg_max_sim']} |"
        )
    lines.append("")

    # ── 3. Comparativa vs baseline: foco en D1 ────────────────────────────────
    lines += ["---", "## 3. Comparativa vs baseline por modelo (foco D1)", ""]
    lines.append("> [+] = mejora >= 0.20 | [-] = regresion >= 0.20")
    lines.append("")

    non_baseline = [c for c in configs_present if c != "baseline"]
    header_cfgs = " | ".join(f"{CONFIG_LABELS[c]} | D" for c in non_baseline)
    sep_cfgs = " | ".join("--- | ---" for _ in non_baseline)

    for model in models:
        model_runs = {r["config"]: r for r in runs if r["model"] == model}
        baseline = model_runs.get("baseline")
        if not baseline:
            continue

        lines.append(f"### {model}")
        lines.append("")
        lines.append(f"| Dimension | Baseline | {header_cfgs} |")
        lines.append(f"|---|---|{sep_cfgs}|")

        dim_rows = [
            ("**D1 -- Adherencia ctx**", lambda r, d="D1": _dim_avg(r, d)),
            ("D2 -- Especificidad", lambda r, d="D2": _dim_avg(r, d)),
            ("D3 -- Categoria", lambda r, d="D3": _dim_avg(r, d)),
            ("D4 -- Completitud", lambda r, d="D4": _dim_avg(r, d)),
            ("**Promedio**", _global_avg),
        ]
        for label, fn in dim_rows:
            base_val = fn(baseline)
            row_parts = [label, str(base_val)]
            for cfg in non_baseline:
                cfg_run = model_runs.get(cfg)
                if cfg_run:
                    val = fn(cfg_run)
                    row_parts += [str(val), _delta(val, base_val)]
                else:
                    row_parts += ["--", "--"]
            lines.append("| " + " | ".join(row_parts) + " |")
        lines.append("")

    # ── 4. Analisis por categoria ──────────────────────────────────────────────
    lines += ["---", "## 4. Analisis por categoria", ""]

    for cat in CATEGORIES:
        lines.append(f"### {cat}")
        lines.append("")
        lines.append("| Config | Modelo | D1 | D2 | D3 | D4 | Promedio |")
        lines.append("|---|---|---|---|---|---|---|")
        cat_runs = sorted(runs, key=lambda r: (-_category_scores(r, cat)["avg"], r["model"]))
        for run in cat_runs:
            s = _category_scores(run, cat)
            n = sum(1 for tc in run["tc_results"].values() if tc.get("category") == cat)
            if n == 0:
                continue
            label = CONFIG_LABELS.get(run["config"], run["config"])
            lines.append(f"| `{label}` | {run['model']} | {s['D1']} | {s['D2']} | {s['D3']} | {s['D4']} | **{s['avg']}** |")
        lines.append("")

    # ── 5. Analisis por modelo ─────────────────────────────────────────────────
    lines += ["---", "## 5. Analisis por modelo", ""]

    for model in models:
        model_runs_list = sorted(
            [r for r in runs if r["model"] == model],
            key=lambda r: CONFIG_ORDER.index(r["config"]) if r["config"] in CONFIG_ORDER else 99,
        )
        if not model_runs_list:
            continue
        lines.append(f"### {model}")
        lines.append("")
        lines.append("| Config | D1 | D2 | D3 | D4 | Promedio | vs baseline | Chunks/q |")
        lines.append("|---|---|---|---|---|---|---|---|")
        baseline_score = _global_avg(
            next((r for r in model_runs_list if r["config"] == "baseline"), model_runs_list[0])
        )
        for run in model_runs_list:
            d1, d2, d3, d4 = (_dim_avg(run, f"D{j}") for j in range(1, 5))
            avg = _global_avg(run)
            vs = _delta(avg, baseline_score) if run["config"] != "baseline" else "--"
            label = CONFIG_LABELS.get(run["config"], run["config"])
            rs = _retrieval_stats(run)
            lines.append(f"| `{label}` | {d1} | {d2} | {d3} | {d4} | **{avg}** | {vs} | {rs['avg_chunks']} |")
        lines.append("")

    # ── 6. Scores por caso (D1 destacado) ─────────────────────────────────────
    lines += ["---", "## 6. Scores detallados por caso", ""]
    all_tc_ids = sorted({tc_id for r in runs for tc_id in r["tc_results"]})

    for tc_id in all_tc_ids:
        sample = next((r["tc_results"][tc_id] for r in runs if tc_id in r["tc_results"]), None)
        if not sample:
            continue
        cat = sample.get("category", "?")
        etype = sample.get("entity_type", "?")
        cq = sample.get("context_quality", "?")
        lines.append(f"#### {tc_id} -- {etype} / {cat}  *(contexto: {cq})*")
        lines.append("")
        lines.append("| Config | Modelo | D1 | D2 | D3 | D4 | Avg | Chunks | MaxSim |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for run in sorted(
            runs,
            key=lambda r: (CONFIG_ORDER.index(r["config"]) if r["config"] in CONFIG_ORDER else 99, r["model"]),
        ):
            tc = run["tc_results"].get(tc_id)
            label = CONFIG_LABELS.get(run["config"], run["config"])
            if not tc or not tc.get("scores"):
                lines.append(f"| `{label}` | {run['model']} | -- | -- | -- | -- | -- | -- | -- |")
                continue
            s = tc["scores"]
            avg_val = round(sum(s.get(f"D{i}", 0) for i in range(1, 5)) / 4, 2)
            n_ch = tc.get("chunks_retrieved", "?")
            max_sim = tc.get("max_retrieval_score", "?")
            lines.append(
                f"| `{label}` | {run['model']} "
                f"| {s.get('D1',0)} | {s.get('D2',0)} | {s.get('D3',0)} | {s.get('D4',0)} "
                f"| {avg_val} | {n_ch} | {max_sim} |"
            )
        lines.append("")

    # ── 7. Decision recomendada ────────────────────────────────────────────────
    lines += ["---", "## 7. Decision recomendada", ""]
    lines.append("| Umbral | Significado |")
    lines.append("|---|---|")
    lines.append("| D1 mejora >= 0.20 | Implementar el cambio |")
    lines.append("| |D1| < 0.20 | Neutral -- no justifica complejidad |")
    lines.append("| D1 empeora >= 0.20 | Descartar |")
    lines.append("")

    for model in models:
        model_runs = {r["config"]: r for r in runs if r["model"] == model}
        baseline = model_runs.get("baseline")
        if not baseline:
            continue
        base_d1 = _dim_avg(baseline, "D1")
        base_avg = _global_avg(baseline)

        lines.append(f"### {model}")
        lines.append("")
        for cfg in non_baseline:
            run = model_runs.get(cfg)
            if not run:
                continue
            d1 = _dim_avg(run, "D1")
            avg = _global_avg(run)
            dd1 = round(d1 - base_d1, 2)
            davg = round(avg - base_avg, 2)
            if dd1 >= 0.2:
                verdict = f"[OK] IMPLEMENTAR (D1 {dd1:+.2f}, avg {davg:+.2f})"
            elif dd1 <= -0.2:
                verdict = f"[X] DESCARTAR (D1 {dd1:+.2f}, avg {davg:+.2f})"
            else:
                verdict = f"[~] NEUTRAL (D1 {dd1:+.2f}, avg {davg:+.2f})"
            label = CONFIG_LABELS.get(cfg, cfg)
            lines.append(f"- `{label}`: {verdict}")
        lines.append("")

    lines += [
        "---",
        "*Reporte generado por `evaluations/rag_params_harness/reporter.py`*",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera reporte markdown de parametros RAG.")
    parser.add_argument("--runs", nargs="*", type=Path, default=None)
    parser.add_argument("--results-dir", type=Path, default=_RESULTS_DIR)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument(
        "--title",
        default="Evaluacion de Parametros RAG -- chunk_size, chunk_overlap y rag_score_threshold",
    )
    args = parser.parse_args()

    run_dirs: list[Path]
    if args.runs:
        run_dirs = [Path(p) for p in args.runs]
    else:
        if not args.results_dir.exists():
            print(f"ERROR: directorio no existe: {args.results_dir}")
            return
        run_dirs = sorted(
            [d for d in args.results_dir.iterdir() if d.is_dir() and (d / "run_summary.json").exists()]
        )

    if not run_dirs:
        print("No se encontraron runs. Ejecuta runner.py primero.")
        return

    runs = []
    for d in run_dirs:
        run = _load_run(d)
        if run:
            runs.append(run)
            print(f"  [+] {d.name}  ({run['model']} / {run['config']})")
        else:
            print(f"  [-] {d.name}  (sin run_summary.json, ignorado)")

    if not runs:
        print("ERROR: ningun run cargado.")
        return

    # Deduplicar: si hay multiples runs para el mismo modelo+config, conservar el mas reciente
    seen: dict[tuple, dict] = {}
    for run in runs:
        key = (run["model"], run["config"])
        if key not in seen or run["run_id"] > seen[key]["run_id"]:
            seen[key] = run
    if len(seen) < len(runs):
        print(f"  [!] {len(runs) - len(seen)} run(s) duplicado(s) descartado(s)")
    runs = list(seen.values())

    print(f"\nGenerando reporte con {len(runs)} runs...")
    report = generate_report(runs, args.title)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"[OK] Reporte guardado en: {args.output}")


if __name__ == "__main__":
    main()
