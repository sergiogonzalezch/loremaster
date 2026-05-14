#!/usr/bin/env python3
"""Compara dos corridas del harness de evaluación de prompts.

Calcula deltas por dimensión y por categoría, y aplica los criterios
de validación del refactor definidos en docs/PHASE-1.md.

Uso (desde backend/ con el venv activo):
    python evaluations/prompt_harness/compare.py \\
        --baseline 2026-05-13_llama3.2_current_0.7 \\
        --target   2026-05-14_llama3.2_refactored_0.7
"""

import argparse
import json
from pathlib import Path

_HARNESS_DIR = Path(__file__).parent
_RESULTS_DIR = _HARNESS_DIR / "results"

_DIMENSIONS = ("D1", "D2", "D3", "D4")
_DIM_NAMES = {
    "D1": "Adherencia al contexto",
    "D2": "Especificidad narrativa",
    "D3": "Cumplimiento de categoría",
    "D4": "Completitud",
}
# D3 debe mejorar al menos 0.3 para validar el refactor (ver PHASE-1.md)
_D3_THRESHOLD = 0.3
# Casos que prueban la Regla 3 (fallback con contexto pobre)
_SPARSE_CASES = {"TC-04", "TC-05"}


def _load_results(run_dir: Path) -> dict[str, dict]:
    results = {}
    for path in run_dir.glob("tc_*_result.json"):
        with path.open(encoding="utf-8") as f:
            r = json.load(f)
            results[r["tc_id"]] = r
    return results


def _avg_dim(results: dict, dim: str) -> float | None:
    scores = [
        r["scores"][dim]
        for r in results.values()
        if r.get("scores") and dim in r["scores"]
    ]
    return round(sum(scores) / len(scores), 2) if scores else None


def _avg_dim_by_category(results: dict, dim: str) -> dict[str, float]:
    by_cat: dict[str, list] = {}
    for r in results.values():
        if not r.get("scores"):
            continue
        cat = r.get("category", "unknown")
        by_cat.setdefault(cat, []).append(r["scores"][dim])
    return {cat: round(sum(v) / len(v), 2) for cat, v in sorted(by_cat.items())}


def _rejection_count(results: dict, tc_ids: set) -> int:
    return sum(1 for tc_id, r in results.items() if tc_id in tc_ids and r.get("rejected"))


def _fmt(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else " N/A"


def _delta_str(base: float | None, tgt: float | None) -> str:
    if base is None or tgt is None:
        return "N/A"
    diff = tgt - base
    sign = "+" if diff >= 0 else ""
    return f"{sign}{diff:.2f}"


def _load_summary(run_dir: Path) -> dict:
    path = run_dir / "run_summary.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Comparativa entre corridas del harness LoreMaster")
    parser.add_argument("--baseline", required=True, help="Directorio baseline (relativo a results/ o absoluto)")
    parser.add_argument("--target", required=True, help="Directorio target (relativo a results/ o absoluto)")
    args = parser.parse_args()

    def _resolve(path_str: str) -> Path:
        p = Path(path_str)
        return p if p.is_absolute() else _RESULTS_DIR / path_str

    baseline_dir = _resolve(args.baseline)
    target_dir = _resolve(args.target)

    baseline = _load_results(baseline_dir)
    target = _load_results(target_dir)

    if not baseline:
        print(f"Sin resultados en baseline: {baseline_dir}")
        return
    if not target:
        print(f"Sin resultados en target: {target_dir}")
        return

    base_meta = _load_summary(baseline_dir)
    tgt_meta = _load_summary(target_dir)

    print(f"\n{'=' * 65}")
    print(f"COMPARATIVA: {base_meta.get('prompt_version', 'baseline')} → {tgt_meta.get('prompt_version', 'target')}")
    print(f"  Baseline : modelo={base_meta.get('model', '?')}  temp={base_meta.get('temperature', '?')}")
    print(f"  Target   : modelo={tgt_meta.get('model', '?')}  temp={tgt_meta.get('temperature', '?')}")
    print(f"{'=' * 65}")

    # --- Por dimensión ---
    print("\nPor dimensión (promedio global):")
    dim_results: dict[str, dict] = {}
    for dim in _DIMENSIONS:
        b = _avg_dim(baseline, dim)
        t = _avg_dim(target, dim)
        delta = _delta_str(b, t)
        note = ""
        if dim == "D3" and b is not None and t is not None:
            passes = (t - b) >= _D3_THRESHOLD
            note = "  ✓ umbral" if passes else "  ✗ umbral"
            dim_results["D3_ok"] = passes
        print(f"  {dim} {_DIM_NAMES[dim]:<30} {_fmt(b)} → {_fmt(t)}  ({delta}){note}")
        dim_results[dim] = {"base": b, "target": t}

    # --- Por categoría (D3) ---
    print("\nPor categoría — D3 cumplimiento:")
    base_by_cat = _avg_dim_by_category(baseline, "D3")
    tgt_by_cat = _avg_dim_by_category(target, "D3")
    all_cats = sorted(set(base_by_cat) | set(tgt_by_cat))
    for cat in all_cats:
        b = base_by_cat.get(cat)
        t = tgt_by_cat.get(cat)
        print(f"  {cat:<25} {_fmt(b)} → {_fmt(t)}  ({_delta_str(b, t)})")

    # --- Regla 3: rechazos en contexto pobre ---
    base_rej = _rejection_count(baseline, _SPARSE_CASES)
    tgt_rej = _rejection_count(target, _SPARSE_CASES)
    rule3_ok = tgt_rej == 0
    print("\nRegla 3 — rechazos en TC-04/TC-05:")
    print(f"  Baseline: {base_rej}  →  Target: {tgt_rej}  {'✓' if rule3_ok else '✗'}")

    # --- Criterios de validación ---
    d1_b = dim_results.get("D1", {}).get("base")
    d1_t = dim_results.get("D1", {}).get("target")
    d1_ok = d1_t is None or d1_b is None or d1_t >= d1_b
    d3_ok = dim_results.get("D3_ok", False)

    print("\nCriterios de validación del refactor (ver PHASE-1.md):")
    print(f"  D3 mejora ≥ {_D3_THRESHOLD}:            {'✓' if d3_ok else '✗'}")
    print(f"  D1 no empeora:              {'✓' if d1_ok else '✗'}")
    print(f"  TC-04/TC-05 sin rechazos:   {'✓' if rule3_ok else '✗'}")

    if d3_ok and d1_ok and rule3_ok:
        print("\n  → REFACTOR VALIDADO")
    else:
        print("\n  → REFACTOR PENDIENTE DE REVISIÓN")
    print()


if __name__ == "__main__":
    main()
