#!/usr/bin/env bash
# Build (if needed) and run the FinAlly Docker container.
set -euo pipefail

cd "$(dirname "$0")/.."

IMAGE_NAME="finally"
CONTAINER_NAME="finally"
PORT="8000"

BUILD=false
if [[ "${1:-}" == "--build" ]]; then
  BUILD=true
fi

if [[ ! -f .env ]]; then
  echo "No .env file found. Copying .env.example -> .env"
  cp .env.example .env
  echo "Edit .env and set OPENROUTER_API_KEY before using the AI chat."
fi

mkdir -p db

if $BUILD || [[ -z "$(docker images -q "$IMAGE_NAME" 2>/dev/null)" ]]; then
  echo "Building Docker image..."
  docker build -t "$IMAGE_NAME" .
fi

if [[ -n "$(docker ps -aq -f name="^${CONTAINER_NAME}$")" ]]; then
  echo "Removing existing container..."
  docker rm -f "$CONTAINER_NAME" >/dev/null
fi

echo "Starting container..."
docker run -d \
  --name "$CONTAINER_NAME" \
  -p "${PORT}:8000" \
  -v "$(pwd)/db:/app/db" \
  --env-file .env \
  "$IMAGE_NAME"

URL="http://localhost:${PORT}"
echo "FinAlly is running at ${URL}"

if command -v open >/dev/null 2>&1; then
  open "$URL"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL"
fi
