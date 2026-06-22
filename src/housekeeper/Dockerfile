ARG BASE_IMAGE=python:3.12-slim-bookworm
FROM ${BASE_IMAGE}

ENV POETRY_VIRTUALENVS_CREATE=false
# Mirror the local layout (src/ on the path) so one alembic.ini works in both
# the container and locally; the runtime entrypoint imports `housekeeper.*`.
ENV PYTHONPATH=/app/src
WORKDIR /app

RUN groupadd --gid 2000 app \
    && useradd --uid 2000 --gid app --shell /bin/bash --create-home app \
    && chown -R app /app \
    && pip install poetry

COPY pyproject.toml poetry.lock* /app/
RUN poetry install --only main,housekeeper --no-root

COPY alembic.ini /app/alembic.ini
COPY src/common /app/src/common
COPY src/housekeeper /app/src/housekeeper
COPY src/common/application/healthcheck.py /app/healthcheck.py
USER app

CMD ["uvicorn", "housekeeper.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

LABEL org.opencontainers.image.title="neuroatlas-housekeeper" \
      org.opencontainers.image.description="Database operations & migrations service"
