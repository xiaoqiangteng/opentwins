# Debug 排障流程

## 标准顺序

1. 进程和端口。
2. MQTT 是否收到 Wine Simulator 数据。
3. Ditto Thing 是否更新。
4. Ditto Connection 是否正常。
5. Telegraf 是否转发 Ditto Events。
6. InfluxDB 是否有时序数据。
7. Grafana 查询是否正确。
8. Debug API / wmctl 是否能读取上述状态。

## 一组完整排查命令

```bash
cd /home/teng/programmings/git/opentwins
./watch_demo.sh --status
curl http://localhost:18080/api/debug/health
worldmind-debug/cli/wmctl doctor
worldmind-debug/cli/wmctl mqtt tail --topic 'telemetry/wine/#' --seconds 10
worldmind-debug/cli/wmctl twin echo wine:tank_01
worldmind-debug/cli/wmctl conn list
worldmind-debug/cli/wmctl influx recent --measurement mqtt_consumer --minutes 60
```

## 判断路径

| 现象 | 优先检查 |
| --- | --- |
| Debug API 不通 | `worldmind-debug/logs/worldmind-debug-api.log`，端口 `18080` |
| MQTT 不通 | `MQTT_HOST`、`MQTT_PORT=30511`、minikube NodePort |
| MQTT 无消息 | Wine Simulator 进程与 `wine-simulator.log` |
| MQTT 有消息，Ditto 不更新 | Ditto Connection status/metrics/logs |
| Ditto 更新，InfluxDB 无数据 | Telegraf pod、Influx token、bucket、measurement |
| InfluxDB 有数据，Grafana 无图 | Grafana datasource 与 panel query |

## Debug trace 示例

```bash
worldmind-debug/cli/wmctl trace-add trace_tank_01 \
  --stage mqtt \
  --status ok \
  --message 'received tank telemetry' \
  --payload '{"topic":"telemetry/wine/tank_01","thingId":"wine:tank_01"}'

worldmind-debug/cli/wmctl trace trace_tank_01
```
