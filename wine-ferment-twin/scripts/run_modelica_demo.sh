#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

OPENMODELICA_IMAGE="${OPENMODELICA_IMAGE:-openmodelica/openmodelica:v1.26.7-minimal}"
mkdir -p modelica/results

echo "[1/3] Checking OpenModelica version..."
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work -w /work "$OPENMODELICA_IMAGE" omc --version

echo "[2/3] Running HelloWine Modelica demo..."
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work -w /work "$OPENMODELICA_IMAGE" omc modelica/scripts/run_hello_wine.mos

echo "[3/3] Moving result files..."
shopt -s nullglob
for f in WineFermentation.HelloWine_res.csv WineFermentation.HelloWine_res.mat; do
  if [ -f "$f" ]; then
    mv "$f" modelica/results/
  fi
done

echo "OpenModelica demo finished. Result directory: modelica/results"
ls -lah modelica/results || true
