# WorldMind Debug Console 使用说明

## 用途

WorldMind Debug Console 是 OpenTwins 与 WineFermentTwin Demo 的旁路调试服务。它通过 FastAPI 暴露 `/api/debug` 接口，用于健康检查、Ditto Thing 查询、Ditto Connection 查询、MQTT tail、InfluxDB 查询、Grafana 数据源检查和本地 trace 记录。

## 安装

推荐使用一键部署脚本：

```bash
cd /home/teng/programmings/git/opentwins
./deploy_all.sh --demo-only
```

手动安装：

```bash
cd /home/teng/programmings/git/opentwins/worldmind-debug/backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## 配置

所有连接信息来自环境变量，不硬编码服务器 IP、账号或密码。

```bash
cd /home/teng/programmings/git/opentwins/worldmind-debug
cp .env.example .env
```

关键配置：

```text
DEBUG_API_PORT=18080
DITTO_BASE_URL=http://<OPENTWINS_HOST_IP>:30525
MQTT_HOST=<OPENTWINS_HOST_IP>
MQTT_PORT=30511
INFLUX_URL=http://<OPENTWINS_HOST_IP>:30716
GRAFANA_URL=http://<OPENTWINS_HOST_IP>:30718
TRACE_DB_PATH=./data/debug_trace.sqlite
```

## 启动

一键启动：

```bash
cd /home/teng/programmings/git/opentwins
./deploy_all.sh --demo-only
```

手动启动：

```bash
cd /home/teng/programmings/git/opentwins/worldmind-debug/backend
. .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 18080
```

健康检查：

```bash
curl http://localhost:18080/api/debug/health
```

## 常用命令

```bash
curl http://localhost:18080/api/debug/doctor
curl http://localhost:18080/api/debug/mqtt/status
curl 'http://localhost:18080/api/debug/mqtt/tail?topic=telemetry/%23&seconds=10'
curl http://localhost:18080/api/debug/ditto/things/wine%3Atank_001
curl http://localhost:18080/api/debug/ditto/connections
curl 'http://localhost:18080/api/debug/influx/query?measurement=tank_001&minutes=60'
curl http://localhost:18080/api/debug/grafana/datasources
```

## 常见错误

- `502 Ditto HTTP 401/403`：检查 `DITTO_USER`、`DITTO_PASSWORD`、`DITTO_DEVOPS_USER`、`DITTO_DEVOPS_PASSWORD`。
- `MQTT 不可达`：检查 `MQTT_HOST` 和 `MQTT_PORT`，当前 OpenTwins 使用 NodePort `30511`。
- `INFLUX_TOKEN 未配置`：只可做 health，不能做 Flux query。
- `Grafana datasources HTTP 401`：需要配置 `GRAFANA_API_TOKEN`。
- `kubectl 不可用或集群未响应`：Telegraf 检查会显示 skipped，不影响其他检查。

## 排障步骤

1. `GET /api/debug/health` 确认 Debug API 自身启动。
2. `GET /api/debug/doctor` 获取整体状态。
3. `GET /api/debug/mqtt/tail` 确认入口 topic 有数据。
4. `GET /api/debug/ditto/things/{thing_id}` 确认 Ditto Thing 被更新。
5. `GET /api/debug/ditto/connections` 和 connection status/metrics/logs 检查连接消费。
6. `GET /api/debug/influx/query` 确认时序数据。
7. `GET /api/debug/grafana/datasources` 检查 Grafana 数据源。

## 示例输出

```json
{
  "status": "ok",
  "service": "worldmind-debug-api",
  "time": "2026-06-08T18:00:00+08:00"
}
```
