"""Generador de reporte markdown comparativo para el harness de parámetros LLM.

Carga los runs del directorio results/ y genera una comparativa entre
configuraciones (baseline, temp_only, tokens_only, both) y modelos.

Uso:
    # Generar con todos los runs del directorio por defecto
    python evaluations/llm_params_harness/reporter.py

    # Especificar runs concretos
    python evaluations/llm_params_harness/reporter.py \\
        --runs results/2026-05-16_llama32_baseline results/2026-05-16_llama32_temp_only \\
        --output docs/reportes/llm_params_eval.md \\
        --title "Eval Temperatura y Tokens — Mayo 2026"
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Carga de datos ─────────────────────────────────────────────────────────────

_RESULTS_DIR = Path(__file__).parent / "results"
_DEFAULT_OUTPUT = Path(__file__).resolve().parents[3] / "docs" / "reportes" / "llm_params_eval.md"

CONFIG_ORDER = ["baseline", "temp_only", "tokens_only", "both"]
CONFIG_LABELS = {
    "baseline": "Baseline",
    "temp_only": "Solo temp",
    "tokens_only": "Solo tokens",
    "both": "Temp + tokens",
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


def _category_scores(run: dict, category: str) -> dict:
    tcs = [tc for tc in run["tc_results"].values() if tc.get("category") == category and tc.get("scores")]
    if not tcs:
        return {"D1": 0.0, "D2": 0.0, "D3": 0.0, "D4": 0.0, "avg": 0.0}
    dims = {f"D{i}": round(sum(t["scores"].get(f"D{i}", 0) for t in tcs) / len(tcs), 2) for i in range(1, 5)}
    dims["avg"] = round(sum(dims.values()) / 4, 2)
    return dims


def _global_avg(run: dict) -> float:
    avgs = [r["score_avg"] for r in run["results"] if r.get("score_avg") is not None]
    return round(sum(avgs) / len(avgs), 2) if avgs else 0.0


def _time_stats(run: dict) -> dict:
    times = [r["response_time_sec"] for r in run["results"] if r.get("response_time_sec")]
    if not times:
        return {"avg": 0.0, "min": 0.0, "max": 0.0}
    return {"avg": round(sum(times) / len(times), 1), "min": round(min(times), 1), "max": round(max(times), 1)}


def _error_count(run: dict) -> int:
    return sum(1 for r in run["results"] if r.get("status") == "ERROR")


def _delta(val: float, base: float) -> str:
    d = round(val - base, 2)
    if d > 0:
        return f"+{d} ✓" if d >= 0.2 else f"+{d}"
    if d < 0:
        return f"{d} ✗" if d <= -0.2 else f"{d}"
    return "="


# ── Generación del reporte ─────────────────────────────────────────────────────


def generate_report(runs: list[dict], title: str) -> str:
    lines: list[str] = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    judges = ", ".join(sorted({r.get("judge_model", "?") for r in runs}))

    lines += [f"# {title}", f"**Generado:** {now}  ", f"**Juez:** {judges}  ", f"**Runs:** {len(runs)}", ""]

    models = list(dict.fromkeys(r["model"] for r in runs))
    configs_present = [c for c in CONFIG_ORDER if any(r["config"] == c for r in runs)]

    # ── Resumen ejecutivo ──────────────────────────────────────────────────────
    lines += ["---", "## Resumen ejecutivo", ""]
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
        icon = "🏆" if delta >= 0.3 else ("✅" if delta >= 0.1 else ("⚪" if abs(delta) < 0.1 else "❌"))
        lines.append(f"- **{model}**: mejor config = `{best_cfg}` → avg={best_score}/3.0 " f"(Δ{delta:+.2f} vs baseline) {icon}")
    lines.append("")

    # ── 1. Ranking global ──────────────────────────────────────────────────────
    lines += ["---", "## 1. Ranking global", ""]
    lines.append("| # | Configuración | Modelo | Errores | D1 | D2 | D3 | D4 | Promedio |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    sorted_runs = sorted(runs, key=lambda r: -_global_avg(r))
    for i, run in enumerate(sorted_runs, 1):
        d1, d2, d3, d4 = (_dim_avg(run, f"D{j}") for j in range(1, 5))
        avg = _global_avg(run)
        label = CONFIG_LABELS.get(run["config"], run["config"])
        lines.append(f"| {i} | `{label}` | {run['model']} | {_error_count(run)} | {d1} | {d2} | {d3} | {d4} | **{avg}** |")
    lines.append("")

    # ── 2. Comparativa vs baseline por modelo ─────────────────────────────────
    lines += ["---", "## 2. Comparativa de configuraciones vs baseline", ""]
    lines.append("> ✓ = mejora ≥ 0.20 | ✗ = regresión ≥ 0.20")
    lines.append("")

    non_baseline = [c for c in configs_present if c != "baseline"]
    header_cfgs = " | ".join(f"{CONFIG_LABELS[c]} | Δ" for c in non_baseline)
    sep_cfgs = " | ".join("--- | ---" for _ in non_baseline)

    for model in models:
        model_runs = {r["config"]: r for r in runs if r["model"] == model}
        baseline = model_runs.get("baseline")
        if not baseline:
            continue

        lines.append(f"### {model}")
        lines.append("")
        lines.append(f"| Dimensión | Baseline | {header_cfgs} |")
        lines.append(f"|---|---|{sep_cfgs}|")

        dim_rows = [
            ("D1 — Adherencia ctx", lambda r, d="D1": _dim_avg(r, d)),
            ("D2 — Especificidad", lambda r, d="D2": _dim_avg(r, d)),
            ("D3 — Categoría", lambda r, d="D3": _dim_avg(r, d)),
            ("D4 — Completitud", lambda r, d="D4": _dim_avg(r, d)),
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
                    row_parts += ["—", "—"]
            lines.append("| " + " | ".join(row_parts) + " |")
        lines.append("")

    # ── 3. Análisis por categoría ──────────────────────────────────────────────
    lines += ["---", "## 3. Análisis por categoría", ""]
    lines.append("> Permite ver si temperatura beneficia más a `scene` que a `backstory`, etc.")
    lines.append("")

    for cat in CATEGORIES:
        lines.append(f"### {cat}")
        lines.append("")
        lines.append("| Configuración | Modelo | D1 | D2 | D3 | D4 | Promedio |")
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

    # ── 4. Análisis por modelo ─────────────────────────────────────────────────
    lines += ["---", "## 4. Análisis por modelo", ""]
    lines.append("> ¿La mejora es consistente entre modelos o solo beneficia a alguno?")
    lines.append("")

    for model in models:
        model_runs_list = sorted(
            [r for r in runs if r["model"] == model],
            key=lambda r: CONFIG_ORDER.index(r["config"]) if r["config"] in CONFIG_ORDER else 99,
        )
        if not model_runs_list:
            continue
        lines.append(f"### {model}")
        lines.append("")
        lines.append("| Configuración | D1 | D2 | D3 | D4 | Promedio | vs baseline |")
        lines.append("|---|---|---|---|---|---|---|")

        baseline_score = _global_avg(next((r for r in model_runs_list if r["config"] == "baseline"), model_runs_list[0]))
        for run in model_runs_list:
            d1, d2, d3, d4 = (_dim_avg(run, f"D{j}") for j in range(1, 5))
            avg = _global_avg(run)
            vs = _delta(avg, baseline_score) if run["config"] != "baseline" else "—"
            label = CONFIG_LABELS.get(run["config"], run["config"])
            lines.append(f"| `{label}` | {d1} | {d2} | {d3} | {d4} | **{avg}** | {vs} |")
        lines.append("")

    # ── 5. Tiempos de respuesta ────────────────────────────────────────────────
    lines += ["---", "## 5. Tiempos de respuesta", ""]
    lines.append("> `tokens_only` y `both` aumentan num_predict en `scene` (2000→2500); se espera latencia ligeramente mayor.")
    lines.append("")
    lines.append("| Configuración | Modelo | Promedio (s) | Mínimo (s) | Máximo (s) |")
    lines.append("|---|---|---|---|---|")
    for run in sorted(runs, key=lambda r: (r["config"], r["model"])):
        t = _time_stats(run)
        label = CONFIG_LABELS.get(run["config"], run["config"])
        lines.append(f"| `{label}` | {run['model']} | {t['avg']} | {t['min']} | {t['max']} |")
    lines.append("")

    # ── 6. Scores detallados por caso ──────────────────────────────────────────
    lines += ["---", "## 6. Scores detallados por caso", ""]
    all_tc_ids = sorted({tc_id for r in runs for tc_id in r["tc_results"]})

    for tc_id in all_tc_ids:
        sample = next((r["tc_results"][tc_id] for r in runs if tc_id in r["tc_results"]), None)
        if not sample:
            continue
        cat = sample.get("category", "?")
        etype = sample.get("entity_type", "?")
        cq = sample.get("context_quality", "?")
        lines.append(f"#### {tc_id} — {etype} / {cat}  *(contexto: {cq})*")
        lines.append("")
        lines.append("| Configuración | Modelo | D1 | D2 | D3 | D4 | Avg |")
        lines.append("|---|---|---|---|---|---|---|")
        for run in sorted(runs, key=lambda r: (CONFIG_ORDER.index(r["config"]) if r["config"] in CONFIG_ORDER else 99, r["model"])):
            tc = run["tc_results"].get(tc_id)
            label = CONFIG_LABELS.get(run["config"], run["config"])
            if not tc or not tc.get("scores"):
                lines.append(f"| `{label}` | {run['model']} | — | — | — | — | — |")
                continue
            s = tc["scores"]
            avg_val = round(sum(s.get(f"D{i}", 0) for i in range(1, 5)) / 4, 2)
            lines.append(
                f"| `{label}` | {run['model']} " f"| {s.get('D1', 0)} | {s.get('D2', 0)} | {s.get('D3', 0)} | {s.get('D4', 0)} " f"| {avg_val} |"
            )
        lines.append("")

    # ── 7. Decisión recomendada ────────────────────────────────────────────────
    lines += ["---", "## 7. Decisión recomendada", ""]
    lines.append("| Umbral | Significado |")
    lines.append("|---|---|")
    lines.append("| Δ ≥ 0.30 | ✅ Implementar — mejora sustancial |")
    lines.append("| 0.10 ≤ Δ < 0.30 | 🟡 Considerar — mejora marginal |")
    lines.append("| \\|Δ\\| < 0.10 | ⚪ Neutral — sin diferencia significativa |")
    lines.append("| Δ < −0.10 | ❌ Descartar — regresión |")
    lines.append("")

    for model in models:
        model_runs = {r["config"]: r for r in runs if r["model"] == model}
        baseline = model_runs.get("baseline")
        if not baseline:
            continue
        base_score = _global_avg(baseline)

        lines.append(f"### {model}")
        lines.append("")
        for cfg in non_baseline:
            run = model_runs.get(cfg)
            if not run:
                continue
            score = _global_avg(run)
            d = round(score - base_score, 2)
            if d >= 0.3:
                verdict = f"✅ **IMPLEMENTAR** (Δ{d:+.2f})"
            elif d >= 0.1:
                verdict = f"🟡 **CONSIDERAR** (Δ{d:+.2f})"
            elif d >= -0.1:
                verdict = f"⚪ **NEUTRAL** (Δ{d:+.2f})"
            else:
                verdict = f"❌ **DESCARTAR** (Δ{d:+.2f})"
            label = CONFIG_LABELS.get(cfg, cfg)
            lines.append(f"- `{label}`: {verdict}")
        lines.append("")

    lines += [
        "---",
        "*Reporte generado por `evaluations/llm_params_harness/reporter.py`*",
    ]
    return "\n".join(lines)


# ── CLI ────────────────────────────────────────────────────────────────────────


def main() -> None:
    """Punto de entrada CLI del reporter."""
    parser = argparse.ArgumentParser(
        description="Genera reporte markdown comparativo de configuraciones LLM.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Todos los runs del directorio de resultados por defecto
  python evaluations/llm_params_harness/reporter.py

  # Runs específicos
  python evaluations/llm_params_harness/reporter.py \\
      --runs results/2026-05-16_llama32_baseline results/2026-05-16_llama32_temp_only \\
      --output docs/reportes/mi_eval.md
        """,
    )
    parser.add_argument(
        "--runs",
        nargs="*",
        type=Path,
        default=None,
        help="Directorios de runs. Si se omite, usa todos los de --results-dir.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=_RESULTS_DIR,
        help=f"Directorio raíz de resultados (default: {_RESULTS_DIR})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_DEFAULT_OUTPUT,
        help=f"Archivo markdown de salida (default: {_DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--title",
        default="Evaluación de Parámetros LLM — Temperatura y num_predict",
        help="Título del reporte",
    )
    args = parser.parse_args()

    run_dirs: list[Path]
    if args.runs:
        run_dirs = [Path(p) for p in args.runs]
    else:
        if not args.results_dir.exists():
            print(f"ERROR: directorio de resultados no existe: {args.results_dir}")
            return
        run_dirs = sorted([d for d in args.results_dir.iterdir() if d.is_dir() and (d / "run_summary.json").exists()])

    if not run_dirs:
        print("No se encontraron runs. Ejecuta runner.py primero.")
        return

    runs = []
    for d in run_dirs:
        run = _load_run(d)
        if run:
            runs.append(run)
            print(f"  ✓ {d.name}  ({run['model']} / {run['config']})")
        else:
            print(f"  ✗ {d.name}  (sin run_summary.json, ignorado)")

    if not runs:
        print("ERROR: ningún run cargado correctamente.")
        return

    # Si hay múltiples runs para el mismo modelo+config, conservar solo el más reciente
    seen: dict[tuple, dict] = {}
    for run in runs:
        key = (run["model"], run["config"])
        if key not in seen or run["run_id"] > seen[key]["run_id"]:
            seen[key] = run
    if len(seen) < len(runs):
        print(f"  [!] {len(runs) - len(seen)} run(s) duplicado(s) descartado(s) (se conserva el mas reciente)")
    runs = list(seen.values())

    print(f"\nGenerando reporte con {len(runs)} runs...")
    report = generate_report(runs, args.title)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"✅ Reporte guardado en: {args.output}")


if __name__ == "__main__":
    main()
