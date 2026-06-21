ARG BASE_IMAGE=python:3.12-slim-bookworm
FROM ${BASE_IMAGE}

ENV POETRY_VIRTUALENVS_CREATE=false
WORKDIR /app

RUN groupadd --gid 2000 app \
    && useradd --uid 2000 --gid app --shell /bin/bash --create-home app \
    && chown -R app /app \
    && pip install poetry

COPY pyproject.toml poetry.lock* /app/
RUN poetry install --only main,patients --no-root

COPY src/common /app/common
COPY src/patients /app/patients
COPY src/common/application/healthcheck.py /app/healthcheck.py
USER app

CMD ["uvicorn", "patients.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

LABEL org.opencontainers.image.title="neuroatlas-patients" \
      org.opencontainers.image.description="Clinical data service for pediatric neurorehabilitation"
