# WineFermentTwin

WineFermentTwin 是基于当前 OpenTwins 部署扩展的葡萄酒发酵过程数字孪生 Demo。它不重写 OpenTwins 底座，而是作为 Companion Service 增加葡萄酒业务层、模拟数据源和 ThreeJS 可视化。

## Architecture

```text
wine-simulator
  -> Mosquitto MQTT telemetry/wine/<tank_id>
  -> Eclipse Ditto updates wine:tank_01..03 Features
  -> Ditto target connection publishes opentwins/#
  -> Telegraf parses messages
  -> InfluxDB stores history

WineTwin Service
  -> reads Ditto current Twin state
  -> reads InfluxDB history when token is configured
  -> computes stage, risk, quality score, alarms, prediction, recommendations
  -> exposes REST API to the frontend

wine-frontend
  -> Vite + React + ThreeJS + ECharts
  -> calls only WineTwin Service APIs
```

## Quick Start

```bash
cd /home/teng/programmings/git/opentwins/wine-ferment-twin
./scripts/deploy_demo.sh --host-ip 10.168.1.102 --opentwins-host-ip 192.168.49.2
```

Open:

- Frontend: `http://10.168.1.102:5173`
- API docs: `http://10.168.1.102:8010/docs`
- OpenTwins/Grafana: `http://192.168.49.2:30718`

## Directory

- `configs/`: simulator config, Twin schema, alarm rules, service config.
- `wine-init/`: idempotent Type/Twin initialization and verification scripts.
- `wine-simulator/`: fermentation model, anomaly injector, MQTT publisher, CSV output.
- `winetwin-service/`: FastAPI business service for Ditto/Influx/rules/prediction APIs.
- `wine-frontend/`: Vite React frontend with ThreeJS workshop and ECharts trends.
- `scripts/`: deployment, stop, OpenTwins checks, simulator runner, access URL printer.
- `logs/`: runtime logs.

## Ports

- `5173`: ThreeJS frontend.
- `8010`: WineTwin Service API.
- `30525`: Ditto API.
- `30526`: Extended API.
- `30511`: Mosquitto MQTT.
- `30716`: InfluxDB.
- `30718`: Grafana/OpenTwins.

## Real Sensor Integration

真实传感器接入时只需要替换 `wine-simulator` 的数据来源。硬件采集程序继续向 MQTT 发布 Ditto Protocol merge-patch 消息即可：

- Topic: `telemetry/wine/<tank_id>`
- Payload `topic`: `wine/<tank_id>/things/twin/commands/merge`
- Payload `path`: `/features`
- Header `content-type`: `application/merge-patch+json`

只要保持 Feature 名称和数据格式不变，WineTwin Service 和前端无需重写。

