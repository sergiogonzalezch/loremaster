"""Harness de evaluación para parámetros LLM: temperatura y num_predict por categoría.

Compara cuatro configuraciones contra el baseline actual:
  baseline    — temp=0.7 fija, num_predict=2000 para todas las categorías
  temp_only   — temperatura por categoría (factual=0.55, scene=0.85), tokens=2000
  tokens_only — temperatura fija 0.7, num_predict por categoría (factual=1200, scene=2500)
  both        — temperatura + num_predict por categoría combinados

Uso:
    python evaluations/llm_params_harness/runner.py \\
        --model llama3.2:latest \\
        --config baseline \\
        --judge gemma:latest
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Permite imports desde backend/ sin instalar el paquete
_BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_BACKEND_DIR))

from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import OllamaLLM

from app.domain.prompt_templates import render_prompt
from app.models.db.entity import EntityType
from app.models.enums import ContentCategory

OLLAMA_BASE_URL = "http://localhost:11434"

# ── Valores de temperatura evaluados (harness 2026-05-16) ─────────────────────
# Descartados por delta neutral vs baseline en llama3.x y mistral.
# Conservados aquí como referencia para futuras pruebas con otros modelos.
_FACTUAL_TEMPERATURE = 0.55   # backstory, extended_description
_CREATIVE_TEMPERATURE = 0.85  # scene

# ── Cuatro configuraciones a comparar ─────────────────────────────────────────

CONFIGS: dict[str, dict] = {
    "baseline": {
        "label": "Baseline (temp=0.7, tokens=2000 todas las categorías)",
        "temperature": {
            ContentCategory.backstory: 0.7,
            ContentCategory.extended_description: 0.7,
            ContentCategory.scene: 0.7,
        },
        "num_predict": {
            ContentCategory.backstory: 2000,
            ContentCategory.extended_description: 2000,
            ContentCategory.scene: 2000,
        },
    },
    "temp_only": {
        "label": "Solo temperatura por categoría (factual=0.55, scene=0.85)",
        "temperature": {
            ContentCategory.backstory: 0.55,
            ContentCategory.extended_description: 0.55,
            ContentCategory.scene: 0.85,
        },
        "num_predict": {
            ContentCategory.backstory: 2000,
            ContentCategory.extended_description: 2000,
            ContentCategory.scene: 2000,
        },
    },
    "tokens_only": {
        "label": "Solo num_predict por categoría (factual=1200, scene=2500)",
        "temperature": {
            ContentCategory.backstory: 0.7,
            ContentCategory.extended_description: 0.7,
            ContentCategory.scene: 0.7,
        },
        "num_predict": {
            ContentCategory.backstory: 1200,
            ContentCategory.extended_description: 1200,
            ContentCategory.scene: 2500,
        },
    },
    "both": {
        "label": "Temperatura + num_predict por categoría",
        "temperature": {
            ContentCategory.backstory: 0.55,
            ContentCategory.extended_description: 0.55,
            ContentCategory.scene: 0.85,
        },
        "num_predict": {
            ContentCategory.backstory: 1200,
            ContentCategory.extended_description: 1200,
            ContentCategory.scene: 2500,
        },
    },
}

# ── 10 casos de prueba ─────────────────────────────────────────────────────────
# Cubren las 3 categorías activas, los 5 tipos de entidad y 3 niveles de
# contexto (rich / medium / sparse) para detectar comportamientos diferenciales.

TEST_CASES: list[dict] = [
    {
        "tc_id": "TC-01",
        "category": ContentCategory.backstory,
        "entity_type": EntityType.character,
        "entity_name": "Lyra Valdris",
        "entity_desc": "Hechicera de la Torre Escarlata, especialista en magia de enlace.",
        "query": "Genera la historia de fondo de Lyra Valdris y cómo llegó a dominar la magia de enlace en Valdorath.",
        "context_quality": "rich",
    },
    {
        "tc_id": "TC-02",
        "category": ContentCategory.extended_description,
        "entity_type": EntityType.character,
        "entity_name": "Lyra Valdris",
        "entity_desc": "Hechicera de la Torre Escarlata, especialista en magia de enlace.",
        "query": "Describe la apariencia actual y personalidad observable de Lyra Valdris.",
        "context_quality": "rich",
    },
    {
        "tc_id": "TC-03",
        "category": ContentCategory.scene,
        "entity_type": EntityType.character,
        "entity_name": "Lyra Valdris",
        "entity_desc": "Hechicera de la Torre Escarlata, especialista en magia de enlace.",
        "query": "Narra una escena donde Lyra investiga el avance de la plaga de petrificación en los límites del reino.",
        "context_quality": "rich",
    },
    {
        "tc_id": "TC-04",
        "category": ContentCategory.backstory,
        "entity_type": EntityType.creature,
        "entity_name": "Devorador de Niebla",
        "entity_desc": "Criatura predadora que habita los bosques del Velo Carmesí en Valdorath.",
        "query": "Escribe el origen evolutivo y la historia del Devorador de Niebla en los bosques de Valdorath.",
        "context_quality": "medium",
    },
    {
        "tc_id": "TC-05",
        "category": ContentCategory.extended_description,
        "entity_type": EntityType.creature,
        "entity_name": "Devorador de Niebla",
        "entity_desc": "Criatura predadora que habita los bosques del Velo Carmesí en Valdorath.",
        "query": "Describe la apariencia física, tamaño y comportamiento observable del Devorador de Niebla.",
        "context_quality": "medium",
    },
    {
        "tc_id": "TC-06",
        "category": ContentCategory.scene,
        "entity_type": EntityType.creature,
        "entity_name": "Devorador de Niebla",
        "entity_desc": "Criatura predadora que habita los bosques del Velo Carmesí en Valdorath.",
        "query": "Narra una escena de emboscada del Devorador de Niebla a un grupo de exploradores al anochecer.",
        "context_quality": "medium",
    },
    {
        "tc_id": "TC-07",
        "category": ContentCategory.extended_description,
        "entity_type": EntityType.location,
        "entity_name": "Torre Escarlata",
        "entity_desc": "Principal centro de estudios de magia en el reino de Valdorath.",
        "query": "Describe la Torre Escarlata: arquitectura, ambiente interior y elementos visuales característicos.",
        "context_quality": "rich",
    },
    {
        "tc_id": "TC-08",
        "category": ContentCategory.scene,
        "entity_type": EntityType.location,
        "entity_name": "Río Valdor",
        "entity_desc": "Principal curso fluvial del reino, frontera natural entre regiones.",
        "query": "Narra una escena al amanecer en las orillas del Río Valdor durante la tensión política entre facciones.",
        "context_quality": "medium",
    },
    {
        "tc_id": "TC-09",
        "category": ContentCategory.backstory,
        "entity_type": EntityType.faction,
        "entity_name": "Los Custodios del Umbral",
        "entity_desc": "Orden fundada para contener la expansión de la plaga de petrificación.",
        "query": "Escribe la historia de fundación de Los Custodios del Umbral y la motivación de sus primeros miembros.",
        "context_quality": "sparse",
    },
    {
        "tc_id": "TC-10",
        "category": ContentCategory.backstory,
        "entity_type": EntityType.item,
        "entity_name": "Cristal del Enlace",
        "entity_desc": "Artefacto que amplifica y estabiliza la magia de enlace de almas.",
        "query": "Escribe el origen del Cristal del Enlace, quién lo creó y por qué en el contexto de Valdorath.",
        "context_quality": "sparse",
    },
]

# ── Prompt del juez ────────────────────────────────────────────────────────────

_JUDGE_PROMPT = """\
Eres un evaluador experto en narrativa de worldbuilding. Evalúa el texto generado.

ESCALA: 0=Deficiente  1=Básico  2=Bueno  3=Excelente

DIMENSIONES:
D1 — Adherencia al contexto: ¿Usa información concreta del contexto RAG proporcionado?
D2 — Especificidad narrativa: ¿Tiene detalles concretos (nombres, lugares, eventos específicos del mundo)?
D3 — Cumplimiento de categoría: ¿Respeta extensión, tiempo verbal y scope exigidos por la categoría?
D4 — Completitud: ¿El texto está completo, sin corte abrupto y con cierre coherente?

CATEGORÍA: {category}
ENTIDAD: {entity_name} ({entity_type})
QUERY: {query}

CONTEXTO RAG (extracto):
---
{context}
---

TEXTO GENERADO:
---
{output}
---

Responde ÚNICAMENTE con JSON válido, sin texto antes ni después:
{{"D1": <0-3>, "D1_reason": "<razón breve en español>", "D2": <0-3>, "D2_reason": "<razón breve>", "D3": <0-3>, "D3_reason": "<razón breve>", "D4": <0-3>, "D4_reason": "<razón breve>"}}"""  # noqa: E501


# ── Funciones auxiliares ───────────────────────────────────────────────────────


def _make_llm(model: str, temperature: float, num_predict: int) -> OllamaLLM:
    return OllamaLLM(
        model=model,
        base_url=OLLAMA_BASE_URL,
        temperature=temperature,
        num_predict=num_predict,
    )


def _score_with_judge(judge_model: str, tc: dict, context: str, output: str) -> dict:
    """Llama al modelo juez y parsea el JSON de puntuaciones D1-D4."""
    prompt = _JUDGE_PROMPT.format(
        category=tc["category"].value,
        entity_name=tc["entity_name"],
        entity_type=tc["entity_type"].value,
        query=tc["query"],
        context=context[:1500],
        output=output,
    )
    llm = _make_llm(judge_model, temperature=0.1, num_predict=600)
    raw = ""
    try:
        raw = (llm | StrOutputParser()).invoke(prompt)
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(raw[start:end])
            # Validar que tiene las 4 dimensiones
            if all(f"D{i}" in parsed for i in range(1, 5)):
                return parsed
    except Exception:
        pass
    return {
        "D1": 0, "D1_reason": f"parse_error: {raw[:80]}",
        "D2": 0, "D2_reason": "parse_error",
        "D3": 0, "D3_reason": "parse_error",
        "D4": 0, "D4_reason": "parse_error",
    }


def _score_avg(scores: dict) -> float:
    return round(sum(scores.get(f"D{i}", 0) for i in range(1, 5)) / 4, 2)


# ── Runner ─────────────────────────────────────────────────────────────────────


def run_eval(
    model: str,
    config_name: str,
    judge_model: str,
    out_dir: Path,
    seed_text: str,
) -> Path:
    """Ejecuta los 10 TC para un modelo y configuración. Retorna el directorio del run."""
    cfg = CONFIGS[config_name]
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    model_slug = model.replace(":", "_").replace(".", "")
    run_id = f"{ts}_{model_slug}_{config_name}"
    run_dir = out_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*65}")
    print(f"  Modelo : {model}")
    print(f"  Config : {config_name}  —  {cfg['label']}")
    print(f"  Juez   : {judge_model}")
    print(f"{'='*65}")

    tc_summaries = []

    for tc in TEST_CASES:
        cat = tc["category"]
        print(f"  {tc['tc_id']} [{cat.value:22}] {tc['entity_name'][:22]:<22} ...", end=" ", flush=True)

        extra = (
            f"Descripción actual de '{tc['entity_name']}' ({tc['entity_type'].value}):\n{tc['entity_desc']}\n\n"
            if tc["entity_desc"]
            else ""
        )
        rendered = render_prompt(
            category=cat,
            entity_name=tc["entity_name"],
            entity_type=tc["entity_type"].value,
            context=extra + seed_text,
            query=tc["query"],
        )

        temperature = cfg["temperature"][cat]
        num_predict = cfg["num_predict"][cat]
        llm = _make_llm(model, temperature, num_predict)

        t0 = time.monotonic()
        output, error = "", None
        try:
            output = (llm | StrOutputParser()).invoke(rendered)
        except Exception as exc:
            error = str(exc)
        elapsed = round(time.monotonic() - t0, 2)

        scores: dict = {}
        if output:
            scores = _score_with_judge(judge_model, tc, seed_text, output)

        avg = _score_avg(scores) if scores else 0.0
        status = "OK" if output and not error else "ERROR"
        print(f"{status} ({elapsed}s) avg={avg}")

        tc_result = {
            "run_id": run_id,
            "tc_id": tc["tc_id"],
            "category": cat.value,
            "entity_type": tc["entity_type"].value,
            "context_quality": tc["context_quality"],
            "model": model,
            "config": config_name,
            "temperature": temperature,
            "num_predict": num_predict,
            "output": output,
            "response_time_sec": elapsed,
            "error": error,
            "scores": scores,
        }
        (run_dir / f"{tc['tc_id'].lower()}_result.json").write_text(
            json.dumps(tc_result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        tc_summaries.append({
            "tc_id": tc["tc_id"],
            "status": status,
            "response_time_sec": elapsed,
            "error": error,
            "score_avg": avg,
        })

    summary = {
        "run_id": run_id,
        "model": model,
        "config": config_name,
        "config_label": cfg["label"],
        "judge_model": judge_model,
        "results": tc_summaries,
    }
    (run_dir / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    global_avg = round(sum(s["score_avg"] for s in tc_summaries) / len(tc_summaries), 2)
    errors = sum(1 for s in tc_summaries if s["status"] == "ERROR")
    print(f"\n  → {run_id}")
    print(f"  → Score global: {global_avg}/3.0  |  Errores: {errors}/{len(TEST_CASES)}")
    return run_dir


# ── CLI ────────────────────────────────────────────────────────────────────────


def main() -> None:
    """Punto de entrada CLI del runner."""
    parser = argparse.ArgumentParser(
        description="Evalúa una configuración LLM (temperatura + num_predict) con un modelo dado.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python evaluations/llm_params_harness/runner.py --model llama3.2:latest --config baseline --judge gemma:latest
  python evaluations/llm_params_harness/runner.py --model mistral:latest  --config temp_only
        """,
    )
    parser.add_argument("--model", required=True, help="Modelo Ollama a evaluar (ej. llama3.2:latest)")
    parser.add_argument("--config", required=True, choices=list(CONFIGS), help="Configuración de parámetros")
    parser.add_argument("--judge", default="gemma:latest", help="Modelo juez para scoring D1-D4 (default: gemma:latest)")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).parent / "results",
        help="Directorio de resultados",
    )
    parser.add_argument(
        "--seed",
        type=Path,
        default=Path(__file__).parent.parent / "dataset" / "golden_seed.txt",
        help="Texto semilla como contexto RAG simulado",
    )
    args = parser.parse_args()

    if not args.seed.exists():
        print(f"ERROR: seed no encontrado: {args.seed}")
        sys.exit(1)

    seed_text = args.seed.read_text(encoding="utf-8")
    run_dir = run_eval(
        model=args.model,
        config_name=args.config,
        judge_model=args.judge,
        out_dir=args.out_dir,
        seed_text=seed_text,
    )
    print(f"\nResultados en: {run_dir}")


if __name__ == "__main__":
    main()
