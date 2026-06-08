# API

Base URL: `http://10.168.1.102:8010`

All WineTwin APIs return:

```json
{ "code": 0, "message": "ok", "data": {} }
```

## Endpoints

- `GET /health`: service status and OpenTwins endpoint configuration.
- `POST /api/wine/init`: initialization hook; operational startup uses `scripts/init_wine_twins.sh`.
- `GET /api/wine/overview`: winery/workshop status, tank count, alarm count, average score, and tank list.
- `GET /api/wine/tanks`: all tank states.
- `GET /api/wine/tanks/{tank_id}`: one tank state.
- `GET /api/wine/tanks/{tank_id}/history?metric=brix&hours=72`: time-series trend.
- `GET /api/wine/tanks/{tank_id}/alarms`: active alarms.
- `GET /api/wine/tanks/{tank_id}/prediction`: future progress and estimated completion time.
- `POST /api/wine/tanks/{tank_id}/simulate`: parameter perturbation simulation.
- `GET /api/wine/rules`: alarm rule configuration.

## Tank Response

```json
{
  "tank_id": "tank_02",
  "thing_id": "wine:tank_02",
  "name": "Fermentation Tank 02",
  "wine_type": "red",
  "stage": "active",
  "risk_level": "critical",
  "metrics": {
    "temperature": { "value": 34.42, "unit": "C" },
    "brix": { "value": 14.3, "unit": "Bx" },
    "fermentation_progress": { "value": 41.5, "unit": "%" }
  },
  "alarms": [
    {
      "level": "critical",
      "type": "temperature_high",
      "message": "Fermentation temperature is above critical range.",
      "recommendation": "Activate cooling immediately and inspect tank."
    }
  ]
}
```
