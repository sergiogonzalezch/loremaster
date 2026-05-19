#!/usr/bin/env python3
"""Runner del guard_harness -evaluación de pipeline completa con Ollama.

Ejecuta tres modos de dataset contra la pipeline de moderación:
  adversarial -check_user_input → Ollama → check_generated_output (casos dañinos)
  rpg         -check_user_input → render_prompt → Ollama → check_generated_output (legítimos)
  bypass      -check_user_input con técnicas de evasión (sin LLM)

Guardar resultados en evaluations/guard_harness/results/{run_id}/.

Uso (desde backend/ con el venv activo):
    $env:PYTHONPATH="."; python evaluations/guard_harness/runner.py
    $env:PYTHONPATH="."; python evaluations/guard_harness/runner.py --dataset adversarial --model mistral
    $env:PYTHONPATH="."; python evaluations/guard_harness/runner.py --run-tag post_fix2 --force-llm

Flags:
  --dataset    adversarial | rpg | bypass | all (default: all)
  --model      Modelo Ollama para generación (default: llama3.2)
  --run-tag    Etiqueta para diferenciar corridas pre/post-fix (default: current)
  --force-llm  Enviar adversarial_llm_prompt aunque input sea bloqueado (testa output guard)
  --ollama-url URL base de Ollama (default: http://localhost:11434)

PYTHONPATH debe apuntar a backend/ para que las importaciones de app.* funcionen.
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
import yaml

_HARNESS_DIR = Path(__file__).parent
_BACKEND_DIR = _HARNESS_DIR.parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

from app.core.exceptions import ContentNotAllowedError, GeneratedContentBlockedError
from app.domain.content_guard import check_generated_output, check_user_input
from app.domain.prompt_templates import render_prompt
from app.models.enums import ContentCategory

_DATASET_DIR = _HARNESS_DIR / "dataset"
_RESULTS_DIR = _HARNESS_DIR / "results"

_DATASET_FILES = {
    "adversarial": _DATASET_DIR / "adversarial_inputs.yaml",
    "rpg":         _DATASET_DIR / "rpg_legitimate.yaml",
    "bypass":      _DATASET_DIR / "bypass_attempts.yaml",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_dataset(name: str) -> list[dict]:
    path = _DATASET_FILES[name]
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("cases", [])


def _call_ollama(prompt: str, model: str, ollama_url: str) -> tuple[str, float]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 1024},
    }
    start = time.time()
    response = requests.post(f"{ollama_url}/api/generate", json=payload, timeout=300)
    response.raise_for_status()
    return response.json()["response"], time.time() - start


def _build_context(fragments: list[str]) -> str:
    return "\n\n".join(f"[{i + 1}] {fragment}" for i, fragment in enumerate(fragments))


def _guard_input(text: str) -> tuple[bool, str | None]:
    """Returns (blocked, snippet_if_blocked)."""
    try:
        check_user_input(text)
        return False, None
    except ContentNotAllowedError as exc:
        return True, str(exc)[:200]


def _guard_output(text: str) -> tuple[bool, str | None]:
    """Returns (blocked, snippet_if_blocked)."""
    try:
        check_generated_output(text)
        return False, None
    except GeneratedContentBlockedError as exc:
        return True, str(exc)[:200]


def _save_result(out_dir: Path, case_id: str, result: dict) -> None:
    path = out_dir / f"{case_id.lower()}_result.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def _print_status(case_id: str, fix: str, input_correct: bool, output_correct: bool | None) -> None:
    i_sym = "OK" if input_correct else "XX"
    if output_correct is None:
        o_sym = "--"
    else:
        o_sym = "OK" if output_correct else "XX"
    status = "PASS" if input_correct and (output_correct is None or output_correct) else "FAIL"
    print(f"  {case_id:<14} fix#{fix}  input:{i_sym}  output:{o_sym}  [{status}]")


# ── Dataset runners ───────────────────────────────────────────────────────────

def run_adversarial(
    cases: list[dict],
    out_dir: Path,
    model: str,
    ollama_url: str,
    force_llm: bool,
    run_id: str,
) -> list[dict]:
    summary_rows = []

    for case in cases:
        case_id: str = case["id"]
        user_input: str = case["user_input"]
        adv_prompt: str = case.get("adversarial_llm_prompt", "")
        exp_in: bool = case["expected_input_blocked"]
        exp_out: bool = case["expected_output_blocked"]

        input_blocked, input_snippet = _guard_input(user_input)
        input_correct = input_blocked == exp_in

        llm_response = None
        output_blocked = None
        output_snippet = None
        output_correct = None
        response_time = None
        error = None

        should_call_llm = adv_prompt and (force_llm or not input_blocked)
        if should_call_llm:
            try:
                llm_response, response_time = _call_ollama(adv_prompt, model, ollama_url)
                output_blocked, output_snippet = _guard_output(llm_response)
                output_correct = output_blocked == exp_out
            except Exception as exc:
                error = str(exc)

        result = {
            "run_id": run_id,
            "dataset": "adversarial",
            "case_id": case_id,
            "fix": case["fix"],
            "group": case["group"],
            "model": model,
            "user_input": user_input,
            "input_blocked": input_blocked,
            "input_snippet": input_snippet,
            "expected_input_blocked": exp_in,
            "input_correct": input_correct,
            "adversarial_llm_prompt": adv_prompt,
            "llm_response": llm_response,
            "output_blocked": output_blocked,
            "output_snippet": output_snippet,
            "expected_output_blocked": exp_out,
            "output_correct": output_correct,
            "response_time_sec": round(response_time, 2) if response_time else None,
            "error": error,
            "scores": None,
        }
        _save_result(out_dir, case_id, result)
        _print_status(case_id, case["fix"], input_correct, output_correct)
        summary_rows.append(result)

    return summary_rows


def run_rpg(
    cases: list[dict],
    out_dir: Path,
    model: str,
    ollama_url: str,
    run_id: str,
) -> list[dict]:
    summary_rows = []

    for case in cases:
        case_id: str = case["id"]
        query: str = case["query"]
        exp_in: bool = case["expected_input_blocked"]
        exp_out: bool = case["expected_output_blocked"]

        input_blocked, input_snippet = _guard_input(query)
        input_correct = input_blocked == exp_in

        llm_response = None
        output_blocked = None
        output_snippet = None
        output_correct = None
        response_time = None
        error = None

        if not input_blocked:
            try:
                context = _build_context(case["simulated_context"])
                category = ContentCategory(case["category"])
                full_prompt = render_prompt(
                    category=category,
                    entity_name=case["entity_name"],
                    entity_type=case["entity_type"],
                    context=context,
                    query=query,
                )
                llm_response, response_time = _call_ollama(full_prompt, model, ollama_url)
                output_blocked, output_snippet = _guard_output(llm_response)
                output_correct = output_blocked == exp_out
            except Exception as exc:
                error = str(exc)

        result = {
            "run_id": run_id,
            "dataset": "rpg",
            "case_id": case_id,
            "fix": case["fix"],
            "group": case["group"],
            "model": model,
            "category": case["category"],
            "entity_name": case["entity_name"],
            "entity_type": case["entity_type"],
            "query": query,
            "input_blocked": input_blocked,
            "input_snippet": input_snippet,
            "expected_input_blocked": exp_in,
            "input_correct": input_correct,
            "llm_response": llm_response,
            "output_blocked": output_blocked,
            "output_snippet": output_snippet,
            "expected_output_blocked": exp_out,
            "output_correct": output_correct,
            "response_time_sec": round(response_time, 2) if response_time else None,
            "error": error,
            "scores": None,
        }
        _save_result(out_dir, case_id, result)
        _print_status(case_id, case["fix"], input_correct, output_correct)
        summary_rows.append(result)

    return summary_rows


def run_bypass(
    cases: list[dict],
    out_dir: Path,
    run_id: str,
) -> list[dict]:
    summary_rows = []

    for case in cases:
        case_id: str = case["id"]
        user_input: str = case["user_input"]
        guard_fn_name: str = case["guard_fn"]
        exp_blocked: bool = case["expected_blocked"]
        currently_blocked: bool = case["currently_blocked"]

        if guard_fn_name == "check_user_input":
            blocked, snippet = _guard_input(user_input)
        else:
            blocked, snippet = _guard_output(user_input)

        correct = blocked == exp_blocked
        is_active_bypass = not currently_blocked and not blocked

        result = {
            "run_id": run_id,
            "dataset": "bypass",
            "case_id": case_id,
            "fix": case["fix"],
            "group": case["group"],
            "guard_fn": guard_fn_name,
            "user_input": user_input,
            "blocked": blocked,
            "snippet": snippet,
            "expected_blocked": exp_blocked,
            "currently_blocked": currently_blocked,
            "correct": correct,
            "is_active_bypass": is_active_bypass,
            "bypass_technique": case.get("bypass_technique", ""),
            "error": None,
            "scores": None,
        }
        _save_result(out_dir, case_id, result)

        sym = "OK" if correct else "XX"
        bypass_flag = "  <- BYPASS ACTIVO" if is_active_bypass else ""
        print(f"  {case_id:<14} fix#{case['fix']}  blocked:{str(blocked):<5} [{sym}]{bypass_flag}")

        summary_rows.append(result)

    return summary_rows


# ── Main ──────────────────────────────────────────────────────────────────────

def _print_section(title: str) -> None:
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Guard Harness Runner -evaluación de pipeline con Ollama"
    )
    parser.add_argument(
        "--dataset",
        choices=["adversarial", "rpg", "bypass", "all"],
        default="all",
        help="Dataset a ejecutar (default: all)",
    )
    parser.add_argument(
        "--model",
        default="llama3.2",
        help="Modelo Ollama para generación (default: llama3.2)",
    )
    parser.add_argument(
        "--run-tag",
        default="current",
        help="Etiqueta de la corrida -usar 'pre_fix2', 'post_fix2', etc. (default: current)",
    )
    parser.add_argument(
        "--force-llm",
        action="store_true",
        help="Enviar adversarial_llm_prompt aunque input guard bloquee (testa output guard en aislamiento)",
    )
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="URL base de Ollama (default: http://localhost:11434)",
    )
    args = parser.parse_args()

    run_id = f"{datetime.now().strftime('%Y-%m-%d_%H-%M')}_{args.model}_{args.run_tag}"
    out_dir = _RESULTS_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    do_adv    = args.dataset in ("adversarial", "all")
    do_rpg    = args.dataset in ("rpg", "all")
    do_bypass = args.dataset in ("bypass", "all")

    all_results: list[dict] = []

    if do_adv:
        _print_section("ADVERSARIAL -- check_user_input -> Ollama -> check_generated_output")
        cases = _load_dataset("adversarial")
        print(f"  Modelo: {args.model}  |  force_llm: {args.force_llm}  |  casos: {len(cases)}")
        print()
        all_results += run_adversarial(cases, out_dir, args.model, args.ollama_url, args.force_llm, run_id)

    if do_rpg:
        _print_section("RPG LEGITIMO -- check_user_input -> render_prompt -> Ollama -> check_generated_output")
        cases = _load_dataset("rpg")
        print(f"  Modelo: {args.model}  |  casos: {len(cases)}")
        print()
        all_results += run_rpg(cases, out_dir, args.model, args.ollama_url, run_id)

    if do_bypass:
        _print_section("BYPASS -check_user_input (sin LLM)")
        cases = _load_dataset("bypass")
        print(f"  casos: {len(cases)}")
        print()
        all_results += run_bypass(cases, out_dir, run_id)

    # ── Resumen ───────────────────────────────────────────────────────────────
    total = len(all_results)
    errors = sum(1 for r in all_results if r.get("error"))

    adv_results = [r for r in all_results if r["dataset"] == "adversarial"]
    rpg_results = [r for r in all_results if r["dataset"] == "rpg"]
    byp_results = [r for r in all_results if r["dataset"] == "bypass"]

    print()
    print("=" * 70)
    print("  RESUMEN")
    print("=" * 70)

    if adv_results:
        in_correct  = sum(1 for r in adv_results if r["input_correct"])
        out_tested  = [r for r in adv_results if r["output_correct"] is not None]
        out_correct = sum(1 for r in out_tested if r["output_correct"])
        fn_input    = [r for r in adv_results if not r["input_blocked"] and r["expected_input_blocked"]]
        fn_output   = [r for r in out_tested if not r["output_blocked"] and r["expected_output_blocked"]]
        print(f"  Adversarial  : {in_correct}/{len(adv_results)} input correcto")
        if out_tested:
            print(f"                 {out_correct}/{len(out_tested)} output correcto (de los que se llamó LLM)")
        if fn_input:
            print(f"  FN input     : {len(fn_input)} -{', '.join(r['case_id'] for r in fn_input)}")
        if fn_output:
            print(f"  FN output    : {len(fn_output)} -{', '.join(r['case_id'] for r in fn_output)}")

    if rpg_results:
        in_correct  = sum(1 for r in rpg_results if r["input_correct"])
        fp_input    = [r for r in rpg_results if r["input_blocked"] and not r["expected_input_blocked"]]
        out_tested  = [r for r in rpg_results if r["output_correct"] is not None]
        fp_output   = [r for r in out_tested if r["output_blocked"] and not r["expected_output_blocked"]]
        print(f"  RPG legítimo : {in_correct}/{len(rpg_results)} input correcto")
        if fp_input:
            print(f"  FP input     : {len(fp_input)} -{', '.join(r['case_id'] for r in fp_input)}")
        if fp_output:
            print(f"  FP output    : {len(fp_output)} -{', '.join(r['case_id'] for r in fp_output)}")

    if byp_results:
        correct       = sum(1 for r in byp_results if r["correct"])
        active_bypass = [r for r in byp_results if r["is_active_bypass"]]
        fixed         = [r for r in byp_results if r["correct"] and not r["currently_blocked"]]
        print(f"  Bypass       : {correct}/{len(byp_results)} correcto")
        if active_bypass:
            print(f"  Activos      : {len(active_bypass)} bypass sin parchear")
        if fixed:
            print(f"  Cerrados     : {len(fixed)} bypass cerrados por fix")

    if errors:
        print(f"  Errores      : {errors} (ver result JSONs)")

    summary = {
        "run_id": run_id,
        "model": args.model,
        "run_tag": args.run_tag,
        "force_llm": args.force_llm,
        "total_cases": total,
        "errors": errors,
        "results_dir": str(out_dir),
    }
    (out_dir / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n  Resultados en: {out_dir}")


if __name__ == "__main__":
    main()
