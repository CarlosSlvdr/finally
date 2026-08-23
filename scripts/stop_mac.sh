#!/usr/bin/env bash
# Stop and remove the FinAlly container. Data in db/ is preserved.
set -euo pipefail

CONTAINER_NAME="finally"

if [[ -n "$(docker ps -aq -f name="^${CONTAINER_NAME}$")" ]]; then
  echo "Stopping FinAlly container..."
  docker rm -f "$CONTAINER_NAME" >/dev/null
  echo "Stopped."
else
  echo "FinAlly container is not running."
fi
