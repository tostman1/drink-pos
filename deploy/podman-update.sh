#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=${PROJECT_DIR:-$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)}
COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.yml}

cd "$PROJECT_DIR"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

: "${DRINK_POS_IMAGE:?Set DRINK_POS_IMAGE=ghcr.io/<github-owner>/drink-pos:latest in .env}"

podman pull "$DRINK_POS_IMAGE"

if podman compose version >/dev/null 2>&1; then
  podman compose -f "$COMPOSE_FILE" up -d --remove-orphans --force-recreate
elif command -v podman-compose >/dev/null 2>&1; then
  podman-compose -f "$COMPOSE_FILE" up -d --force-recreate
else
  echo "podman compose or podman-compose is required." >&2
  exit 1
fi

podman image prune -f
