# WorldMind Debug Console / wmctl

## 用途

`worldmind-debug` 是 OpenTwins + WineFermentTwin Demo 的旁路调试工具链，提供类似 ROS `rostopic echo`、`rostopic hz`、`rosnode info` 的观测能力。本模块只读访问 OpenTwins、Ditto、MQTT、InfluxDB、Grafana、Telegraf，不修改 OpenTwins 核心部署架构。

## 安装

一键部署脚本已集成 Debug API：

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

配置全部通过环境变量读取。示例文件：

```bash
cd /home/teng/programmings/git/opentwins/worldmind-debug
cp .env.example .env
```

当前部署常用配置：

```bash
DITTO_BASE_URL=http://192.168.49.2:30525
MQTT_HOST=192.168.49.2
MQTT_PORT=30511
INFLUX_URL=http://192.168.49.2:30716
GRAFANA_URL=http://192.168.49.2:30718
TRACE_DB_PATH=/home/teng/programmings/git/opentwins/worldmind-debug/data/debug_trace.sqlite
```

## 启动

```bash
cd /home/teng/programmings/git/opentwins
./deploy_all.sh --demo-only
curl http://localhost:18080/api/debug/health
```

## 常用命令

```bash
cd /home/teng/programmings/git/opentwins
worldmind-debug/cli/wmctl doctor
worldmind-debug/cli/wmctl mqtt tail --topic 'telemetry/#' --seconds 10
worldmind-debug/cli/wmctl twin echo wine:tank_001
worldmind-debug/cli/wmctl twin watch wine:tank_001 --feature ph --interval 2
worldmind-debug/cli/wmctl conn list
worldmind-debug/cli/wmctl influx recent --measurement tank_001 --minutes 60
worldmind-debug/cli/wmctl trace trace_20260608_0001
```

## 常见错误

- `Ditto API 不可达`：先运行 `./watch_demo.sh --status`，确认 minikube IP 与 `30525` 是否可访问。
- `MQTT tail 失败`：确认 `MQTT_HOST`、`MQTT_PORT=30511`，并检查 Mosquitto NodePort。
- `INFLUX_TOKEN 未配置`：从 `OpenTwins/values.yaml` 的 `influxdb2.adminUser.token` 配置同步到 `.env`。
- `Grafana API Token 未配置或无权限`：`doctor` 只依赖 `/api/health`，数据源列表需要配置 `GRAFANA_API_TOKEN`。

## 排障步骤

标准顺序：

1. 容器/进程是否运行。
2. MQTT 是否收到 Wine Simulator 数据。
3. Ditto Thing 是否更新。
4. Ditto Connection 是否正常。
5. Telegraf 是否运行并转发。
6. InfluxDB 是否有最近数据。
7. Grafana 数据源是否可用。
8. Debug API 与 `wmctl` 是否能读取上述状态。

## 示例输出

```text
$ worldmind-debug/cli/wmctl doctor
[OK]    mqtt: reachable
[OK]    ditto: api reachable: http://192.168.49.2:30525
[OK]    ditto_connections: connections=2
[OK]    influxdb: reachable bucket=opentwins
[WARN]  telegraf: kubectl 不可用或集群未响应，跳过 Telegraf 检查
[OK]    grafana: reachable: http://192.168.49.2:30718
Result: warning
```
