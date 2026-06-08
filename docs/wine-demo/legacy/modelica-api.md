# OpenModelica API

## Simulation Service

Base URL: `http://<SERVER_IP>:8020`

### GET `/health`

返回 OpenModelica 可用性和 `omc --version`。

### POST `/api/modelica/demo`

运行 `WineFermentation.HelloWine` 最小模型，生成 `modelica/results/WineFermentation.HelloWine_res.csv` 或 `.mat`。

### POST `/api/modelica/simulate`

从当前发酵罐状态继续仿真未来曲线。

```json
{
  "tank_id": "tank_01",
  "wine_type": "red",
  "horizon_hours": 24,
  "step_hours": 1,
  "current_state": {
    "brix": 16.2,
    "alcohol": 4.3,
    "co2": 3200.0,
    "temperature": 25.4,
    "ph": 3.41,
    "progress": 37.0
  },
  "model_params": {
    "initial_brix_reference": 24.5,
    "final_brix": -1.0,
    "optimal_temperature": 25.0,
    "warning_temperature": 30.0,
    "critical_temperature": 33.0
  }
}
```

响应包含：

- `engine`: `OpenModelica`
- `model`: `WineFermentation.ContinuationFermentation`
- `estimated_completion_hours`
- `risk_level`
- `quality_score_end`
- `points[]`: `hour`, `brix`, `alcohol`, `co2`, `progress`, `quality_score`, `risk_code`

### POST `/api/modelica/what-if`

请求体与 `/simulate` 相同，额外支持：

```json
{
  "temperature_delta": -5,
  "nutrient_boost": 0
}
```

## WineTwin Service 聚合 API

Base URL: `http://<SERVER_IP>:8010`

- `GET /api/wine/modelica/health`
- `GET /api/wine/tanks/{tank_id}/modelica-prediction?horizon=24`
- `POST /api/wine/tanks/{tank_id}/modelica-simulate`

WineTwin Service 会从 Ditto 读取当前 Twin Feature，并自动映射为 OpenModelica 请求。
