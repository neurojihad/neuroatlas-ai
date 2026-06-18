ARG BASE_IMAGE=python:3.12-slim-bookworm
FROM ${BASE_IMAGE}

ENV POETRY_VIRTUALENVS_CREATE=false
WORKDIR /app

RUN groupadd --gid 2000 app \
    && useradd --uid 2000 --gid app --shell /bin/bash --create-home app \
    && chown -R app /app \
    && pip install poetry

COPY pyproject.toml poetry.lock* /app/
# The baseline predictor needs no native ML wheels; add `,ml` to install the
# heavy group once you wire a trained model.
RUN poetry install --only main --no-root

COPY src/common /app/common
COPY src/ml /app/ml
USER app

CMD ["uvicorn", "ml.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

LABEL org.opencontainers.image.title="neuroatlas-ml" \
      org.opencontainers.image.description="Outcome prediction with explainability"
