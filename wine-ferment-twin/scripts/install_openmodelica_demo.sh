#!/usr/bin/env bash
set -euo pipefail

OPENMODELICA_IMAGE="${OPENMODELICA_IMAGE:-openmodelica/openmodelica:v1.26.7-minimal}"

echo "[1/2] Pulling OpenModelica image: ${OPENMODELICA_IMAGE}"
docker pull "$OPENMODELICA_IMAGE"

echo "[2/2] Checking omc version"
docker run --rm "$OPENMODELICA_IMAGE" omc --version
