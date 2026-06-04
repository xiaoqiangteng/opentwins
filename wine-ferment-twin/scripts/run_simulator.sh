#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_IP="${OPENTWINS_HOST_IP:-${HOST_IP:-127.0.0.1}}"
while [[ $# -gt 0 ]]; do case "$1" in --host-ip|--opentwins-host-ip) HOST_IP="$2"; shift 2;; *) echo "Unknown argument: $1"; exit 1;; esac; done
cd "$ROOT_DIR"; mkdir -p logs
export MQTT_HOST="$HOST_IP" MQTT_PORT="${MQTT_PORT:-30511}"
exec python3 wine-simulator/wine_fermentation_simulator.py --config configs/wine_simulation.yaml
