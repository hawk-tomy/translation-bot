FROM ghcr.io/astral-sh/uv:python3.12-trixie AS builder

WORKDIR /app

COPY ./pyproject.toml ./pyproject.toml
COPY ./uv.lock ./uv.lock

RUN uv sync --frozen


FROM python:3.12-slim-trixie AS prod

ARG COMMIT_HASH
ENV COMMIT_HASH=${COMMIT_HASH:-NotSetCommitHash}

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY . .

CMD ["./.venv/bin/python", "./main.py"]
