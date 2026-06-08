# Topic / Thing / Feature / Measurement 查找表

## MQTT Broker

当前部署：

```text
Host: <OPENTWINS_HOST_IP>
Port: 30511
Username: ditto
Password: ditto
```

## Wine Simulator 发布 Topic

来自 `wine-ferment-twin/configs/wine_simulation.yaml` 与 `wine-simulator/mqtt_client.py`：

```text
topic_prefix: telemetry
namespace:    wine
tank_id:      tank_01 / tank_02 / tank_03
publish topic format: telemetry/wine/{tank_id}
```

实际 topic：

| 罐体 | MQTT publish topic | 用途 |
| --- | --- | --- |
| tank_01 | `telemetry/wine/tank_01` | 正常红葡萄酒发酵罐 |
| tank_02 | `telemetry/wine/tank_02` | 高温异常红葡萄酒发酵罐 |
| tank_03 | `telemetry/wine/tank_03` | 停滞发酵白葡萄酒发酵罐 |

## MQTT 订阅通配

| Topic | 覆盖范围 | 推荐用途 |
| --- | --- | --- |
| `telemetry/#` | `telemetry` 下全部消息 | 全局入口排查 |
| `telemetry/wine/#` | Wine namespace 全部消息 | Wine Demo 排查 |
| `telemetry/wine/+` | Wine namespace 下一层所有 tank | 只看单层 tank telemetry |
| `telemetry/wine/tank_01` | tank_01 | 单罐排查 |
| `telemetry/wine/tank_02` | tank_02 | 高温异常路径排查 |
| `telemetry/wine/tank_03` | tank_03 | 停滞发酵路径排查 |

命令示例：

```bash
worldmind-debug/cli/wmctl mqtt tail --topic 'telemetry/#' --seconds 10
worldmind-debug/cli/wmctl mqtt tail --topic 'telemetry/wine/#' --seconds 10
worldmind-debug/cli/wmctl mqtt tail --topic 'telemetry/wine/+' --seconds 10
worldmind-debug/cli/wmctl mqtt tail --topic 'telemetry/wine/tank_01' --seconds 10
```

## Ditto Command Payload 内部 Topic

Wine Simulator 发布到 MQTT 的 payload 里还包含 Ditto command topic：

```json
{
  "topic": "wine/tank_01/things/twin/commands/merge",
  "headers": {"content-type": "application/merge-patch+json"},
  "path": "/features",
  "value": {},
  "extra": {
    "thingId": "wine:tank_01",
    "attributes": {"_parents": ["wine:workshop_01"]}
  }
}
```

内部 topic 格式：

```text
wine/{tank_id}/things/twin/commands/merge
```

实际内部 topic：

```text
wine/tank_01/things/twin/commands/merge
wine/tank_02/things/twin/commands/merge
wine/tank_03/things/twin/commands/merge
```

## Ditto Thing IDs

| thingId | 类型 | 说明 |
| --- | --- | --- |
| `wine:winery_01` | Winery | 酒庄根节点 |
| `wine:workshop_01` | Workshop | 发酵车间 |
| `wine:tank_01` | FermentationTank | 正常红葡萄酒发酵罐 |
| `wine:tank_02` | FermentationTank | 高温异常红葡萄酒发酵罐 |
| `wine:tank_03` | FermentationTank | 停滞发酵白葡萄酒发酵罐 |

查询示例：

```bash
worldmind-debug/cli/wmctl twin echo wine:winery_01
worldmind-debug/cli/wmctl twin echo wine:workshop_01
worldmind-debug/cli/wmctl twin echo wine:tank_01
```

## Feature 列表

Winery：

```text
status
risk_level
```

Workshop：

```text
status
tank_count
risk_level
```

FermentationTank：

| feature | 单位 | 说明 |
| --- | --- | --- |
| `temperature` | `C` | 发酵温度 |
| `ph` | 空 | pH |
| `brix` | `Bx` | 糖度 |
| `specific_gravity` | 空 | 比重 |
| `co2` | `ppm` | 二氧化碳浓度 |
| `pressure` | `kPa` | 罐体压力 |
| `liquid_level` | `%` | 液位 |
| `alcohol_estimation` | `%vol` | 估算酒精度 |
| `fermentation_progress` | `%` | 发酵进度 |
| `fermentation_stage` | 空 | 发酵阶段 |
| `quality_score` | 空 | 质量评分 |
| `risk_level` | 空 | 风险等级 |
| `recommendation` | 空 | 处置建议 |

Feature watch 示例：

```bash
worldmind-debug/cli/wmctl twin watch wine:tank_01 --feature temperature --interval 2
worldmind-debug/cli/wmctl twin watch wine:tank_01 --feature ph --interval 2
worldmind-debug/cli/wmctl twin watch wine:tank_02 --feature risk_level --interval 2
worldmind-debug/cli/wmctl twin watch wine:tank_03 --feature fermentation_progress --interval 5
```

## InfluxDB

当前部署：

```text
URL:    http://<OPENTWINS_HOST_IP>:30716
Org:    opentwins
Bucket: opentwins
```

当前 WineTwin Service 查询代码使用：

```text
measurement: mqtt_consumer
tag:         thingId == "wine:{tank_id}"
```

查询示例：

```bash
worldmind-debug/cli/wmctl influx recent --measurement mqtt_consumer --minutes 60
```

如果要按 `thingId` 精确过滤，可在 InfluxDB 里执行 Flux：

```text
from(bucket: "opentwins")
  |> range(start: -60m)
  |> filter(fn: (r) => r._measurement == "mqtt_consumer")
  |> filter(fn: (r) => r.thingId == "wine:tank_01")
```

## 常见误用

- `telemetry/#` 要整体加引号，避免 shell 对 `#` 后内容当注释处理。
- `wine:tank_01` 用在 Ditto thingId；MQTT topic 使用 `telemetry/wine/tank_01`。
- `/api/debug/ditto/things/wine:tank_01` 在 curl 中应编码为 `/api/debug/ditto/things/wine%3Atank_01`。
- Wine 当前实际 tank 是 `tank_01`、`tank_02`、`tank_03`，不是 `tank_001`。
