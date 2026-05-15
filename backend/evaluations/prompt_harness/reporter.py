#!/usr/bin/env python3
"""Genera un reporte markdown comparando múltiples corridas del harness.

Uso (desde backend/ con el venv activo):
    python evaluations/prompt_harness/reporter.py \\
        --runs run1 run2 run3 \\
        --baseline run1 \\
        --output docs/phase2-model-comparison.md \\
        --title "Phase 2 — Comparativa de Modelos"
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

_HARNESS_DIR = Path(__file__).parent
_RESULTS_DIR = _HARNESS_DIR / "results"
_BACKEND_DIR = _HARNESS_DIR.parent.parent

_DIMENSIONS = ("D1", "D2", "D3", "D4")
_DIM_NAMES = {
    "D1": "Adherencia al contexto",
    "D2": "Especificidad narrativa",
    "D3": "Cumplimiento de categoría",
    "D4": "Completitud",
}
_SWITCH_THRESHOLD = 0.5


def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else _RESULTS_DIR / path_str


def _load_run(run_dir: Path) -> dict:
    results = {}
    for path in sorted(run_dir.glob("tc*_result.json")):
        with path.open(encoding="utf-8") as f:
            r = json.load(f)
            results[r["tc_id"]] = r

    summary_path = run_dir / "run_summary.json"
    meta = {}
    if summary_path.exists():
        with summary_path.open(encoding="utf-8") as f:
            meta = json.load(f)

    return {"results": results, "meta": meta, "dir": run_dir}


def _model_label(run: dict) -> str:
    meta = run["meta"]
    model = meta.get("model", "?")
    temp = meta.get("temperature", "?")
    return f"{model} (t={temp})"


def _avg(values: list) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def _dim_avg(run: dict, dim: str) -> float | None:
    scores = [
        r["scores"][dim]
        for r in run["results"].values()
        if r.get("scores") and dim in r["scores"]
    ]
    return _avg(scores)


def _category_avg(run: dict, dim: str) -> dict[str, float]:
    by_cat: dict[str, list] = {}
    for r in run["results"].values():
        s = r.get("scores")
        if not s or dim not in s:
            continue
        cat = r.get("category", "unknown")
        by_cat.setdefault(cat, []).append(s[dim])
    return {cat: _avg(vals) for cat, vals in sorted(by_cat.items())}


def _response_stats(run: dict) -> dict:
    times = [
        r["response_time_sec"]
        for r in run["results"].values()
        if r.get("response_time_sec") is not None
    ]
    if not times:
        return {"avg": None, "min": None, "max": None}
    return {
        "avg": round(sum(times) / len(times), 1),
        "min": round(min(times), 1),
        "max": round(max(times), 1),
    }


def _rejection_count(run: dict) -> int:
    return sum(1 for r in run["results"].values() if r.get("rejected"))


def _fmt(v: float | None) -> str:
    return f"{v:.2f}" if v is not None else "N/A"


def generate_report(
    runs: list[dict],
    labels: list[str],
    baseline_idx: int,
    title: str,
    judge_model: str,
) -> str:
    lines: list[str] = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    baseline = runs[baseline_idx]
    baseline_label = labels[baseline_idx]

    all_cats = sorted({
        r.get("category", "unknown")
        for run in runs
        for r in run["results"].values()
    })
    all_tc_ids = sorted({tc for run in runs for tc in run["results"]})

    # ── Encabezado ─────────────────────────────────────────────────────────────
    lines += [
        f"# {title}",
        "",
        f"**Generado:** {now}  ",
        f"**Juez:** `{judge_model}`  ",
        f"**Baseline:** `{baseline_label}`  ",
        f"**Umbral de switch:** ≥ {_SWITCH_THRESHOLD} puntos de diferencia en D3 por categoría",
        "",
        "---",
        "",
    ]

    # ── Ranking global ──────────────────────────────────────────────────────────
    lines += [
        "## Ranking global",
        "",
        "| Modelo | Rechazos | D1 | D2 | D3 | D4 | Promedio |",
        "|---|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]

    rows = []
    for run, label in zip(runs, labels, strict=False):
        rejected = _rejection_count(run)
        dim_avgs = {d: _dim_avg(run, d) for d in _DIMENSIONS}
        valid = [v for v in dim_avgs.values() if v is not None]
        overall = _avg(valid) if valid else None
        rows.append((label, rejected, dim_avgs, overall))

    rows.sort(key=lambda x: x[3] or 0, reverse=True)
    winner_label = rows[0][0]

    for label, rejected, dim_avgs, overall in rows:
        bold = "**" if label == winner_label else ""
        rej_str = f"{rejected}/10" if rejected > 0 else "0/10"
        lines.append(
            f"| {bold}`{label}`{bold} | {rej_str} | {_fmt(dim_avgs['D1'])} | "
            f"{_fmt(dim_avgs['D2'])} | {_fmt(dim_avgs['D3'])} | {_fmt(dim_avgs['D4'])} | "
            f"{bold}{_fmt(overall)}{bold} |"
        )

    lines += ["", "---", ""]

    # ── D3 por categoría ────────────────────────────────────────────────────────
    lines += [
        "## D3 — Cumplimiento de categoría por modelo",
        "",
        "| Categoría | " + " | ".join(f"`{lbl}`" for lbl in labels) + " | Mejor |",
        "|---|" + ":---:|" * len(labels) + ":---|",
    ]

    for cat in all_cats:
        cat_scores = []
        best_score = -1.0
        best_label = "N/A"
        for run, label in zip(runs, labels, strict=False):
            score = _category_avg(run, "D3").get(cat)
            cat_scores.append(_fmt(score))
            if score is not None and score > best_score:
                best_score = score
                best_label = label

        base_cat = _category_avg(baseline, "D3").get(cat) or 0
        delta = best_score - base_cat if best_score >= 0 else 0
        flag = " ⚡" if delta >= _SWITCH_THRESHOLD and best_label != baseline_label else ""
        lines.append(
            f"| `{cat}` | " + " | ".join(cat_scores) + f" | `{best_label}`{flag} |"
        )

    lines += ["", "---", ""]

    # ── Tiempos de respuesta ────────────────────────────────────────────────────
    lines += [
        "## Tiempos de respuesta",
        "",
        "| Modelo | Promedio (s) | Mínimo (s) | Máximo (s) |",
        "|---|:---:|:---:|:---:|",
    ]
    for run, label in zip(runs, labels, strict=False):
        st = _response_stats(run)
        lines.append(f"| `{label}` | {st['avg']} | {st['min']} | {st['max']} |")

    lines += ["", "---", ""]

    # ── Scores por caso ─────────────────────────────────────────────────────────
    lines += [
        "## Scores por caso (D1 / D2 / D3 / D4)",
        "",
        "| TC | Categoría | Ctx | " + " | ".join(f"`{lbl}`" for lbl in labels) + " |",
        "|---|---|---|" + "---|" * len(labels),
    ]

    for tc_id in all_tc_ids:
        tc_info = next(
            (run["results"][tc_id] for run in runs if tc_id in run["results"]), {}
        )
        cat = tc_info.get("category", "?")[:8]
        ctx = tc_info.get("context_quality", "?")[:8]

        cells = []
        for run in runs:
            r = run["results"].get(tc_id, {})
            s = r.get("scores") or {}
            if r.get("rejected") and not s:
                cells.append("RECHAZADO")
            elif s:
                rej = "⚠" if r.get("rejected") else ""
                cells.append(f"{s.get('D1','?')}/{s.get('D2','?')}/{s.get('D3','?')}/{s.get('D4','?')}{rej}")
            else:
                cells.append("—")

        lines.append(f"| {tc_id} | {cat} | {ctx} | " + " | ".join(cells) + " |")

    lines += ["", "---", ""]

    # ── Decisión de switch ──────────────────────────────────────────────────────
    lines += [
        "## Decisión de switch por categoría",
        "",
        f"Umbral: el mejor modelo alternativo debe superar al baseline en **≥ {_SWITCH_THRESHOLD}** puntos de D3.",
        "",
        "| Categoría | Baseline D3 | Mejor alternativo | Delta D3 | ¿Switch? |",
        "|---|:---:|---|:---:|:---:|",
    ]

    switch_recommendations: list[tuple[str, str]] = []

    for cat in all_cats:
        base_score = _category_avg(baseline, "D3").get(cat)
        best_alt_score = -1.0
        best_alt_label = "N/A"
        for run, label in zip(runs, labels, strict=False):
            if label == baseline_label:
                continue
            score = _category_avg(run, "D3").get(cat)
            if score is not None and score > best_alt_score:
                best_alt_score = score
                best_alt_label = label

        if best_alt_score < 0:
            delta_str = "N/A"
            switch_str = "—"
        else:
            delta = best_alt_score - (base_score or 0)
            sign = "+" if delta >= 0 else ""
            delta_str = f"{sign}{delta:.2f}"
            if delta >= _SWITCH_THRESHOLD:
                switch_str = "✅ Sí"
                switch_recommendations.append((cat, best_alt_label))
            else:
                switch_str = "❌ No"

        lines.append(
            f"| `{cat}` | {_fmt(base_score)} | `{best_alt_label}` ({_fmt(best_alt_score if best_alt_score >= 0 else None)}) "
            f"| {delta_str} | {switch_str} |"
        )

    lines += ["", "---", ""]

    # ── Resumen ejecutivo ───────────────────────────────────────────────────────
    lines += [
        "## Resumen y próximos pasos",
        "",
        f"**Modelo ganador overall:** `{winner_label}`",
        "",
    ]

    if switch_recommendations:
        lines.append(f"**Categorías con switch recomendado (delta ≥ {_SWITCH_THRESHOLD}):**")
        lines.append("")
        for cat, model in switch_recommendations:
            lines.append(f"- `{cat}` → usar `{model}`")
        lines.append("")
        lines += [
            "**Próximo paso:** implementar `ollama_model_overrides` en Settings y `get_llm()` factory",
            "en `llm.py` para activar el switch por categoría (ver diseño en `docs/PHASE-2.md`).",
        ]
    else:
        lines += [
            f"**Ninguna categoría supera el umbral de {_SWITCH_THRESHOLD} puntos.** El switch per-categoría",
            "no está justificado con los datos actuales. Se recomienda mantener el modelo baseline",
            f"(`{baseline_label}`) o migrar globalmente a `{winner_label}` si el delta overall lo justifica.",
        ]

    lines += [
        "",
        "---",
        "",
        "*Reporte generado automáticamente por `reporter.py` — harness LoreMaster*",
    ]

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera reporte markdown comparativo del harness LoreMaster")
    parser.add_argument(
        "--runs",
        nargs="+",
        required=True,
        help="Directorios de runs (relativos a results/ o rutas absolutas)",
    )
    parser.add_argument(
        "--baseline",
        default=None,
        help="Run baseline para deltas (por defecto: el primero de --runs)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Ruta del reporte de salida (relativa a la raíz del repo, o absoluta). Sin valor: imprime a stdout.",
    )
    parser.add_argument(
        "--title",
        default="Comparativa de Modelos — Harness LoreMaster",
        help="Título del reporte",
    )
    parser.add_argument(
        "--judge-model",
        default="gemma2:9b",
        help="Modelo juez usado (solo metadata, default: gemma2:9b)",
    )
    args = parser.parse_args()

    runs = [_load_run(_resolve(r)) for r in args.runs]
    labels = [_model_label(run) for run in runs]

    baseline_idx = 0
    if args.baseline:
        baseline_resolved = _resolve(args.baseline)
        for i, run in enumerate(runs):
            if run["dir"] == baseline_resolved or run["dir"].name == args.baseline:
                baseline_idx = i
                break

    report = generate_report(
        runs=runs,
        labels=labels,
        baseline_idx=baseline_idx,
        title=args.title,
        judge_model=args.judge_model,
    )

    if args.output:
        out_path = Path(args.output)
        if not out_path.is_absolute():
            out_path = _BACKEND_DIR.parent / args.output
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        print(f"Reporte guardado en: {out_path}")
    else:
        print(report)


if __name__ == "__main__":
    main()
