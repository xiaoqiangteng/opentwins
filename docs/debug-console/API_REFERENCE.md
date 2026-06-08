# Debug API 全量接口参考

## 基础信息

```text
Base URL: http://localhost:18080
Prefix:   /api/debug
用途:     只读调试、健康检查、短时监听、trace 记录
```

所有接口失败时会返回结构化错误；外部组件不可达时使用 `502`，错误原因在 `detail` 字段中。

## Health / Doctor

| 方法 | 路径 | 参数 | 说明 | 示例 |
| --- | --- | --- | --- | --- |
| GET | `/api/debug/health` | 无 | Debug API 自身健康检查 | `curl http://localhost:18080/api/debug/health` |
| GET | `/api/debug/doctor` | 无 | 一键检查 MQTT、Ditto、Connections、InfluxDB、Telegraf、Grafana | `curl http://localhost:18080/api/debug/doctor` |

`doctor` 返回组件状态：

```json
{
  "status": "warning",
  "checked_at": "2026-06-08T18:00:00+08:00",
  "components": [
    {"name": "mqtt", "status": "ok", "message": "reachable"},
    {"name": "ditto", "status": "ok", "message": "api reachable"}
  ]
}
```

## MQTT

| 方法 | 路径 | 参数 | 说明 | 示例 |
| --- | --- | --- | --- | --- |
| GET | `/api/debug/mqtt/status` | 无 | 检查 MQTT Broker TCP 可达性 | `curl http://localhost:18080/api/debug/mqtt/status` |
| GET | `/api/debug/mqtt/tail` | `topic`, `seconds`, `limit` | 短时间订阅 topic 并返回样例消息 | `curl 'http://localhost:18080/api/debug/mqtt/tail?topic=telemetry/%23&seconds=10&limit=20'` |

常用 `topic` 参数见 [Topic 查找表](TOPICS_IDS_MEASUREMENTS.md)。

## Ditto Things

| 方法 | 路径 | 参数 | 说明 | 示例 |
| --- | --- | --- | --- | --- |
| GET | `/api/debug/ditto/things/{thing_id}` | path `thing_id` | 查询 Ditto Thing 完整 JSON，并输出摘要 | `curl http://localhost:18080/api/debug/ditto/things/wine%3Atank_01` |
| GET | `/api/debug/ditto/things/{thing_id}/features/{feature}/value` | path `thing_id`, `feature` | 查询指定 feature 的 properties | `curl http://localhost:18080/api/debug/ditto/things/wine%3Atank_01/features/ph/value` |

注意：URL 中 `:` 需要编码为 `%3A`。`wmctl` 会自动处理编码。

## Ditto Connections

| 方法 | 路径 | 参数 | 说明 | 示例 |
| --- | --- | --- | --- | --- |
| GET | `/api/debug/ditto/connections` | 无 | 列出 Ditto Connections | `curl http://localhost:18080/api/debug/ditto/connections` |
| GET | `/api/debug/ditto/connections/{connection_id}/status` | path `connection_id` | 查询 Connection 状态 | `curl http://localhost:18080/api/debug/ditto/connections/mosquitto-source-connection/status` |
| GET | `/api/debug/ditto/connections/{connection_id}/metrics` | path `connection_id` | 查询 Connection metrics | `curl http://localhost:18080/api/debug/ditto/connections/mosquitto-source-connection/metrics` |
| GET | `/api/debug/ditto/connections/{connection_id}/logs` | path `connection_id` | 查询 Connection logs | `curl http://localhost:18080/api/debug/ditto/connections/mosquitto-source-connection/logs` |

当前 OpenTwins Chart 相关 connection 名称通常来自：

```text
mosquitto-source-connection
mosquitto-target-connection
hono-amqp-connection-for-<tenant>
hono-kafka-source-connection-for-<tenant>
```

以 `wmctl conn list` 的实际返回为准。

## InfluxDB

| 方法 | 路径 | 参数 | 说明 | 示例 |
| --- | --- | --- | --- | --- |
| GET | `/api/debug/influx/query` | `measurement`, `bucket`, `minutes` | 查询最近时序数据 | `curl 'http://localhost:18080/api/debug/influx/query?measurement=mqtt_consumer&minutes=60'` |

当前 Wine Demo 服务查询使用的 measurement 是 `mqtt_consumer`，tag 条件为 `thingId == "wine:{tank_id}"`。Debug API 当前只提供 measurement/time 范围查询；需要按 `thingId` 精确过滤时可直接使用 InfluxDB Flux。

## Grafana

| 方法 | 路径 | 参数 | 说明 | 示例 |
| --- | --- | --- | --- | --- |
| GET | `/api/debug/grafana/datasources` | 无 | 列出 Grafana datasources | `curl http://localhost:18080/api/debug/grafana/datasources` |

该接口需要 `GRAFANA_API_TOKEN`。没有 token 时，`doctor` 仍会通过 `/api/health` 检查 Grafana 可达性。

## Trace

| 方法 | 路径 | 参数 | 说明 | 示例 |
| --- | --- | --- | --- | --- |
| GET | `/api/debug/trace/{trace_id}` | path `trace_id` | 查询本地 trace 步骤 | `curl http://localhost:18080/api/debug/trace/trace_demo_001` |
| POST | `/api/debug/trace` | JSON body | 写入一条 trace 记录 | 见下方 |

写入示例：

```bash
curl -X POST http://localhost:18080/api/debug/trace \
  -H 'Content-Type: application/json' \
  -d '{
    "trace_id": "trace_demo_001",
    "stage": "mqtt",
    "status": "ok",
    "message": "message received",
    "payload": {"topic": "telemetry/wine/tank_01"}
  }'
```

## Logs

| 方法 | 路径 | 参数 | 说明 | 示例 |
| --- | --- | --- | --- | --- |
| GET | `/api/debug/logs/tail` | `path`, `lines` | 读取服务器本地日志尾部 | `curl 'http://localhost:18080/api/debug/logs/tail?path=/home/teng/programmings/git/opentwins/worldmind-debug/logs/worldmind-debug-api.log&lines=100'` |

该接口仅用于服务器本地调试。不要暴露到公网。
