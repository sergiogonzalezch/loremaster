"""Smoke tests del harness de evaluación de prompts.

Verifica que runner, judge y compare importan sin error y que los test cases
YAML tienen la estructura mínima requerida. No requiere Ollama ni red.
"""

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

_HARNESS_DIR = Path(__file__).parent.parent / "evaluations" / "prompt_harness"

_REQUIRED_TC_FIELDS = ("id", "name", "category", "entity_name", "entity_type",
                       "context_quality", "simulated_context", "query")


def _import_harness_module(name: str):
    path = _HARNESS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"harness_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"harness_{name}"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_runner_importable():
    runner = _import_harness_module("runner")
    assert callable(runner.run)
    assert callable(runner._load_test_cases)


def test_judge_importable():
    judge = _import_harness_module("judge")
    assert isinstance(judge._DIMENSIONS, dict)
    assert set(judge._DIMENSIONS.keys()) == {"D1", "D2", "D3", "D4"}


def test_compare_importable():
    compare = _import_harness_module("compare")
    assert callable(compare.main)
    assert callable(compare._avg_dim)
    assert callable(compare._load_results)


def test_test_cases_valid():
    tc_dir = _HARNESS_DIR / "test_cases"
    yamls = sorted(tc_dir.glob("*.yaml"))
    assert yamls, "No se encontraron archivos YAML en test_cases/"
    for path in yamls:
        tc = yaml.safe_load(path.read_text(encoding="utf-8"))
        for field in _REQUIRED_TC_FIELDS:
            assert field in tc, f"{path.name}: falta campo '{field}'"
        assert isinstance(tc["simulated_context"], list), \
            f"{path.name}: 'simulated_context' debe ser lista"
        assert len(tc["simulated_context"]) >= 1, \
            f"{path.name}: 'simulated_context' no puede estar vacío"
