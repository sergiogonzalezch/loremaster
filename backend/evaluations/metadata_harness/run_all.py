"""Lanza todos los runs (3 configs x N modelos) y genera el reporte comparativo.

Uso rapido:
    python evaluations/metadata_harness/run_all.py

Con modelos especificos:
    python evaluations/metadata_harness/run_all.py \\
        --models mistral:latest,llama3.2:latest \\
        --configs baseline,meta_name,meta_full

Solo reporte (sin re-ejecutar):
    python evaluations/metadata_harness/run_all.py --report-only
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

os.environ.setdefault("PYTHONUTF8", "1")

_SCRIPT_DIR = Path(__file__).resolve().parent
_RUNNER = _SCRIPT_DIR / "runner.py"
_REPORTER = _SCRIPT_DIR / "reporter.py"

_DEFAULT_MODELS = "mistral:latest,llama3.2:latest"
_DEFAULT_JUDGE = "gemma2:9b"
_DEFAULT_CONFIGS = "baseline,meta_name,meta_full"
_DEFAULT_SEEDS = ",".join(
    [
        str(_SCRIPT_DIR.parent / "dataset" / "golden_seed.txt"),
        str(_SCRIPT_DIR.parent / "dataset" / "golden_seed_2.txt"),
    ]
)
_DEFAULT_REPORT = _SCRIPT_DIR.parents[2] / "docs" / "reportes" / "metadata_eval.md"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ejecuta todos los runs del metadata_harness y genera el reporte final.",
    )
    parser.add_argument("--models", default=_DEFAULT_MODELS)
    parser.add_argument("--configs", default=_DEFAULT_CONFIGS)
    parser.add_argument("--judge", default=_DEFAULT_JUDGE)
    parser.add_argument("--out-dir", type=Path, default=_SCRIPT_DIR / "results")
    parser.add_argument("--seeds", default=_DEFAULT_SEEDS, help="Rutas seed separadas por coma")
    parser.add_argument("--report-out", type=Path, default=_DEFAULT_REPORT)
    parser.add_argument(
        "--title",
        default="Evaluacion de Metadata en Contexto RAG -- cabeceras de fuente",
    )
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    configs = [c.strip() for c in args.configs.split(",") if c.strip()]

    if not args.report_only:
        total = len(models) * len(configs)
        print(f"\n{'='*65}")
        print("  metadata_harness -- run_all")
        print(f"  Modelos : {models}")
        print(f"  Configs : {configs}")
        print(f"  Juez    : {args.judge}")
        print(f"  Seeds   : {args.seeds.split(',')}")
        print(f"  Total   : {total} runs x 10 TC = {total * 10} evaluaciones")
        print(f"{'='*65}\n")

        run_errors = 0
        global_t0 = time.monotonic()

        for i, model in enumerate(models):
            for j, config in enumerate(configs):
                idx = i * len(configs) + j + 1
                print(f"\n[{idx}/{total}] {model}  x  {config}")
                cmd = [
                    sys.executable,
                    str(_RUNNER),
                    "--model",
                    model,
                    "--config",
                    config,
                    "--judge",
                    args.judge,
                    "--out-dir",
                    str(args.out_dir),
                    "--seeds",
                    args.seeds,
                ]
                result = subprocess.run(cmd)
                if result.returncode != 0:
                    print(f"  [!] Run termino con error (exit {result.returncode}), continuando...")
                    run_errors += 1

        elapsed_total = round(time.monotonic() - global_t0, 0)
        print(f"\n{'='*65}")
        print(f"  Runs completados: {total - run_errors}/{total}  |  Tiempo total: {int(elapsed_total)}s")
        print(f"{'='*65}")

    print("\nGenerando reporte final...")
    report_cmd = [
        sys.executable,
        str(_REPORTER),
        "--results-dir",
        str(args.out_dir),
        "--output",
        str(args.report_out),
        "--title",
        args.title,
    ]
    subprocess.run(report_cmd)
    print(f"\n[OK] Proceso completo. Reporte en: {args.report_out}")


if __name__ == "__main__":
    main()
