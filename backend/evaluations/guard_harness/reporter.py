#!/usr/bin/env python3
"""Genera un reporte markdown comparando corridas del guard_harness.

Compara una corrida pre-fix contra una corrida post-fix y muestra:
  - FP rate y FN rate antes/después (seguridad)
  - Bypass coverage antes/después
  - Severidad J2 de contenido generado (si hay LLM results)
  - FP confirmados por juez J3

Uso (desde backend/ con el venv activo):
    $env:PYTHONPATH="."; python evaluations/guard_harness/reporter.py \\
        --pre  2026-05-17_10-00_llama3.2_pre_fix2 \\
        --post 2026-05-17_15-00_llama3.2_post_fix2 \\
        --output docs/reportes/guard_eval.md

Sin --post: genera reporte de una única corrida (baseline).
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

_HARNESS_DIR = Path(__file__).parent
_RESULTS_DIR = _HARNESS_DIR / "results"
_BACKEND_DIR = _HARNESS_DIR.parent.parent
_DEFAULT_OUTPUT = Path(__file__).resolve().parents[3] / "docs" / "reportes" / "guard_eval.md"


def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else _RESULTS_DIR / path_str


def _load_run(run_dir: Path) -> dict:
    results: dict[str, dict] = {}
    for path in sorted(run_dir.glob("*_result.json")):
        with path.open(encoding="utf-8") as f:
            r = json.load(f)
            results[r["case_id"]] = r

    meta: dict = {}
    summary_path = run_dir / "run_summary.json"
    if summary_path.exists():
        with summary_path.open(encoding="utf-8") as f:
            meta = json.load(f)

    return {"results": results, "meta": meta, "dir": run_dir, "name": run_dir.name}


def _pct(n: int, d: int) -> str:
    return f"{n/d*100:.0f}%" if d else "—"


def _delta(pre: int, post: int, lower_is_better: bool = True) -> str:
    d = post - pre
    if d == 0:
        return "±0"
    sign = "+" if d > 0 else ""
    arrow = ("↓" if d < 0 else "↑") if lower_is_better else ("↑" if d > 0 else "↓")
    return f"{sign}{d} {arrow}"


def _security_stats(run: dict) -> dict:
    """Extract FP/FN stats from adversarial + rpg datasets."""
    adv = [r for r in run["results"].values() if r.get("dataset") == "adversarial"]
    rpg = [r for r in run["results"].values() if r.get("dataset") == "rpg"]

    fn_input  = [r for r in adv if not r.get("input_blocked") and r.get("expected_input_blocked")]
    fn_output = [r for r in adv if r.get("output_correct") is not None
                 and not r.get("output_blocked") and r.get("expected_output_blocked")]
    fp_input  = [r for r in rpg if r.get("input_blocked") and not r.get("expected_input_blocked")]
    fp_output = [r for r in rpg if r.get("output_correct") is not None
                 and r.get("output_blocked") and not r.get("expected_output_blocked")]

    return {
        "adv_total": len(adv),
        "fn_input": fn_input,
        "fn_output": fn_output,
        "rpg_total": len(rpg),
        "fp_input": fp_input,
        "fp_output": fp_output,
    }


def _bypass_stats(run: dict) -> dict:
    byp = [r for r in run["results"].values() if r.get("dataset") == "bypass"]
    active = [r for r in byp if r.get("is_active_bypass")]
    closed = [r for r in byp if r.get("correct") and not r.get("currently_blocked")]
    regressions = [r for r in byp if r.get("currently_blocked") and not r.get("blocked")]
    return {
        "total": len(byp),
        "active_bypasses": active,
        "newly_closed": closed,
        "regressions": regressions,
    }


def _j2_stats(run: dict) -> list[dict]:
    return [
        r for r in run["results"].values()
        if r.get("dataset") == "adversarial"
        and r.get("scores") and r["scores"].get("J2") is not None
    ]


def _j3_stats(run: dict) -> list[dict]:
    return [
        r for r in run["results"].values()
        if r.get("dataset") == "rpg"
        and r.get("scores") and r["scores"].get("J3") is not None
    ]


def generate_report(pre: dict, post: dict | None, title: str) -> str:
    lines: list[str] = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    pre_label = pre["meta"].get("run_tag", pre["name"])
    post_label = post["meta"].get("run_tag", post["name"]) if post else None
    model = pre["meta"].get("model", "?")

    lines += [
        f"# {title}",
        "",
        f"**Generado:** {now}  ",
        f"**Modelo:** `{model}`  ",
        f"**Baseline:** `{pre_label}`  ",
    ]
    if post_label:
        lines += [f"**Post-fix:** `{post_label}`  "]
    lines += ["", "---", ""]

    # ── Resumen de seguridad ───────────────────────────────────────────────────
    pre_sec  = _security_stats(pre)
    post_sec = _security_stats(post) if post else None

    lines += [
        "## Seguridad — FP rate y FN rate",
        "",
    ]

    if post_sec:
        lines += [
            "| Métrica | Pre-fix | Post-fix | Delta |",
            "|---|:---:|:---:|:---:|",
            f"| FN input (dañino no bloqueado)  | {len(pre_sec['fn_input'])}/{pre_sec['adv_total']} | "
            f"{len(post_sec['fn_input'])}/{post_sec['adv_total']} | "
            f"{_delta(len(pre_sec['fn_input']), len(post_sec['fn_input']))} |",
            f"| FN output (dañino generado, no bloqueado) | {len(pre_sec['fn_output'])}/? | "
            f"{len(post_sec['fn_output'])}/? | "
            f"{_delta(len(pre_sec['fn_output']), len(post_sec['fn_output']))} |",
            f"| FP input (RPG bloqueado — Fix #2) | {len(pre_sec['fp_input'])}/{pre_sec['rpg_total']} | "
            f"{len(post_sec['fp_input'])}/{post_sec['rpg_total']} | "
            f"{_delta(len(pre_sec['fp_input']), len(post_sec['fp_input']))} |",
            f"| FP output (RPG generado, bloqueado) | {len(pre_sec['fp_output'])}/? | "
            f"{len(post_sec['fp_output'])}/? | "
            f"{_delta(len(pre_sec['fp_output']), len(post_sec['fp_output']))} |",
        ]
    else:
        lines += [
            "| Métrica | Valor | Total |",
            "|---|:---:|:---:|",
            f"| FN input (dañino no bloqueado) | {len(pre_sec['fn_input'])} | {pre_sec['adv_total']} |",
            f"| FN output (dañino generado, no bloqueado) | {len(pre_sec['fn_output'])} | — |",
            f"| FP input (RPG bloqueado — false positive) | {len(pre_sec['fp_input'])} | {pre_sec['rpg_total']} |",
            f"| FP output (RPG generado, bloqueado) | {len(pre_sec['fp_output'])} | — |",
        ]

    if pre_sec["fn_input"]:
        lines += ["", "**Falsos negativos en input (pre-fix):**", ""]
        for r in pre_sec["fn_input"]:
            lines.append(f"- `{r['case_id']}` fix#{r['fix']}: _{r['user_input'][:80]}_")

    if pre_sec["fp_input"]:
        lines += ["", "**Falsos positivos en input RPG (pre-fix):**", ""]
        for r in pre_sec["fp_input"]:
            lines.append(f"- `{r['case_id']}` fix#{r['fix']}: _{r['query'][:80]}_")

    lines += ["", "---", ""]

    # ── Bypass coverage ────────────────────────────────────────────────────────
    pre_byp  = _bypass_stats(pre)
    post_byp = _bypass_stats(post) if post else None

    lines += ["## Cobertura de bypasses", ""]

    if post_byp:
        lines += [
            "| Métrica | Pre-fix | Post-fix | Delta |",
            "|---|:---:|:---:|:---:|",
            f"| Bypasses activos (sin parchear) | {len(pre_byp['active_bypasses'])}/{pre_byp['total']} | "
            f"{len(post_byp['active_bypasses'])}/{post_byp['total']} | "
            f"{_delta(len(pre_byp['active_bypasses']), len(post_byp['active_bypasses']))} |",
            f"| Bypasses cerrados (nuevos) | — | {len(post_byp['newly_closed'])} | — |",
        ]
        if post_byp["regressions"]:
            lines.append(
                f"| **REGRESIONES** | 0 | {len(post_byp['regressions'])} | ⚠ |"
            )
    else:
        lines += [
            "| Métrica | Valor |",
            "|---|:---:|",
            f"| Total bypass cases | {pre_byp['total']} |",
            f"| Activos (sin parchear) | {len(pre_byp['active_bypasses'])} |",
            f"| Cubiertos por guard actual | {pre_byp['total'] - len(pre_byp['active_bypasses'])} |",
        ]

    if pre_byp["active_bypasses"]:
        lines += ["", "**Bypasses activos pre-fix:**", ""]
        for r in pre_byp["active_bypasses"]:
            technique = r.get("bypass_technique", "")
            lines.append(f"- `{r['case_id']}` fix#{r['fix']}: _{r['user_input'][:60]}_ — {technique[:60]}")

    if post_byp and post_byp["regressions"]:
        lines += ["", "**⚠ REGRESIONES detectadas post-fix:**", ""]
        for r in post_byp["regressions"]:
            lines.append(f"- `{r['case_id']}`: _{r['user_input'][:60]}_")

    lines += ["", "---", ""]

    # ── J2: Severidad de contenido generado ───────────────────────────────────
    pre_j2 = _j2_stats(pre)
    if pre_j2:
        lines += ["## J2 — Severidad de contenido generado (LLM-as-judge)", ""]
        lines += [
            "| Caso | J2 (1–5) | Razón |",
            "|---|:---:|---|",
        ]
        for r in sorted(pre_j2, key=lambda x: x["scores"]["J2"], reverse=True):
            j2_score = r["scores"]["J2"]
            j2_reason = r["scores"].get("J2_reason", "")[:80]
            flag = " ⚠" if j2_score >= 4 else ""
            lines.append(f"| `{r['case_id']}` | {j2_score}{flag} | {j2_reason} |")
        lines += ["", "---", ""]

    # ── J3: Legitimidad RPG ────────────────────────────────────────────────────
    pre_j3 = _j3_stats(pre)
    if pre_j3:
        lines += ["## J3 — Legitimidad RPG (confirmación de falsos positivos)", ""]
        lines += [
            "| Caso | J3 (1–5) | ¿FP confirmado? | Razón |",
            "|---|:---:|:---:|---|",
        ]
        for r in sorted(pre_j3, key=lambda x: x["scores"]["J3"]):
            j3_score = r["scores"]["J3"]
            is_fp = r["scores"].get("is_false_positive", False)
            fp_str = "✅ Sí" if is_fp else "❌ No"
            j3_reason = r["scores"].get("J3_reason", "")[:80]
            lines.append(f"| `{r['case_id']}` | {j3_score} | {fp_str} | {j3_reason} |")
        lines += ["", "---", ""]

    # ── Tabla completa de resultados ──────────────────────────────────────────
    lines += ["## Resultados completos", ""]

    if post:
        lines += [
            "| Caso | Dataset | Fix | Input bloq (pre) | Input bloq (post) | Output bloq (pre) | Output bloq (post) |",
            "|---|---|---|:---:|:---:|:---:|:---:|",
        ]
        all_ids = sorted(set(list(pre["results"].keys()) + list(post["results"].keys())))
        for cid in all_ids:
            r_pre  = pre["results"].get(cid, {})
            r_post = post["results"].get(cid, {})
            ds = r_pre.get("dataset", r_post.get("dataset", "?"))[:3]
            fix = r_pre.get("fix", r_post.get("fix", "?"))

            def _bl(r: dict, field: str) -> str:
                v = r.get(field)
                if v is None:
                    return "—"
                return "🔴" if v else "🟢"

            lines.append(
                f"| `{cid}` | {ds} | #{fix} | "
                f"{_bl(r_pre, 'input_blocked')} | {_bl(r_post, 'input_blocked')} | "
                f"{_bl(r_pre, 'output_blocked')} | {_bl(r_post, 'output_blocked')} |"
            )
    else:
        lines += [
            "| Caso | Dataset | Fix | Input bloq | Exp input | Output bloq | Exp output | Correcto |",
            "|---|---|---|:---:|:---:|:---:|:---:|:---:|",
        ]
        for cid, r in sorted(pre["results"].items()):
            ds = r.get("dataset", "?")[:3]
            fix = r.get("fix", "?")

            def _sym(v: bool | None) -> str:
                if v is None:
                    return "—"
                return "🔴" if v else "🟢"

            inp_bl  = _sym(r.get("input_blocked"))
            exp_inp = _sym(r.get("expected_input_blocked"))
            out_bl  = _sym(r.get("output_blocked"))
            exp_out = _sym(r.get("expected_output_blocked"))

            in_ok  = r.get("input_correct")
            out_ok = r.get("output_correct")
            if in_ok is None and out_ok is None:
                ok = r.get("correct")
            elif in_ok is False or out_ok is False:
                ok = False
            else:
                ok = True
            ok_sym = "✓" if ok else ("✗" if ok is False else "—")

            lines.append(f"| `{cid}` | {ds} | #{fix} | {inp_bl} | {exp_inp} | {out_bl} | {exp_out} | {ok_sym} |")

    lines += ["", "---", ""]

    # ── Resumen ejecutivo ──────────────────────────────────────────────────────
    lines += ["## Resumen ejecutivo", ""]

    if post_sec:
        fp_delta = len(pre_sec["fp_input"]) - len(post_sec["fp_input"])
        fn_delta = len(pre_sec["fn_input"]) - len(post_sec["fn_input"])
        byp_delta = len(pre_byp["active_bypasses"]) - len(post_byp["active_bypasses"])
        lines += [
            f"- Fix #2 redujo FP input de {len(pre_sec['fp_input'])} a {len(post_sec['fp_input'])} ({fp_delta:+d})",
            f"- Fix #2 redujo FN input de {len(pre_sec['fn_input'])} a {len(post_sec['fn_input'])} ({fn_delta:+d})",
            f"- Fix #5/#6 cerró {byp_delta} bypass(es) activos",
        ]
        if post_byp and post_byp["regressions"]:
            lines.append(f"- ⚠ Se introdujeron {len(post_byp['regressions'])} regresiones — revisar antes de merge")
    else:
        lines += [
            f"- Baseline: {len(pre_sec['fn_input'])}/{pre_sec['adv_total']} FN input, "
            f"{len(pre_sec['fp_input'])}/{pre_sec['rpg_total']} FP input",
            f"- Bypasses activos: {len(pre_byp['active_bypasses'])}/{pre_byp['total']}",
            "- Ejecutar post-fix para ver el delta.",
        ]

    lines += [
        "",
        "---",
        "",
        "*Reporte generado automáticamente por `reporter.py` — guard_harness LoreMaster*",
    ]

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Reporte comparativo del guard_harness")
    parser.add_argument("--pre",  required=True, help="Run pre-fix (relativo a results/ o absoluto)")
    parser.add_argument("--post", default=None,  help="Run post-fix (opcional)")
    parser.add_argument(
        "--output",
        type=Path,
        default=_DEFAULT_OUTPUT,
        help="Ruta de salida del reporte markdown",
    )
    parser.add_argument(
        "--title",
        default="Guard Eval — Comparativa Pre/Post Fix",
        help="Título del reporte",
    )
    args = parser.parse_args()

    pre_run = _load_run(_resolve(args.pre))
    post_run = _load_run(_resolve(args.post)) if args.post else None

    report = generate_report(pre=pre_run, post=post_run, title=args.title)

    out_path = args.output if args.output.is_absolute() else _BACKEND_DIR.parent / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"Reporte guardado en: {out_path}")


if __name__ == "__main__":
    main()
