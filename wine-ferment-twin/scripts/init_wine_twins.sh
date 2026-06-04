#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_IP="${OPENTWINS_HOST_IP:-${HOST_IP:-127.0.0.1}}"
while [[ $# -gt 0 ]]; do case "$1" in --host-ip|--opentwins-host-ip) HOST_IP="$2"; shift 2;; *) echo "Unknown argument: $1"; exit 1;; esac; done
cd "$ROOT_DIR"
python3 wine-init/init_wine_types.py --ditto-url "http://${HOST_IP}:30525" --extended-api "http://${HOST_IP}:30526" --username "${DITTO_USERNAME:-ditto}" --password "${DITTO_PASSWORD:-ditto}"
python3 wine-init/create_wine_twins.py --schema configs/wine_twin_schema.json --ditto-url "http://${HOST_IP}:30525" --username "${DITTO_USERNAME:-ditto}" --password "${DITTO_PASSWORD:-ditto}"
python3 wine-init/verify_wine_twins.py --ditto-url "http://${HOST_IP}:30525" --username "${DITTO_USERNAME:-ditto}" --password "${DITTO_PASSWORD:-ditto}"
