#!/usr/bin/env python3
"""Evaluador de outputs del harness de prompts.

Aplica scores D1-D4 (1-3) a cada resultado de una corrida del runner.
Soporta evaluación manual interactiva y evaluación automática con LLM-as-judge.

Uso (desde backend/ con el venv activo):
    python evaluations/prompt_harness/judge.py --run-dir 2026-05-13_llama3.2_current_0.7 --mode manual
    python evaluations/prompt_harness/judge.py --run-dir 2026-05-13_llama3.2_current_0.7 --mode llm

El score se escribe directamente en el JSON de cada resultado.
Los casos ya evaluados se saltan automáticamente (idempotente).
"""

import argparse
import json
import sys
from pathlib import Path

import requests
import yaml

_HARNESS_DIR = Path(__file__).parent
_TEST_CASES_DIR = _HARNESS_DIR / "test_cases"
_RESULTS_DIR = _HARNESS_DIR / "results"

_DIMENSIONS: dict[str, dict] = {
    "D1": {
        "name": "Adherencia al contexto",
        "criteria": {
            1: "Ignora el contexto, genera libremente sin referenciarlo",
            2: "Usa parte del contexto mezclado con invención sin señalarlo",
            3: "Usa el contexto de forma clara; lo que inventa es consistente con él",
        },
    },
    "D2": {
        "name": "Especificidad narrativa",
        "criteria": {
            1: "Output genérico que podría aplicar a cualquier entidad de ese tipo",
            2: "Algunos detalles específicos pero predomina lo genérico",
            3: "Output rico en detalles específicos del mundo y la entidad",
        },
    },
    "D3": {
        "name": "Cumplimiento de categoría",
        "criteria": {
            1: "El output no corresponde a la categoría pedida",
            2: "Corresponde parcialmente pero le falta estructura característica",
            3: "Reconociblemente de la categoría correcta con la estructura esperada",
        },
    },
    "D4": {
        "name": "Completitud",
        "criteria": {
            1: "Output cortado, incompleto o demasiado corto para la categoría",
            2: "Completo pero con longitud insuficiente para lo que se pedía",
            3: "Completo y con extensión apropiada para la categoría",
        },
    },
}

_JUDGE_PROMPT = """\
You are a narrative content evaluator. Score the following AI-generated output on 4 dimensions using a 1-3 scale.

SIMULATED CONTEXT (what the model had available):
---
{context}
---

USER QUERY: {query}
EXPECTED CATEGORY: {category}

OUTPUT TO EVALUATE:
---
{output}
---

SCORING DIMENSIONS:
D1 - Context adherence:     1=ignores context entirely  2=partial use with uninvited invention  3=clear context use
D2 - Narrative specificity: 1=generic for any entity    2=some specific details                 3=rich specific details
D3 - Category compliance:   1=wrong category feel       2=partial compliance                    3=correct category structure
D4 - Completeness:          1=too short or cut off      2=complete but insufficient length      3=complete and appropriate length

Respond ONLY with valid JSON — no text before or after the JSON object:
{{"D1": <1-3>, "D1_reason": "<one sentence>", "D2": <1-3>, "D2_reason": "<one sentence>",
"D3": <1-3>, "D3_reason": "<one sentence>", "D4": <1-3>, "D4_reason": "<one sentence>"}}\
"""


def _load_tc_map() -> dict[str, dict]:
    result = {}
    for path in _TEST_CASES_DIR.glob("*.yaml"):
        with path.open(encoding="utf-8") as f:
            tc = yaml.safe_load(f)
            result[tc["id"]] = tc
    return result


def _score_manual(result: dict, tc: dict) -> dict:
    sep = "=" * 70
    print(f"\n{sep}")
    print(f"TC: {result['tc_id']}  |  Category: {tc['category']}  |  Context: {tc['context_quality']}")
    print(f"Entity: {tc['entity_name']} ({tc['entity_type']})")
    print("\nCONTEXTO:")
    for i, fragment in enumerate(tc["simulated_context"], 1):
        print(f"  [{i}] {fragment}")
    print(f"\nQUERY: {tc['query']}")
    print(f"\nOUTPUT ({result['response_time_sec']}s):")
    print("-" * 40)
    print(result["output"] or "[VACÍO / RECHAZADO]")
    print("-" * 40)

    scores: dict = {}
    for dim, info in _DIMENSIONS.items():
        print(f"\n{dim} — {info['name']}:")
        for score, desc in info["criteria"].items():
            print(f"  {score}: {desc}")
        while True:
            raw = input("  Score (1-3): ").strip()
            if raw in ("1", "2", "3"):
                scores[dim] = int(raw)
                scores[f"{dim}_reason"] = input("  Justificación breve: ").strip()
                break
            print("  Valor inválido, ingresa 1, 2 o 3.")

    avg = sum(scores[d] for d in _DIMENSIONS) / len(_DIMENSIONS)
    print(f"\n  Promedio: {avg:.2f}")
    return scores


_MAX_OUTPUT_CHARS = 800


def _score_llm(result: dict, tc: dict, judge_model: str, ollama_url: str) -> dict:
    context = "\n\n".join(f"[{i + 1}] {f}" for i, f in enumerate(tc["simulated_context"]))
    output_text = (result["output"] or "[VACÍO]")[:_MAX_OUTPUT_CHARS]
    prompt = _JUDGE_PROMPT.format(
        context=context,
        query=tc["query"],
        category=tc["category"],
        output=output_text,
    )
    response = requests.post(
        f"{ollama_url}/api/generate",
        json={
            "model": judge_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0, "num_predict": -1},
        },
        timeout=300,
    )
    response.raise_for_status()
    raw = response.json()["response"].strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        msg = f"El juez no devolvió JSON válido: {raw[:200]}"
        raise ValueError(msg)
    return json.loads(raw[start:end])


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluador del harness de prompts LoreMaster")
    parser.add_argument(
        "--run-dir",
        required=True,
        help="Directorio de la corrida a evaluar (nombre relativo a results/, o ruta absoluta)",
    )
    parser.add_argument("--mode", choices=["manual", "llm"], default="manual", help="Modo de evaluación (default: manual)")
    parser.add_argument("--judge-model", default="llama3.2", help="Modelo juez para --mode llm (default: llama3.2)")
    parser.add_argument("--ollama-url", default="http://localhost:11434", help="URL base de Ollama")
    args = parser.parse_args()

    run_dir_path = Path(args.run_dir)
    run_dir = run_dir_path if run_dir_path.is_absolute() else _RESULTS_DIR / args.run_dir

    if not run_dir.exists():
        print(f"Directorio no encontrado: {run_dir}")
        sys.exit(1)

    result_files = sorted(run_dir.glob("tc*_result.json"))
    if not result_files:
        print(f"No se encontraron resultados en {run_dir}")
        sys.exit(1)

    tc_map = _load_tc_map()
    evaluated = 0

    for result_path in result_files:
        with result_path.open(encoding="utf-8") as f:
            result = json.load(f)

        if result.get("scores") is not None:
            print(f"  {result['tc_id']}: ya evaluado, saltando.")
            continue

        tc = tc_map.get(result["tc_id"])
        if not tc:
            print(f"  {result['tc_id']}: test case YAML no encontrado, saltando.")
            continue

        if args.mode == "manual":
            scores = _score_manual(result, tc)
        else:
            print(f"  Evaluando {result['tc_id']} con LLM-as-judge ({args.judge_model})... ", end="", flush=True)
            try:
                scores = _score_llm(result, tc, args.judge_model, args.ollama_url)
                avg = sum(scores[d] for d in _DIMENSIONS) / len(_DIMENSIONS)
                print(f"promedio={avg:.2f}")
            except Exception as exc:
                print(f"ERROR: {exc}")
                continue

        result["scores"] = scores
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        evaluated += 1

    print(f"\nEvaluación completada. {evaluated} caso(s) nuevos evaluados.")


if __name__ == "__main__":
    main()
