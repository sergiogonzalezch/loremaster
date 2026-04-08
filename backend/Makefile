PY_CACHE_DIR ?= .pycache
export PYTHONPYCACHEPREFIX := $(PY_CACHE_DIR)

.PHONY: run test

run:
	@mkdir -p $(PY_CACHE_DIR)
	uvicorn app.main:app --reload

test:
	@mkdir -p $(PY_CACHE_DIR)
	pytest
