ARG BASE_IMAGE=python:3.12-slim-bookworm
FROM node:20-alpine AS ui-build

WORKDIR /ui
COPY src/admin_ui/ui/package.json /ui/
RUN npm install
COPY src/admin_ui/ui/ /ui/
RUN npm run build

FROM ${BASE_IMAGE}

ENV POETRY_VIRTUALENVS_CREATE=false
WORKDIR /app

RUN groupadd --gid 2000 app \
    && useradd --uid 2000 --gid app --shell /bin/bash --create-home app \
    && chown -R app /app \
    && pip install poetry

COPY pyproject.toml poetry.lock* /app/
RUN poetry install --only main --no-root

COPY src/common /app/common
COPY src/admin_ui /app/admin_ui
COPY --from=ui-build /ui/build /app/admin_ui/frontend
COPY src/common/application/healthcheck.py /app/healthcheck.py
USER app

CMD ["uvicorn", "admin_ui.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

LABEL org.opencontainers.image.title="neuroatlas-admin-ui" \
      org.opencontainers.image.description="Admin panel BFF: OIDC session, guard proxy, embedded React UI"
