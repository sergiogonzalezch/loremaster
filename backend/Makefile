# Centraliza todos los __pycache__ y .pyc en un solo directorio
PY_CACHE_DIR ?= .pycache
export PYTHONPYCACHEPREFIX := $(CURDIR)/$(PY_CACHE_DIR)
export PYTHONDONTWRITEBYTECODE := 1

.PHONY: run test format lint install clean clean-all

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt -r requirements-dev.txt

run:
	uvicorn app.main:app --reload

test:
	pytest

format:
	black .

lint:
	ruff check .

# Limpia solo el caché centralizado
clean:
	rm -rf $(PY_CACHE_DIR)

# Limpia TODO: caché centralizado + __pycache__ dispersos + .pyc sueltos
clean-all: clean
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
