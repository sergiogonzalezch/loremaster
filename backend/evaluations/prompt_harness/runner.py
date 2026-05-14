#!/usr/bin/env python3
"""Runner del harness de evaluación de prompts.

Ejecuta los 10 test cases contra Ollama usando render_prompt() del código de producción.
Los resultados se guardan en evaluations/prompt_harness/results/{run_id}/.

Uso (desde backend/ con el venv activo):
    python evaluations/prompt_harness/runner.py
    python evaluations/prompt_harness/runner.py --model qwen3 --prompt-version refactored --temperature 0.5

IMPORTANTE: el flag --prompt-version es solo una etiqueta de metadata. El comportamiento
real del prompt depende del código actualmente cargado. Ejecuta el baseline ANTES de
aplicar el refactor, y la corrida "refactored" DESPUÉS.
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

from app.domain.prompt_templates import render_prompt  # noqa: E402
from app.models.enums import ContentCategory  # noqa: E402

_TEST_CASES_DIR = _HARNESS_DIR / "test_cases"
_RESULTS_DIR = _HARNESS_DIR / "results"
_REJECTION_MARKER = "No puedo procesar esta solicitud"


def _load_test_cases() -> list[dict]:
    cases = []
    for path in sorted(_TEST_CASES_DIR.glob("*.yaml")):
        with path.open(encoding="utf-8") as f:
            cases.append(yaml.safe_load(f))
    return cases


def _build_context(fragments: list[str]) -> str:
    return "\n\n".join(f"[{i + 1}] {fragment}" for i, fragment in enumerate(fragments))


def _call_ollama(prompt: str, model: str, temperature: float, base_url: str) -> tuple[str, float]:
    url = f"{base_url}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": 2048},
    }
    start = time.time()
    response = requests.post(url, json=payload, timeout=300)
    response.raise_for_status()
    elapsed = time.time() - start
    return response.json()["response"], elapsed


def run(model: str, prompt_version: str, temperature: float, ollama_url: str) -> None:
    run_id = f"{datetime.now().strftime('%Y-%m-%d_%H-%M')}_{model}_{prompt_version}_{temperature}"
    out_dir = _RESULTS_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    test_cases = _load_test_cases()
    summary: dict = {
        "run_id": run_id,
        "model": model,
        "prompt_version": prompt_version,
        "temperature": temperature,
        "results": [],
    }

    print(f"\nRun: {run_id}")
    print(f"Test cases: {len(test_cases)}\n")

    for tc in test_cases:
        tc_id = tc["id"]
        print(f"  {tc_id}: {tc['name'][:55]} ... ", end="", flush=True)

        context = _build_context(tc["simulated_context"])
        category = ContentCategory(tc["category"])

        prompt = render_prompt(
            category=category,
            entity_name=tc["entity_name"],
            entity_type=tc["entity_type"],
            context=context,
            query=tc["query"],
        )

        try:
            output, elapsed = _call_ollama(prompt, model, temperature, ollama_url)
            rejected = _REJECTION_MARKER in output
            error = None
        except Exception as exc:
            output = ""
            elapsed = 0.0
            rejected = False
            error = str(exc)

        status = "REJECTED" if rejected else ("ERROR" if error else "OK")
        print(f"{status} ({elapsed:.1f}s)")

        result = {
            "run_id": run_id,
            "tc_id": tc_id,
            "category": tc["category"],
            "entity_type": tc["entity_type"],
            "context_quality": tc["context_quality"],
            "model": model,
            "prompt_version": prompt_version,
            "temperature": temperature,
            "output": output,
            "response_time_sec": round(elapsed, 2),
            "rejected": rejected,
            "error": error,
            "scores": None,
        }

        result_path = out_dir / f"{tc_id.lower()}_result.json"
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

        summary["results"].append({
            "tc_id": tc_id,
            "status": status,
            "rejected": rejected,
            "response_time_sec": round(elapsed, 2),
            "error": error,
        })

    summary_path = out_dir / "run_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    total = len(test_cases)
    errors = sum(1 for r in summary["results"] if r["error"])
    rejected = sum(1 for r in summary["results"] if r["rejected"])
    print(f"\nResumen: {total} casos | {errors} errores | {rejected} rechazos")
    print(f"Resultados en: {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Harness de evaluación de prompts LoreMaster")
    parser.add_argument("--model", default="llama3.2", help="Modelo Ollama (default: llama3.2)")
    parser.add_argument(
        "--prompt-version",
        default="current",
        help="Etiqueta de la versión del prompt (default: current). Acepta cualquier string.",
    )
    parser.add_argument("--temperature", type=float, default=0.7, help="Temperatura del modelo (default: 0.7)")
    parser.add_argument("--ollama-url", default="http://localhost:11434", help="URL base de Ollama")
    args = parser.parse_args()

    run(
        model=args.model,
        prompt_version=args.prompt_version,
        temperature=args.temperature,
        ollama_url=args.ollama_url,
    )


if __name__ == "__main__":
    main()
