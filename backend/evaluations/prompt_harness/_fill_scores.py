"""Script temporal para evaluar casos pendientes con llama3.2 como juez fallback."""

import json
import re
import yaml
import requests
from pathlib import Path

DIMENSIONS = ["D1", "D2", "D3", "D4"]
TC_DIR = Path(__file__).parent / "test_cases"
RESULTS_DIR = Path(__file__).parent / "results"

JUDGE_PROMPT = """\
Score this AI-generated narrative output. Rate each dimension 1-3.

CONTEXT PROVIDED TO MODEL:
{context}

USER QUERY: {query}
EXPECTED CATEGORY: {category}

MODEL OUTPUT:
{output}

Return ONLY valid JSON (no markdown, no extra text):
{{"D1": 2, "D1_reason": "one sentence", "D2": 2, "D2_reason": "one sentence", "D3": 2, "D3_reason": "one sentence", "D4": 2, "D4_reason": "one sentence"}}

D1=context adherence(1=ignores,2=partial,3=uses well)
D2=specificity(1=generic,2=some details,3=rich details)
D3=category fit(1=wrong,2=partial,3=correct structure)
D4=completeness(1=too short,2=insufficient,3=appropriate)\
"""


def parse_scores(raw: str) -> dict:
    raw = re.sub(r"```[a-z]*", "", raw).strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1:
        raise ValueError("No JSON found")
    parsed = json.loads(raw[start:end])
    return {k.strip('"'): v for k, v in parsed.items()}


def main() -> None:
    tc_map = {}
    for p in TC_DIR.glob("*.yaml"):
        tc = yaml.safe_load(p.read_text(encoding="utf-8"))
        tc_map[tc["id"]] = tc

    runs = [
        "2026-05-13_21-24_llama3.2_current_0.7",
        "2026-05-13_21-26_llama3.2_refactored_0.7",
        "2026-05-13_23-17_llama3.2_refactored_v2_0.7",
    ]

    for run in runs:
        run_dir = RESULTS_DIR / run
        for f in sorted(run_dir.glob("tc*_result.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("scores") is not None:
                continue
            tc_id = data["tc_id"]
            tc = tc_map.get(tc_id)
            if not tc:
                continue

            context = "\n\n".join(
                f"[{i+1}] {x}" for i, x in enumerate(tc["simulated_context"])
            )
            output_text = (data["output"] or "[EMPTY]")[:600]
            prompt = JUDGE_PROMPT.format(
                context=context,
                query=tc["query"],
                category=tc["category"],
                output=output_text,
            )

            label = run.split("_")[3]
            print(f"  {tc_id} ({label}) ... ", end="", flush=True)
            try:
                resp = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "llama3.2",
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0, "num_predict": 512},
                    },
                    timeout=300,
                )
                scores = parse_scores(resp.json()["response"])
                avg = sum(scores[d] for d in DIMENSIONS) / 4
                data["scores"] = scores
                f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"avg={avg:.2f}")
            except Exception as e:
                print(f"ERROR: {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()
