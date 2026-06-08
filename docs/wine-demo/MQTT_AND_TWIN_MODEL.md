# Wine Demo MQTT 与 Twin 数据模型

## 数据链路

```text
Wine Simulator
  -> MQTT topic telemetry/wine/{tank_id}
  -> Ditto Connection
  -> Ditto Thing wine:{tank_id}
  -> Ditto Events / Telegraf
  -> InfluxDB mqtt_consumer
  -> WineTwin Service / Grafana / Frontend
```

## 罐体配置

来自 `wine-ferment-twin/configs/wine_simulation.yaml`：

| tank_id | thing_id | parent_id | wine_type | anomaly |
| --- | --- | --- | --- | --- |
| `tank_01` | `wine:tank_01` | `wine:workshop_01` | `red` | `null` |
| `tank_02` | `wine:tank_02` | `wine:workshop_01` | `red` | `temperature_high` |
| `tank_03` | `wine:tank_03` | `wine:workshop_01` | `white` | `stuck_fermentation` |

## MQTT 发布格式

外层 MQTT topic：

```text
telemetry/wine/tank_01
telemetry/wine/tank_02
telemetry/wine/tank_03
```

Payload 结构：

```json
{
  "topic": "wine/tank_01/things/twin/commands/merge",
  "headers": {
    "content-type": "application/merge-patch+json"
  },
  "path": "/features",
  "value": {
    "temperature": {
      "properties": {
        "value": 25.0,
        "observed_at": "2026-06-08T10:30:00Z",
        "unit": "C"
      }
    }
  },
  "extra": {
    "thingId": "wine:tank_01",
    "attributes": {
      "_parents": ["wine:workshop_01"]
    }
  }
}
```

## Feature 值结构

每个 feature 基本结构：

```json
{
  "properties": {
    "value": 3.45,
    "observed_at": "2026-06-08T10:30:00Z",
    "unit": ""
  }
}
```

## 风险等级

`risk_level` 可能值：

```text
normal
warning
critical
finished
offline
```

## 快速观测

```bash
worldmind-debug/cli/wmctl mqtt tail --topic 'telemetry/wine/#' --seconds 10
worldmind-debug/cli/wmctl twin echo wine:tank_01
worldmind-debug/cli/wmctl twin watch wine:tank_01 --feature brix --interval 2
worldmind-debug/cli/wmctl twin watch wine:tank_02 --feature risk_level --interval 2
worldmind-debug/cli/wmctl twin watch wine:tank_03 --feature fermentation_progress --interval 5
```

## 与 Wine API 的 ID 对照

| 场景 | 使用形式 | 示例 |
| --- | --- | --- |
| Wine API path | 短 ID | `/api/wine/tanks/tank_01` |
| Ditto thingId | 完整 thingId | `wine:tank_01` |
| MQTT publish topic | slash topic | `telemetry/wine/tank_01` |
| Ditto command payload topic | slash command topic | `wine/tank_01/things/twin/commands/merge` |
