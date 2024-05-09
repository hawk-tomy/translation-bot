#!/bin/bash
set -euo pipefail

docker compose build --build-arg COMMIT_HASH=$(git rev-parse --short HEAD)
docker compose up -d
docker compose logs -f
