"""Smoke tests de los harnesses de evaluación.

Verifica que runner, judge y módulos auxiliares importan sin error y que los
test cases YAML tienen la estructura mínima requerida. No requiere Ollama ni red.
"""

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

_HARNESS_DIR = Path(__file__).parent.parent / "evaluations" / "prompt_harness"
_IMAGE_HARNESS_DIR = Path(__file__).parent.parent / "evaluations" / "image_prompt_harness"

_REQUIRED_TC_FIELDS = ("id", "name", "category", "entity_name", "entity_type",
                       "context_quality", "simulated_context", "query")


def _import_harness_module(name: str):
    path = _HARNESS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"harness_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"harness_{name}"] = mod
    spec.loader.exec_module(mod)
    return mod


def _import_image_harness_module(name: str):
    path = _IMAGE_HARNESS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"image_harness_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"image_harness_{name}"] = mod
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


def test_reporter_importable():
    reporter = _import_harness_module("reporter")
    assert callable(reporter.generate_report)
    assert callable(reporter.main)


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


# ── Image Prompt Harness ──────────────────────────────────────────────────────

_IMAGE_REQUIRED_TC_FIELDS = ("id", "entity_type", "category", "expected_types", "content")


def test_image_harness_judge_importable():
    judge = _import_image_harness_module("judge")
    assert callable(judge.check_tipo)
    assert callable(judge.check_english)
    assert isinstance(judge._SPANISH_TOKENS, frozenset)


def test_image_harness_runner_importable():
    runner = _import_image_harness_module("runner")
    assert callable(runner.run)
    assert callable(runner._load_test_cases)


def test_image_harness_reporter_importable():
    reporter = _import_image_harness_module("reporter")
    assert callable(reporter.generate_report)
    assert callable(reporter.main)


def test_image_harness_cases_valid():
    tc_dir = _IMAGE_HARNESS_DIR / "test_cases"
    yamls = sorted(tc_dir.glob("tc_*.yaml"))
    assert len(yamls) >= 10, f"Se esperaban al menos 10 casos, encontrados: {len(yamls)}"
    for path in yamls:
        tc = yaml.safe_load(path.read_text(encoding="utf-8"))
        for field in _IMAGE_REQUIRED_TC_FIELDS:
            assert field in tc, f"{path.name}: falta campo '{field}'"
        assert isinstance(tc["expected_types"], list), \
            f"{path.name}: 'expected_types' debe ser lista"
        assert len(tc["expected_types"]) >= 1, \
            f"{path.name}: 'expected_types' no puede estar vacío"
        assert tc["content"].strip(), \
            f"{path.name}: 'content' no puede estar vacío"
