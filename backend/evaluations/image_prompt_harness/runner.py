#!/usr/bin/env python3
"""Runner del image prompt harness.

Evalúa tipo correcto e inglés sobre el output de build_combined_prompt()
para cada modelo Ollama indicado.

Uso (desde backend/ con el venv activo):
    python evaluations/image_prompt_harness/runner.py --model llama3.2:latest
    python evaluations/image_prompt_harness/runner.py --model mistral --temperature 0.5
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

from app.domain.image_prompt_rules import build_combined_prompt  # noqa: E402
from app.models.db.entity import EntityType  # noqa: E402
from app.models.enums import ContentCategory  # noqa: E402
from evaluations.image_prompt_harness.judge import check_english, check_tipo  # noqa: E402

_TEST_CASES_DIR = _HARNESS_DIR / "test_cases"
_RESULTS_DIR = _HARNESS_DIR / "results"


def _load_test_cases() -> list[dict]:
    cases = []
    for path in sorted(_TEST_CASES_DIR.glob("tc_*.yaml")):
        with path.open(encoding="utf-8") as f:
            cases.append(yaml.safe_load(f))
    return cases


def _call_ollama(prompt: str, model: str, temperature: float, base_url: str) -> tuple[str, float]:
    url = f"{base_url}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": 256},
    }
    start = time.time()
    response = requests.post(url, json=payload, timeout=120)
    response.raise_for_status()
    elapsed = time.time() - start
    return response.json()["response"], elapsed


def run(model: str, temperature: float, ollama_url: str) -> None:
    run_id = f"{datetime.now().strftime('%Y-%m-%d_%H-%M')}_{model.replace(':', '_')}_{temperature}"
    out_dir = _RESULTS_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    test_cases = _load_test_cases()
    summary: dict = {
        "run_id": run_id,
        "model": model,
        "temperature": temperature,
        "total_cases": len(test_cases),
        "tipo_correct": 0,
        "english_correct": 0,
        "results": [],
    }

    print(f"\nRun: {run_id}")
    print(f"Test cases: {len(test_cases)}\n")

    for tc in test_cases:
        tc_id = tc["id"]
        entity_type = EntityType(tc["entity_type"])
        category = ContentCategory(tc["category"])
        expected_types = [t.lower() for t in tc["expected_types"]]

        print(f"  {tc_id}: {tc['entity_type']}/{tc['category'][:20]} ... ", end="", flush=True)

        prompt = build_combined_prompt(entity_type, category, tc["content"])

        try:
            output, elapsed = _call_ollama(prompt, model, temperature, ollama_url)
            error = None
        except Exception as exc:
            output = ""
            elapsed = 0.0
            error = str(exc)

        tipo_ok = check_tipo(output, expected_types)
        english_ok = check_english(output)

        if tipo_ok:
            summary["tipo_correct"] += 1
        if english_ok:
            summary["english_correct"] += 1

        status = "ERROR" if error else f"tipo={'OK' if tipo_ok else 'FAIL'} en={'OK' if english_ok else 'FAIL'}"
        print(f"{status} ({elapsed:.1f}s)")

        result = {
            "run_id": run_id,
            "tc_id": tc_id,
            "entity_type": tc["entity_type"],
            "category": tc["category"],
            "expected_types": expected_types,
            "model": model,
            "temperature": temperature,
            "output": output,
            "response_time_sec": round(elapsed, 2),
            "tipo_ok": tipo_ok,
            "english_ok": english_ok,
            "error": error,
        }

        result_path = out_dir / f"{tc_id}_result.json"
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

        summary["results"].append(
            {
                "tc_id": tc_id,
                "tipo_ok": tipo_ok,
                "english_ok": english_ok,
                "response_time_sec": round(elapsed, 2),
                "error": error,
            }
        )

    total = len(test_cases)
    summary["tipo_pct"] = round(summary["tipo_correct"] / total * 100, 1) if total else 0.0
    summary["english_pct"] = round(summary["english_correct"] / total * 100, 1) if total else 0.0

    (out_dir / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        f"\nResumen - tipo: {summary['tipo_correct']}/{total} ({summary['tipo_pct']}%) "
        f"| ingles: {summary['english_correct']}/{total} ({summary['english_pct']}%)"
    )
    print(f"Resultados en: {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Image Prompt Harness — evaluación tipo e inglés")
    parser.add_argument("--model", default="llama3.2:latest", help="Modelo Ollama (default: llama3.2:latest)")
    parser.add_argument("--temperature", type=float, default=0.7, help="Temperatura del modelo (default: 0.7)")
    parser.add_argument("--ollama-url", default="http://localhost:11434", help="URL base de Ollama")
    args = parser.parse_args()

    run(model=args.model, temperature=args.temperature, ollama_url=args.ollama_url)


if __name__ == "__main__":
    main()
