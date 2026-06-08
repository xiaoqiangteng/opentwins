# 部署命令与 Debug 使用说明

## 用途

本文是部署维护人员的快速操作手册，覆盖一键部署、一键停止、实时日志、Debug API 和 `wmctl` 示例。

## 安装

```bash
cd /home/teng/programmings/git/opentwins
./deploy_all.sh
```

## 配置

一键部署会自动根据 `OPENTWINS_HOST_IP` 注入 Debug API 运行时配置。需要手动覆盖时编辑：

```bash
/home/teng/programmings/git/opentwins/worldmind-debug/.env
```

## 启动

完整部署：

```bash
cd /home/teng/programmings/git/opentwins
./deploy_all.sh
```

仅 OpenTwins 基础设施：

```bash
./deploy_all.sh --infra-only
```

仅 Wine Demo + Debug 工具：

```bash
./deploy_all.sh --demo-only
```

跳过 Debug 工具：

```bash
./deploy_all.sh --skip-debug
```

## 停止

停止 Demo 和 Debug API：

```bash
./stop_all.sh
```

停止 Demo、Debug API 并卸载 OpenTwins：

```bash
./stop_all.sh --infra
```

## 查看日志

```bash
./watch_demo.sh --status
./watch_demo.sh --debug --snapshot
./watch_demo.sh --debug
```

## 常用 Debug 命令

```bash
worldmind-debug/cli/wmctl doctor
worldmind-debug/cli/wmctl mqtt tail --topic 'telemetry/#' --seconds 10
worldmind-debug/cli/wmctl twin echo wine:tank_001
worldmind-debug/cli/wmctl twin watch wine:tank_001 --feature ph --interval 2
worldmind-debug/cli/wmctl conn list
worldmind-debug/cli/wmctl influx recent --measurement tank_001 --minutes 60
worldmind-debug/cli/wmctl trace trace_demo_001
```

## 常见错误

- `Debug API 不可达`：看 `worldmind-debug/logs/worldmind-debug-api.log`。
- `wmctl doctor` 中 Ditto error：确认 `http://<OPENTWINS_HOST_IP>:30525/api/2/things`。
- `MQTT tail 未收到消息`：确认 Wine Simulator 正在运行。
- `InfluxDB 查询为空`：确认 Telegraf 和 Influx token。

## 排障步骤

1. `./watch_demo.sh --status`
2. `curl http://localhost:18080/api/debug/health`
3. `worldmind-debug/cli/wmctl doctor`
4. `worldmind-debug/cli/wmctl mqtt tail --topic 'telemetry/#' --seconds 10`
5. `worldmind-debug/cli/wmctl twin echo wine:tank_001`
6. `worldmind-debug/cli/wmctl influx recent --measurement tank_001 --minutes 60`

## Debug 示例

问题：Grafana 图表没有最新数据。

```bash
worldmind-debug/cli/wmctl doctor
worldmind-debug/cli/wmctl mqtt tail --topic 'telemetry/#' --seconds 10
worldmind-debug/cli/wmctl twin echo wine:tank_001
worldmind-debug/cli/wmctl influx recent --measurement tank_001 --minutes 60
```

判断：

```text
MQTT 有消息，但 Ditto Thing 不更新：优先查 Ditto Connection。
Ditto Thing 更新，但 InfluxDB 为空：优先查 Telegraf 和 bucket/measurement。
InfluxDB 有数据，但 Grafana 无图：优先查 Grafana datasource 和 panel query。
```
