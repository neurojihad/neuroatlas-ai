-include infra/.env
export

export PYTHONPATH := $(PYTHONPATH):$(shell pwd)/src

# Local setup

install:
	pip install poetry
	poetry install

install_ml:
	poetry install --with ml

init:
	@test -f infra/.env || cp infra/.env.example infra/.env

# Run services locally (in-memory adapters, no infra required)
# Local and compose targets load variables from infra/.env (see -include above).

run_patients:
	poetry run uvicorn patients.main:app --host 0.0.0.0 --port 8001 --reload

run_ml:
	poetry run uvicorn ml.main:app --host 0.0.0.0 --port 8002 --reload

run_housekeeper:
	poetry run uvicorn housekeeper.main:app --host 0.0.0.0 --port 8003 --reload

# Infrastructure (local)
# Infra compose: Postgres + Kafka + shared network. App compose: patients, ml, housekeeper.
# Run `make up_infra` before app services; `make up` starts both.
#
# ML Kafka consumer (Docker):
#   1. Set KAFKA_ENABLED=true in infra/.env
#   2. make up_infra && make kafka_topics && make up_ml

COMPOSE_ENV = --env-file infra/.env
COMPOSE_INFRA = docker compose $(COMPOSE_ENV) -f infra/infra.compose.yml
COMPOSE_APP = docker compose $(COMPOSE_ENV) -f infra/application.compose.yml

up: up_infra up_app

down: down_app down_infra

up_infra:
	$(COMPOSE_INFRA) up -d

down_infra:
	$(COMPOSE_INFRA) down

kafka_topics:
	KAFKA_BOOTSTRAP_SERVERS=localhost:9092 $(COMPOSE_ENV) poetry run python infra/kafka/init_topics.py

kafka_logs:
	docker logs -f kafka_neuroatlas

up_app:
	$(COMPOSE_APP) up -d --build

down_app:
	$(COMPOSE_APP) down

up_pat:
	$(COMPOSE_APP) up -d --build patients

down_pat:
	$(COMPOSE_APP) stop patients

up_ml:
	@echo "ML Kafka consumer is active only when KAFKA_ENABLED=true in infra/.env"
	$(COMPOSE_APP) up -d --build ml

down_ml:
	$(COMPOSE_APP) stop ml

up_hk:
	$(COMPOSE_APP) up -d --build housekeeper

down_hk:
	$(COMPOSE_APP) stop housekeeper

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

test_housekeeper:
	poetry run pytest src/housekeeper --cov=src/housekeeper

test_messaging:
	poetry run pytest src/common/tests/test_bus src/ml/tests/test_adapters

# Migrations (all run through Housekeeper; requires Postgres — run `make up_infra` first)

migrate:
	poetry run alembic upgrade head

makemigration:
	poetry run alembic revision --autogenerate -m "${m}"

test_k:
	poetry run pytest src -k=${k}

# Poetry

relock:
	poetry lock --no-update
