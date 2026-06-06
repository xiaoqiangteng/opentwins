#!/usr/bin/env bash
set -euo pipefail
HOST_IP="127.0.0.1"; OPENTWINS_HOST_IP=""
while [[ $# -gt 0 ]]; do case "$1" in --host-ip) HOST_IP="$2"; shift 2;; --opentwins-host-ip) OPENTWINS_HOST_IP="$2"; shift 2;; *) shift;; esac; done
[[ -z "$OPENTWINS_HOST_IP" ]] && OPENTWINS_HOST_IP="$HOST_IP"
echo "WineFermentTwin Demo URLs"
echo "Frontend:              http://${HOST_IP}:5173"
echo "WineTwin Service API:   http://${HOST_IP}:8010/docs"
echo "Modelica Service API:   http://${HOST_IP}:8020/docs"
echo "Grafana/OpenTwins:      http://${OPENTWINS_HOST_IP}:30718"
echo "Ditto API:              http://${OPENTWINS_HOST_IP}:30525"
echo "Extended API:           http://${OPENTWINS_HOST_IP}:30526"
echo "InfluxDB:               http://${OPENTWINS_HOST_IP}:30716"
echo "Mosquitto MQTT:         ${OPENTWINS_HOST_IP}:30511"
