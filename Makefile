.PHONY: setup test up down logs generate-urls benchmark clean

PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python

setup:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@if [ ! -f .env ]; then cp .env.example .env; fi

test:
	PYTHONPATH=. $(PY) -m pytest -q

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

generate-urls:
	$(PY) scripts/generate_urls.py --count 100

benchmark:
	$(PY) scripts/benchmark_redirects.py

clean:
	docker compose down -v
	rm -rf $(VENV) .pytest_cache
