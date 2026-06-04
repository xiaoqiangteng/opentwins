#!/usr/bin/env bash
set -euo pipefail

HOST_IP="127.0.0.1"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --host-ip|--opentwins-host-ip) HOST_IP="$2"; shift 2 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

DITTO_USER="${DITTO_USERNAME:-ditto}"
DITTO_PASS="${DITTO_PASSWORD:-ditto}"

echo "Checking OpenTwins services at ${HOST_IP}"

check_http() {
  local name="$1" url="$2" auth="${3:-noauth}"
  local args=(-fsS --max-time 5)
  if [[ "$auth" == "auth" ]]; then
    args+=(-u "${DITTO_USER}:${DITTO_PASS}")
  fi
  if curl "${args[@]}" "$url" >/dev/null; then
    echo "OK   ${name}: ${url}"
  else
    echo "FAIL ${name}: ${url}"
    return 1
  fi
}

check_tcp() {
  local name="$1" host="$2" port="$3"
  if timeout 4 bash -c "</dev/tcp/${host}/${port}" 2>/dev/null; then
    echo "OK   ${name}: ${host}:${port}"
  else
    echo "FAIL ${name}: ${host}:${port}"
    return 1
  fi
}

check_http "Ditto API" "http://${HOST_IP}:30525/api/2/things" auth
check_http "Extended API" "http://${HOST_IP}:30526" noauth || true
check_http "InfluxDB" "http://${HOST_IP}:30716/health" noauth || true
check_http "Grafana" "http://${HOST_IP}:30718/login" noauth || true
check_tcp "Mosquitto MQTT" "${HOST_IP}" "30511"
