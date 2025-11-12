FROM python:3.14-slim AS base

ENV POETRY_HOME=/opt/poetry
ENV PATH="$POETRY_HOME/bin:$PATH" \
    POETRY_VIRTUALENVS_IN_PROJECT=true

RUN python3 -m venv $POETRY_HOME \
    && $POETRY_HOME/bin/pip install --no-cache-dir -U pip setuptools \
    && $POETRY_HOME/bin/pip install --no-cache-dir "poetry>=2,<3"

WORKDIR /app

COPY pyproject.toml poetry.lock* /app/
RUN poetry install --only main


FROM python:3.14-slim

WORKDIR /app

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY . /app
COPY --from=base /app/.venv /app/.venv

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
