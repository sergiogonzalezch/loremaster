"""Lanza todos los runs (4 configs × N modelos) y genera el reporte comparativo.

Uso rápido:
    python evaluations/llm_params_harness/run_all.py

Con modelos específicos:
    python evaluations/llm_params_harness/run_all.py \\
        --models llama3.2:latest,mistral:latest \\
        --judge gemma:latest \\
        --configs baseline,temp_only,both

Notas:
  - qwen3.5 (razonador) excluido por diseño: no aporta ventaja en generación creativa.
  - gemma reservado para juez, no para ser evaluado.
  - Cada run tarda ~10 min en hardware local mid-range (10 TC × ~60s/TC).
    Un run_all completo con 4 modelos × 4 configs ≈ 3-4 horas.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Forzar UTF-8 en subprocesos (necesario en Windows con cp1252)
os.environ.setdefault("PYTHONUTF8", "1")

_SCRIPT_DIR = Path(__file__).resolve().parent
_RUNNER = _SCRIPT_DIR / "runner.py"
_REPORTER = _SCRIPT_DIR / "reporter.py"

# Modelos a evaluar (gemma como juez, no evaluado; qwen3.5 razonador excluido)
_DEFAULT_MODELS = "llama3.2:latest,llama3.1:latest,qwen2.5:latest,mistral:latest"
_DEFAULT_JUDGE = "gemma:latest"
_DEFAULT_CONFIGS = "baseline,temp_only,tokens_only,both"
_DEFAULT_REPORT = _SCRIPT_DIR.parents[2] / "docs" / "reportes" / "llm_params_eval.md"


def main() -> None:
    """Punto de entrada CLI del orquestador."""
    parser = argparse.ArgumentParser(
        description="Ejecuta todos los runs de evaluación y genera el reporte final.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Evaluación completa (todos los modelos y configs)
  python evaluations/llm_params_harness/run_all.py

  # Solo dos modelos, solo las configs más relevantes
  python evaluations/llm_params_harness/run_all.py \\
      --models llama3.2:latest,mistral:latest \\
      --configs baseline,temp_only,both

  # Solo generar el reporte de runs ya existentes (sin ejecutar)
  python evaluations/llm_params_harness/run_all.py --report-only
        """,
    )
    parser.add_argument(
        "--models",
        default=_DEFAULT_MODELS,
        help=f"Modelos separados por coma (default: {_DEFAULT_MODELS})",
    )
    parser.add_argument(
        "--configs",
        default=_DEFAULT_CONFIGS,
        help=f"Configs separadas por coma (default: {_DEFAULT_CONFIGS})",
    )
    parser.add_argument("--judge", default=_DEFAULT_JUDGE, help=f"Modelo juez (default: {_DEFAULT_JUDGE})")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=_SCRIPT_DIR / "results",
        help="Directorio donde guardar los resultados",
    )
    parser.add_argument(
        "--seed",
        type=Path,
        default=_SCRIPT_DIR.parent / "dataset" / "golden_seed.txt",
        help="Texto semilla como contexto RAG",
    )
    parser.add_argument(
        "--report-out",
        type=Path,
        default=_DEFAULT_REPORT,
        help=f"Ruta del reporte markdown final (default: {_DEFAULT_REPORT})",
    )
    parser.add_argument(
        "--title",
        default="Evaluación de Parámetros LLM — Temperatura y num_predict",
        help="Título del reporte",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Solo genera el reporte a partir de runs existentes, sin ejecutar nuevos runs",
    )
    args = parser.parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    configs = [c.strip() for c in args.configs.split(",") if c.strip()]

    if not args.report_only:
        total = len(models) * len(configs)
        print(f"\n{'='*65}")
        print("  llm_params_harness — run_all")
        print(f"  Modelos : {models}")
        print(f"  Configs : {configs}")
        print(f"  Juez    : {args.judge}")
        print(f"  Total   : {total} runs")
        print(f"{'='*65}\n")

        run_errors = 0
        global_t0 = time.monotonic()

        for i, model in enumerate(models):
            for j, config in enumerate(configs):
                idx = i * len(configs) + j + 1
                print(f"\n[{idx}/{total}] {model}  ×  {config}")
                cmd = [
                    sys.executable, str(_RUNNER),
                    "--model", model,
                    "--config", config,
                    "--judge", args.judge,
                    "--out-dir", str(args.out_dir),
                    "--seed", str(args.seed),
                ]
                result = subprocess.run(cmd)
                if result.returncode != 0:
                    print(f"  ⚠ Run terminó con error (exit {result.returncode}), continuando...")
                    run_errors += 1

        elapsed_total = round(time.monotonic() - global_t0, 0)
        print(f"\n{'='*65}")
        print(f"  Runs completados: {total - run_errors}/{total}  |  Tiempo total: {int(elapsed_total)}s")
        print(f"{'='*65}")

    # Generar reporte con todos los runs del directorio
    print("\nGenerando reporte final...")
    report_cmd = [
        sys.executable, str(_REPORTER),
        "--results-dir", str(args.out_dir),
        "--output", str(args.report_out),
        "--title", args.title,
    ]
    subprocess.run(report_cmd)
    print(f"\n✅ Proceso completo. Reporte en: {args.report_out}")


if __name__ == "__main__":
    main()
