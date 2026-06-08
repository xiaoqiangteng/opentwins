# wmctl 命令全量参考

## 基础配置

```bash
export WM_DEBUG_API_URL=http://localhost:18080/api/debug
export WM_DEBUG_TIMEOUT=20
```

查看当前配置：

```bash
worldmind-debug/cli/wmctl config show
```

## doctor

```bash
worldmind-debug/cli/wmctl doctor
```

检查组件：

```text
MQTT
Ditto API
Ditto Connections
InfluxDB
Telegraf
Grafana
```

## mqtt tail

```bash
worldmind-debug/cli/wmctl mqtt tail --topic 'telemetry/#' --seconds 10 --limit 20
```

参数：

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--topic` | `telemetry/#` | MQTT 订阅 topic，支持 `#` 与 `+` 通配 |
| `--seconds` | `10` | 监听秒数 |
| `--limit` | `20` | 最多返回消息数 |

常用 topic：

```bash
worldmind-debug/cli/wmctl mqtt tail --topic 'telemetry/#' --seconds 10
worldmind-debug/cli/wmctl mqtt tail --topic 'telemetry/wine/#' --seconds 10
worldmind-debug/cli/wmctl mqtt tail --topic 'telemetry/wine/+' --seconds 10
worldmind-debug/cli/wmctl mqtt tail --topic 'telemetry/wine/tank_01' --seconds 10
worldmind-debug/cli/wmctl mqtt tail --topic 'telemetry/wine/tank_02' --seconds 10
worldmind-debug/cli/wmctl mqtt tail --topic 'telemetry/wine/tank_03' --seconds 10
```

## twin echo

```bash
worldmind-debug/cli/wmctl twin echo wine:tank_01
```

常用 thingId：

```bash
worldmind-debug/cli/wmctl twin echo wine:winery_01
worldmind-debug/cli/wmctl twin echo wine:workshop_01
worldmind-debug/cli/wmctl twin echo wine:tank_01
worldmind-debug/cli/wmctl twin echo wine:tank_02
worldmind-debug/cli/wmctl twin echo wine:tank_03
```

## twin watch

```bash
worldmind-debug/cli/wmctl twin watch wine:tank_01 --feature ph --interval 2
```

常用 feature：

```text
temperature
ph
brix
specific_gravity
co2
pressure
liquid_level
alcohol_estimation
fermentation_progress
fermentation_stage
quality_score
risk_level
recommendation
status
tank_count
```

示例：

```bash
worldmind-debug/cli/wmctl twin watch wine:tank_01 --feature temperature --interval 2
worldmind-debug/cli/wmctl twin watch wine:tank_02 --feature risk_level --interval 2
worldmind-debug/cli/wmctl twin watch wine:tank_03 --feature fermentation_progress --interval 5
```

## conn

```bash
worldmind-debug/cli/wmctl conn list
worldmind-debug/cli/wmctl conn status mosquitto-source-connection
worldmind-debug/cli/wmctl conn metrics mosquitto-source-connection
worldmind-debug/cli/wmctl conn logs mosquitto-source-connection
```

实际 connectionId 以 `conn list` 返回为准。

## influx recent

```bash
worldmind-debug/cli/wmctl influx recent --measurement mqtt_consumer --minutes 60
```

参数：

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--measurement` | 必填 | InfluxDB measurement |
| `--bucket` | `.env` 中 `INFLUX_BUCKET` | InfluxDB bucket |
| `--minutes` | `60` | 查询最近 N 分钟 |

当前 Wine Demo 代码中的 Influx measurement：

```text
mqtt_consumer
```

## trace

写入 trace：

```bash
worldmind-debug/cli/wmctl trace-add trace_demo_001 \
  --stage mqtt \
  --status ok \
  --message 'message received' \
  --payload '{"topic":"telemetry/wine/tank_01"}'
```

查询 trace：

```bash
worldmind-debug/cli/wmctl trace trace_demo_001
```

## 排障示例

前端无数据：

```bash
worldmind-debug/cli/wmctl doctor
worldmind-debug/cli/wmctl mqtt tail --topic 'telemetry/wine/#' --seconds 10
worldmind-debug/cli/wmctl twin echo wine:tank_01
worldmind-debug/cli/wmctl conn list
worldmind-debug/cli/wmctl influx recent --measurement mqtt_consumer --minutes 60
```

判断：

```text
MQTT 无消息: 查 Wine Simulator。
MQTT 有消息但 Ditto 不更新: 查 Ditto Connection。
Ditto 更新但 Influx 无数据: 查 Telegraf 与 Influx token/bucket。
Influx 有数据但 Grafana 无图: 查 Grafana datasource/panel query。
```
