ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION} as builder

WORKDIR /app

RUN pip install -U pdm

COPY ./pyproject.toml ./pyproject.toml
COPY ./pdm.lock ./pdm.lock

RUN pdm install

FROM python:${PYTHON_VERSION}-slim as prod

WORKDIR /app

ARG COMMIT_HASH
ENV COMMIT_HASH=${COMMIT_HASH:-NotSetCommitHash}

COPY --from=builder /app/.venv /app/.venv
COPY . .

CMD ["./.venv/bin/python", "./main.py"]
