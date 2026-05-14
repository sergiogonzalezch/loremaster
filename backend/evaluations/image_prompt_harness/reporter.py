#!/usr/bin/env python3
"""Genera un informe markdown comparando resultados de múltiples modelos.

Uso (desde backend/ con el venv activo):
    python evaluations/image_prompt_harness/reporter.py
"""

import json
from pathlib import Path

_RESULTS_DIR = Path(__file__).parent / "results"


def _load_summaries() -> list[dict]:
    summaries = []
    for path in sorted(_RESULTS_DIR.glob("*/run_summary.json")):
        with path.open(encoding="utf-8") as f:
            summaries.append(json.load(f))
    return summaries


def generate_report(summaries: list[dict]) -> str:
    lines = [
        "# Image Prompt Harness — Comparativa por modelo",
        "",
        "Métricas evaluadas sobre el output de `build_combined_prompt()`:",
        "",
        "| Criterio | Descripción |",
        "| --- | --- |",
        "| **Tipo correcto** | El primer token del output coincide con el tipo de entidad esperado |",
        "| **En inglés** | El output no contiene palabras función ni colores en español |",
        "",
        "## Resultados",
        "",
        "| Modelo | Temp | Tipo correcto | En inglés |",
        "| --- | --- | --- | --- |",
    ]

    for s in summaries:
        total = s.get("total_cases", 1)
        lines.append(
            f"| {s['model']} "
            f"| {s.get('temperature', '—')} "
            f"| {s['tipo_correct']}/{total} ({s['tipo_pct']}%) "
            f"| {s['english_correct']}/{total} ({s['english_pct']}%) |"
        )

    lines += [
        "",
        "## Detalle por caso",
        "",
    ]

    for s in summaries:
        lines.append(f"### {s['model']} (temp={s.get('temperature', '—')})")
        lines.append("")
        lines.append("| Caso | Tipo | Inglés | Error |")
        lines.append("| --- | --- | --- | --- |")
        for r in s.get("results", []):
            tipo = "✓" if r["tipo_ok"] else "✗"
            english = "✓" if r["english_ok"] else "✗"
            error = r["error"] or "—"
            lines.append(f"| {r['tc_id']} | {tipo} | {english} | {error} |")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    summaries = _load_summaries()
    if not summaries:
        print("No hay resultados. Ejecuta runner.py primero.")
        return

    report = generate_report(summaries)
    out_path = _RESULTS_DIR / "comparison_report.md"
    out_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nReporte guardado en {out_path}")


if __name__ == "__main__":
    main()
