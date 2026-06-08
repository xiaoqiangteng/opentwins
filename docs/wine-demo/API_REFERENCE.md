# Wine Demo API 全量接口参考

## WineTwin Service

```text
Base URL: http://localhost:8010
Source:   wine-ferment-twin/winetwin-service/app/main.py
```

| 方法 | 路径 | 参数 / Body | 说明 | 示例 |
| --- | --- | --- | --- | --- |
| GET | `/health` | 无 | 服务健康检查，返回 Ditto/Influx/Modelica 配置摘要 | `curl http://localhost:8010/health` |
| POST | `/api/wine/init` | 无 | 初始化提示；完整初始化使用 `scripts/init_wine_twins.sh` | `curl -X POST http://localhost:8010/api/wine/init` |
| GET | `/api/wine/overview` | 无 | 酒庄、车间、罐体总览 | `curl http://localhost:8010/api/wine/overview` |
| GET | `/api/wine/tanks` | 无 | 列出所有发酵罐 | `curl http://localhost:8010/api/wine/tanks` |
| GET | `/api/wine/tanks/{tank_id}` | path `tank_id` | 查询单个发酵罐 | `curl http://localhost:8010/api/wine/tanks/tank_01` |
| GET | `/api/wine/tanks/{tank_id}/history` | query `metric=brix`, `hours=48` | 查询历史曲线 | `curl 'http://localhost:8010/api/wine/tanks/tank_01/history?metric=brix&hours=48'` |
| GET | `/api/wine/tanks/{tank_id}/alarms` | path `tank_id` | 查询罐体告警 | `curl http://localhost:8010/api/wine/tanks/tank_02/alarms` |
| GET | `/api/wine/tanks/{tank_id}/prediction` | path `tank_id` | Python 预测 | `curl http://localhost:8010/api/wine/tanks/tank_01/prediction` |
| POST | `/api/wine/tanks/{tank_id}/simulate` | JSON body | Python what-if 仿真 | `curl -X POST http://localhost:8010/api/wine/tanks/tank_01/simulate -H 'Content-Type: application/json' -d '{"temperature_delta": 1}'` |
| GET | `/api/wine/modelica/health` | 无 | 检查 Modelica 服务 | `curl http://localhost:8010/api/wine/modelica/health` |
| GET | `/api/wine/tanks/{tank_id}/modelica-prediction` | query `horizon=24` | 调用 Modelica 预测 | `curl 'http://localhost:8010/api/wine/tanks/tank_01/modelica-prediction?horizon=24'` |
| POST | `/api/wine/tanks/{tank_id}/modelica-simulate` | JSON body | Modelica what-if 仿真 | `curl -X POST http://localhost:8010/api/wine/tanks/tank_01/modelica-simulate -H 'Content-Type: application/json' -d '{"temperature_delta": -2}'` |
| GET | `/api/wine/rules` | 无 | 返回告警规则配置 | `curl http://localhost:8010/api/wine/rules` |
| GET | `/api/wine/simulation/status` | 无 | 嵌入式仿真引擎状态 | `curl http://localhost:8010/api/wine/simulation/status` |
| POST | `/api/wine/simulation/start` | 无 | 启动嵌入式仿真引擎 | `curl -X POST http://localhost:8010/api/wine/simulation/start` |
| POST | `/api/wine/simulation/pause` | 无 | 暂停嵌入式仿真引擎 | `curl -X POST http://localhost:8010/api/wine/simulation/pause` |
| POST | `/api/wine/simulation/reset` | 无 | 重置嵌入式仿真引擎 | `curl -X POST http://localhost:8010/api/wine/simulation/reset` |

## tank_id 取值

```text
tank_01
tank_02
tank_03
```

Wine API 通常使用短 ID，如 `tank_01`。Ditto API 使用完整 thingId，如 `wine:tank_01`。

## history metric 取值

常用 metric 与 feature 对应：

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
quality_score
```

## OpenModelica Simulation Service

```text
Base URL: http://localhost:8020
Source:   wine-ferment-twin/simulation-service/app/main.py
```

| 方法 | 路径 | 参数 / Body | 说明 | 示例 |
| --- | --- | --- | --- | --- |
| GET | `/health` | 无 | OpenModelica `omc --version` 健康检查 | `curl http://localhost:8020/health` |
| POST | `/api/modelica/demo` | 无 | 运行 HelloWine demo | `curl -X POST http://localhost:8020/api/modelica/demo` |
| POST | `/api/modelica/simulate` | `SimulationRequest` | 运行连续发酵模型 | `curl -X POST http://localhost:8020/api/modelica/simulate -H 'Content-Type: application/json' -d '{"tank_id":"tank_01","horizon_hours":24}'` |
| POST | `/api/modelica/what-if` | `WhatIfRequest` | what-if 仿真 | `curl -X POST http://localhost:8020/api/modelica/what-if -H 'Content-Type: application/json' -d '{"tank_id":"tank_01","horizon_hours":24,"temperature_delta":-2}'` |

## 常见错误

| 错误 | 原因 | 处理 |
| --- | --- | --- |
| `tank not found` | Ditto 中没有对应 thing | 运行 Wine 初始化脚本 |
| `Modelica service unavailable` | 8020 服务未启动或不可达 | `./watch_demo.sh --modelica --snapshot` |
| history 为空 | InfluxDB 无数据或 metric 不存在 | 用 `wmctl influx recent --measurement mqtt_consumer` 查链路 |
| 仿真引擎未启动 | 当前是独立进程模式 | 用外部 simulator 或启用嵌入式 simulation mode |
