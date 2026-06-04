# Twin Model

## Hierarchy

```text
wine:winery_01
└── wine:workshop_01
    ├── wine:tank_01
    ├── wine:tank_02
    └── wine:tank_03
```

## FermentationTank Features

- `temperature` C
- `ph`
- `brix` Bx
- `specific_gravity`
- `co2` ppm
- `pressure` kPa
- `liquid_level` %
- `alcohol_estimation` %vol
- `fermentation_progress` %
- `fermentation_stage`
- `quality_score`
- `risk_level`
- `recommendation`

## MQTT Inbound Format

OpenTwins current source connection subscribes to `telemetry/#`. The simulator publishes to:

```text
telemetry/wine/tank_01
telemetry/wine/tank_02
telemetry/wine/tank_03
```

Payload is Ditto Protocol merge-patch:

```json
{
  "topic": "wine/tank_01/things/twin/commands/merge",
  "headers": { "content-type": "application/merge-patch+json" },
  "path": "/features",
  "value": {
    "temperature": { "properties": { "value": 25.4, "unit": "C" } }
  },
  "extra": {
    "thingId": "wine:tank_01",
    "attributes": { "_parents": ["wine:workshop_01"] }
  }
}
```

Ditto target connection publishes events to `opentwins/...`, which is consumed by Telegraf/InfluxDB.
