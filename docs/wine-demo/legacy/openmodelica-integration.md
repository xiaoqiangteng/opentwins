# WineFermentTwin OpenModelica 集成说明

本文档说明如何在当前 OpenTwins + WineFermentTwin Demo 上启用 OpenModelica 机理仿真服务。

## 1. 部署命令

在服务器执行：

```bash
cd /home/teng/programmings/git/opentwins
./deploy_all.sh --demo-only
```

如果需要从零部署 OpenTwins 基础设施和 Demo：

```bash
cd /home/teng/programmings/git/opentwins
./deploy_all.sh
```

如果只想验证 OpenModelica 最小模型：

```bash
cd /home/teng/programmings/git/opentwins/wine-ferment-twin
bash scripts/run_modelica_demo.sh
```

如果 Docker Hub 访问受限，先准备镜像并覆盖变量：

```bash
export OPENMODELICA_IMAGE=<your-registry>/openmodelica/openmodelica:v1.26.7-minimal
cd /home/teng/programmings/git/opentwins
./deploy_all.sh --demo-only
```

## 2. 停止和日志

停止 Demo，不卸载 OpenTwins：

```bash
cd /home/teng/programmings/git/opentwins
./stop_all.sh
```

查看状态：

```bash
./watch_demo.sh --status
```

查看 OpenModelica 服务日志：

```bash
./watch_demo.sh --modelica --snapshot --lines 80
./watch_demo.sh --modelica
```

## 3. 访问地址

部署完成后访问：

- Wine 前端：`http://<SERVER_IP>:5173`
- WineTwin Service Swagger：`http://<SERVER_IP>:8010/docs`
- OpenModelica Simulation Service Swagger：`http://<SERVER_IP>:8020/docs`
- Grafana/OpenTwins：`http://<MINIKUBE_IP>:30718`
- Ditto API：`http://<MINIKUBE_IP>:30525`

当前部署脚本会自动检测服务器 IP 和 Minikube IP。局域网其他机器访问前端时，前端仍通过 Vite proxy 调用 8010 后端。

## 4. 运行逻辑

集成后系统包含两条并行但互补的仿真链路。

### 4.1 实时演化链路

实时演化仍由 `wine-simulator` 提供，OpenModelica 不替代实时传感器源：

```text
wine-simulator
  -> Mosquitto MQTT telemetry/wine/<tank_id>
  -> Eclipse Ditto merge-patch 更新 wine:tank_xx Features
  -> Telegraf 写入 InfluxDB mqtt_consumer
  -> WineTwin Service 读取当前状态和历史曲线
  -> 前端 3D 车间每 5 秒刷新
```

这条链路回答“现在发生了什么”。它负责让 3 个发酵罐的温度、糖度、酒精度、CO2、压力、发酵进度和风险等级持续变化。

### 4.2 OpenModelica 未来演化链路

OpenModelica 链路回答“从当前状态出发，未来会怎样”：

```text
前端选择 tank_xx
  -> WineTwin Service GET /api/wine/tanks/{id}/modelica-prediction
  -> WineTwin Service 从 Ditto 读取当前 Features
  -> 映射为 Modelica SimulationRequest
  -> 调用 8020 /api/modelica/simulate
  -> Simulation Service 生成 .mos 文件
  -> omc 编译并运行 WineFermentation.ContinuationFermentation
  -> 解析 CSV 输出
  -> 返回 brix/alcohol/co2/progress/quality_score/risk_code 曲线
  -> 前端绘制 OpenModelica 预测曲线
```

这条链路不写回 Ditto，不改变实时孪生状态。它是“影子推演”，用于演示数字孪生根据当前状态驱动机理模型的能力。

## 5. Modelica 机理模型

模型文件：

```text
wine-ferment-twin/modelica/WineFermentation.mo
```

包含两个模型：

- `WineFermentation.HelloWine`：最小 smoke demo，用来验证 OpenModelica 能编译、仿真和输出 CSV。
- `WineFermentation.ContinuationFermentation`：从当前罐状态继续仿真未来演化。

核心状态变量：

- `brix`：糖度，随发酵持续下降。
- `alcohol`：酒精度，随糖消耗上升。
- `co2`：CO2 浓度，由发酵产生，同时向环境耗散。
- `yeast`：酵母活性指数，受温度适宜性影响。
- `progress`：发酵进度。
- `qualityScore`：质量评分。
- `riskCode`：0 normal、1 warning、2 critical、3 finished。

核心方程：

```text
tempFactor = exp(-alphaT * (temperature - optimalTemperature)^2)
fermentationRate = kSugar * yeast * tempFactor * max(brix - finalBrix, 0)
der(brix) = -fermentationRate
der(alcohol) = yAlcohol * fermentationRate
der(co2) = yCO2 * fermentationRate - kCO2 * max(co2 - co2Base, 0)
der(yeast) = mu * yeast * (1 - yeast / yeastMax) * tempFactor - deathRate * yeast
progress = 100 * clamp((initialBrixReference - brix) / (initialBrixReference - finalBrix), 0, 1)
```

温度通过 `tempFactor` 影响发酵速率。温度接近最适温度时，糖消耗更快；温度偏离越大，酵母活性和糖消耗效率越低。风险等级根据发酵完成度和温度阈值计算。

## 6. what-if 演示逻辑

前端“OpenModelica 机理仿真”面板提供温度扰动滑块，范围 -5 到 +5 C。

操作 tank_02：

1. tank_02 是红葡萄酒高温异常罐。
2. 基线仿真直接使用 Ditto 当前温度。
3. 将 `temperature_delta` 调到 `-5 C` 并运行 what-if。
4. WineTwin Service 调用 `/api/modelica/what-if`。
5. Simulation Service 将 `temperatureSet = current.temperature - 5` 写入 `.mos`。
6. OpenModelica 重新求解未来 24 小时轨迹。
7. 前端显示 what-if 末端质量分与基线差异。

预期演示效果：

- 降温后 `quality_score_end` 提高或保持。
- 风险等级可能从 `critical/warning` 改善为更低风险，或者至少不恶化。
- Brix 继续下降、Alcohol 上升，说明机理仿真仍保持发酵演化。

操作 tank_03：

1. tank_03 是白葡萄酒，最适温度和风险阈值更低。
2. 将 `temperature_delta` 调到 `+5 C`。
3. 因白葡萄酒 `warningTemperature=18`、`criticalTemperature=22`，同样的升温扰动更容易触发 warning 或 critical。
4. 这个对比用于说明模型参数随品类变化，而不是所有罐使用同一阈值。

## 7. 验收命令

```bash
curl http://localhost:8020/health
curl -X POST http://localhost:8020/api/modelica/simulate \
  -H 'Content-Type: application/json' \
  -d '{"tank_id":"tank_01","wine_type":"red","horizon_hours":6,"step_hours":1,"current_state":{"brix":16.2,"alcohol":4.3,"co2":3200,"temperature":25.4,"ph":3.41,"progress":37},"model_params":{"initial_brix_reference":24.5,"final_brix":-1.0,"optimal_temperature":25.0,"warning_temperature":30.0,"critical_temperature":33.0}}'
curl http://localhost:8010/api/wine/modelica/health
curl http://localhost:8010/api/wine/tanks/tank_01/modelica-prediction?horizon=24
curl -X POST http://localhost:8010/api/wine/tanks/tank_02/modelica-simulate \
  -H 'Content-Type: application/json' \
  -d '{"temperature_delta":-5,"horizon_hours":24}'
```

## 8. 常见问题

- `docker pull openmodelica/openmodelica:v1.26.7-minimal` 失败：设置 `OPENMODELICA_IMAGE` 指向可访问的镜像仓库。服务器当前已验证该具体 tag 能解析，避免使用 `latest`。
- `Modelica Service 不可达`：执行 `docker ps` 和 `docker logs modelica-simulation-service` 查看容器状态。
- WineTwin Service 调用 8020 失败：确认 `MODELICA_SERVICE_URL=http://127.0.0.1:8020`，并确认 8020 已监听。
- 前端没有曲线：先打开 `http://<SERVER_IP>:8020/docs` 直接运行 `/api/modelica/simulate`，确认服务端可返回 points。
