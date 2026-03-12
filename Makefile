PY ?= python
PIP ?= pip
WEB_DIR ?= frontend/enqueteur-webview

.PHONY: help test test-cov demo-run server-dev web-install web-dev web-dev-local clean

help:
	@echo "Enqueteur commands"
	@echo "  make test         Run backend tests"
	@echo "  make test-cov     Run backend tests with coverage"
	@echo "  make demo-run     Generate deterministic offline demo artifacts"
	@echo "  make server-dev   Run canonical backend host on 127.0.0.1:7777"
	@echo "  make web-install  Install webview dependencies"
	@echo "  make web-dev      Run webview dev server"
	@echo "  make web-dev-local Run webview dev server preconfigured for local backend"
	@echo "  make clean        Remove local caches and generated runs"

test:
	$(PY) -m pytest backend/sim4/tests -q

test-cov:
	$(PY) -m pytest backend/sim4/tests --cov=backend.sim4 --cov-report=term-missing

demo-run:
	$(PY) scripts/run_sim4_kvp_demo.py --ticks 1800 --tick-rate 30 --agents 6

server-dev:
	ENQ_SERVER_HOST=127.0.0.1 ENQ_SERVER_PORT=7777 $(PY) -m backend.server

web-install:
	cd $(WEB_DIR) && npm install

web-dev:
	cd $(WEB_DIR) && npm run dev

web-dev-local:
	cd $(WEB_DIR) && npm run dev:local

clean:
	rm -rf .pytest_cache runs
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
