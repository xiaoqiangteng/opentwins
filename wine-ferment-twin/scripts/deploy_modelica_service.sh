#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

OPENMODELICA_IMAGE="${OPENMODELICA_IMAGE:-openmodelica/openmodelica:v1.26.7-minimal}"
IMAGE_NAME="${MODELICA_SERVICE_IMAGE_NAME:-wine-modelica-simulation-service:latest}"
CONTAINER_NAME="${MODELICA_SERVICE_CONTAINER_NAME:-modelica-simulation-service}"
PORT="${MODELICA_SERVICE_PORT:-8020}"

mkdir -p logs

echo "[1/4] Building Modelica Simulation Service image"
docker build \
  --build-arg OPENMODELICA_IMAGE="$OPENMODELICA_IMAGE" \
  -f simulation-service/Dockerfile \
  -t "$IMAGE_NAME" \
  .

echo "[2/4] Replacing old container if present"
docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

echo "[3/4] Starting Modelica Simulation Service on 0.0.0.0:${PORT}"
docker run -d \
  --name "$CONTAINER_NAME" \
  --restart unless-stopped \
  -p "${PORT}:8020" \
  -e MODEL_ROOT=/app \
  -e MODELICA_TIMEOUT_SECONDS="${MODELICA_TIMEOUT_SECONDS:-120}" \
  "$IMAGE_NAME" >/dev/null

echo "[4/4] Waiting for health"
for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
    curl -fsS "http://127.0.0.1:${PORT}/health"
    echo ""
    echo "Modelica Simulation Service is ready: http://127.0.0.1:${PORT}/docs"
    exit 0
  fi
  sleep 2
done

echo "ERROR: Modelica Simulation Service did not become healthy"
docker logs --tail 80 "$CONTAINER_NAME" || true
exit 1
