#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_IP="$(hostname -I | awk '{print $1}')"
OPENTWINS_HOST_IP=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host-ip) HOST_IP="$2"; shift 2 ;;
    --opentwins-host-ip) OPENTWINS_HOST_IP="$2"; shift 2 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

if [[ -z "$OPENTWINS_HOST_IP" ]]; then
  OPENTWINS_HOST_IP="$HOST_IP"
  if ! curl -fsS --max-time 3 -u "${DITTO_USERNAME:-ditto}:${DITTO_PASSWORD:-ditto}" "http://${OPENTWINS_HOST_IP}:30525/api/2/things" >/dev/null 2>&1 && command -v minikube >/dev/null 2>&1; then
    MK_IP="$(minikube ip 2>/dev/null || true)"
    [[ -n "$MK_IP" ]] && OPENTWINS_HOST_IP="$MK_IP"
  fi
fi

export HOST_IP OPENTWINS_HOST_IP
export DITTO_BASE_URL="http://${OPENTWINS_HOST_IP}:30525"
export EXTENDED_API_URL="http://${OPENTWINS_HOST_IP}:30526"
export MQTT_HOST="${OPENTWINS_HOST_IP}"
export MQTT_PORT="30511"
export INFLUX_URL="http://${OPENTWINS_HOST_IP}:30716"
if [[ -z "${INFLUX_TOKEN:-}" && -f "${ROOT_DIR}/../OpenTwins/values.yaml" ]]; then
  INFLUX_TOKEN="$(awk '/adminUser:/{in_admin=1} in_admin && /^[[:space:]]+token:/{gsub(/^[[:space:]]+token:[[:space:]]*"/,""); gsub(/"[[:space:]]*$/,""); print; exit}' "${ROOT_DIR}/../OpenTwins/values.yaml")"
fi
export INFLUX_TOKEN="${INFLUX_TOKEN:-}"
export WINE_SERVICE_URL="http://${HOST_IP}:8010"
export WINE_SERVICE_HOST="0.0.0.0"
export WINE_SERVICE_PORT="8010"
export CORS_ALLOW_ORIGINS="*"

cd "$ROOT_DIR"
mkdir -p logs
bash scripts/check_opentwins.sh --opentwins-host-ip "$OPENTWINS_HOST_IP"

PYTHON_BIN="python3"
if python3 -m venv .venv >/dev/null 2>&1; then
  source .venv/bin/activate
  PYTHON_BIN="python"
  python -m pip install --upgrade pip
  pip install -r wine-init/requirements.txt -r wine-simulator/requirements.txt -r winetwin-service/requirements.txt
else
  echo "python3-venv is not available; falling back to python3 -m pip --user"
  python3 -m pip install --user -r wine-init/requirements.txt -r wine-simulator/requirements.txt -r winetwin-service/requirements.txt
fi

"$PYTHON_BIN" wine-init/init_wine_types.py --ditto-url "$DITTO_BASE_URL" --extended-api "$EXTENDED_API_URL" --username "${DITTO_USERNAME:-ditto}" --password "${DITTO_PASSWORD:-ditto}"
"$PYTHON_BIN" wine-init/create_wine_twins.py --schema configs/wine_twin_schema.json --ditto-url "$DITTO_BASE_URL" --username "${DITTO_USERNAME:-ditto}" --password "${DITTO_PASSWORD:-ditto}"
"$PYTHON_BIN" wine-init/verify_wine_twins.py --ditto-url "$DITTO_BASE_URL" --username "${DITTO_USERNAME:-ditto}" --password "${DITTO_PASSWORD:-ditto}"

bash scripts/stop_demo.sh >/dev/null 2>&1 || true

(cd winetwin-service && DITTO_BASE_URL="$DITTO_BASE_URL" INFLUX_URL="$INFLUX_URL" INFLUX_TOKEN="$INFLUX_TOKEN" CORS_ALLOW_ORIGINS="$CORS_ALLOW_ORIGINS" setsid -f "$PYTHON_BIN" -m uvicorn app.main:app --host 0.0.0.0 --port 8010 > "$ROOT_DIR/logs/winetwin-service.log" 2>&1 < /dev/null)
(cd wine-frontend && npm install && VITE_API_BASE_URL="http://127.0.0.1:8010" setsid -f npm run dev -- --host 0.0.0.0 --port 5173 > "$ROOT_DIR/logs/wine-frontend.log" 2>&1 < /dev/null)
MQTT_HOST="$MQTT_HOST" MQTT_PORT="$MQTT_PORT" setsid -f "$PYTHON_BIN" wine-simulator/wine_fermentation_simulator.py --config configs/wine_simulation.yaml > logs/wine-simulator.log 2>&1 < /dev/null

sleep 2
bash scripts/print_access_urls.sh --host-ip "$HOST_IP" --opentwins-host-ip "$OPENTWINS_HOST_IP"
