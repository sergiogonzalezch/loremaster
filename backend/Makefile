# Centraliza todos los __pycache__ y .pyc en un solo directorio
PY_CACHE_DIR ?= .pycache
export PYTHONPYCACHEPREFIX := $(CURDIR)/$(PY_CACHE_DIR)
export PYTHONDONTWRITEBYTECODE := 1

.PHONY: run test format lint install clean clean-all

install:
	@mkdir -p $(PY_CACHE_DIR)
	pip install -r requirements.txt

install-dev:
	@mkdir -p $(PY_CACHE_DIR)
	pip install -r requirements.txt -r requirements-dev.txt

run:
	@mkdir -p $(PY_CACHE_DIR)
	uvicorn app.main:app --reload

test:
	@mkdir -p $(PY_CACHE_DIR)
	pytest

format:
	@mkdir -p $(PY_CACHE_DIR)
	black .

lint:
	@mkdir -p $(PY_CACHE_DIR)
	ruff check .

# Limpia solo el caché centralizado
clean:
	rm -rf $(PY_CACHE_DIR)

# Limpia TODO: caché centralizado + __pycache__ dispersos + .pyc sueltos
clean-all: clean
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
