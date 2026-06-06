#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
for f in logs/winetwin-service.pid logs/wine-frontend.pid logs/wine-simulator.pid logs/modelica-service.pid; do
  if [[ -f "$f" ]]; then pid="$(cat "$f")"; kill "$pid" 2>/dev/null || true; rm -f "$f"; fi
done
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "wine_fermentation_simulator.py" 2>/dev/null || true
pkill -f "vite.*5173" 2>/dev/null || true
docker rm -f "${MODELICA_SERVICE_CONTAINER_NAME:-modelica-simulation-service}" >/dev/null 2>&1 || true
echo "WineFermentTwin demo stopped."
