FROM python:3.12

ARG COMMIT_HASH
ENV COMMIT_HASH=${COMMIT_HASH:-NotSetCommitHash}

WORKDIR /app

RUN pip install -U pdm

COPY ./pyproject.toml ./pyproject.toml
COPY ./pdm.lock ./pdm.lock

RUN pdm install

COPY . .

CMD ["./.venv/bin/python", "./main.py"]
