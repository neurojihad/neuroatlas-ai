-include infra/.env
export

export PYTHONPATH := $(PYTHONPATH):$(shell pwd)/src

# Local setup

install:
	pip install poetry
	poetry install

init:
	cp infra/.env.example infra/.env

# Run services locally (in-memory adapters, no infra required)

run_patients:
	poetry run uvicorn patients.main:app --host 0.0.0.0 --port 8001 --reload

run_ml:
	poetry run uvicorn ml.main:app --host 0.0.0.0 --port 8002 --reload

# Infrastructure (local)

up:
	docker compose up -d

down:
	docker compose down

# Lint and format

fmt:
	poetry run isort --profile black src/
	poetry run ruff format src

fmt_check:
	poetry run isort --profile black --check src/
	poetry run ruff format --check src

lint:
	poetry run ruff check src
	poetry run mypy src/

lint_fix:
	poetry run ruff check --fix src

sast:
	poetry run bandit -c pyproject.toml -r src

check: fmt lint test

# Tests

test:
	poetry run pytest src

test_patients:
	poetry run pytest src/patients --cov=src/patients

test_ml:
	poetry run pytest src/ml --cov=src/ml

test_k:
	poetry run pytest src -k=${k}

# Poetry

relock:
	poetry lock --no-update
