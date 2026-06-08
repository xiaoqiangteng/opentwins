# OpenTwins 调试排障流程

## 用途

本文给出 OpenTwins + WineFermentTwin Demo 的标准排障顺序。所有排障都应逐段确认数据链路，而不是直接判断前端是否有数据。

## 安装

确保 Debug 工具链已安装：

```bash
cd /home/teng/programmings/git/opentwins
./deploy_all.sh --demo-only
```

## 配置

确认 Debug API 指向当前 OpenTwins NodePort：

```bash
worldmind-debug/cli/wmctl config show
curl http://localhost:18080/api/debug/health
```

## 启动

完整启动：

```bash
./deploy_all.sh
```

仅启动 Demo 与 Debug API：

```bash
./deploy_all.sh --demo-only
```

停止：

```bash
./stop_all.sh
```

查看日志：

```bash
./watch_demo.sh --status
./watch_demo.sh --debug --snapshot
```

## 常用命令

```bash
worldmind-debug/cli/wmctl doctor
worldmind-debug/cli/wmctl mqtt tail --topic 'telemetry/#' --seconds 10
worldmind-debug/cli/wmctl twin echo wine:tank_001
worldmind-debug/cli/wmctl conn list
worldmind-debug/cli/wmctl influx recent --measurement tank_001 --minutes 60
```

## 常见错误

- Demo 进程已停止：`./watch_demo.sh --status` 会显示 WineTwin Service、Frontend、Simulator 状态。
- MQTT 无消息：先看 `wine-ferment-twin/logs/wine-simulator.log`。
- Ditto Thing 不更新：检查 MQTT topic、Ditto Connection、policy 和 thingId。
- InfluxDB 无数据：检查 Telegraf pod、Influx token、bucket 和 measurement。
- Grafana 无图：先确认 InfluxDB query 返回数据，再检查 Grafana datasource。

## 排障步骤

1. 进程与服务状态：

```bash
./watch_demo.sh --status
```

2. Debug API 自检：

```bash
curl http://localhost:18080/api/debug/health
worldmind-debug/cli/wmctl doctor
```

3. 入口 MQTT：

```bash
worldmind-debug/cli/wmctl mqtt tail --topic 'telemetry/#' --seconds 10
```

4. Ditto 当前状态：

```bash
worldmind-debug/cli/wmctl twin echo wine:tank_001
worldmind-debug/cli/wmctl twin watch wine:tank_001 --feature ph --interval 2
```

5. Ditto Connection：

```bash
worldmind-debug/cli/wmctl conn list
worldmind-debug/cli/wmctl conn status mosquitto-source-connection
worldmind-debug/cli/wmctl conn metrics mosquitto-source-connection
worldmind-debug/cli/wmctl conn logs mosquitto-source-connection
```

6. InfluxDB：

```bash
worldmind-debug/cli/wmctl influx recent --measurement tank_001 --minutes 60
```

7. Trace：

```bash
worldmind-debug/cli/wmctl trace-add trace_demo_001 --stage mqtt --status ok --message 'message received'
worldmind-debug/cli/wmctl trace trace_demo_001
```

## 示例输出

```text
[OK]    mqtt: reachable
[OK]    ditto: api reachable: http://192.168.49.2:30525
[WARN]  ditto_connections: 未发现 Ditto Connections
[OK]    influxdb: reachable bucket=opentwins
[SKIP]  telegraf: kubectl 不可用或集群未响应，跳过 Telegraf 检查
[OK]    grafana: reachable: http://192.168.49.2:30718
Result: warning
```
