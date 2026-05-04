PY_CACHE_DIR ?= .pycache
export PYTHONPYCACHEPREFIX := $(CURDIR)/$(PY_CACHE_DIR)

.PHONY: run test format lint install clean

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

clean:
	rm -rf $(PY_CACHE_DIR)
