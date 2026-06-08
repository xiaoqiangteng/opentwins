# 葡萄酒发酵数字孪生 — 仿真演变逻辑文档

## 一、三个发酵罐的仿真公式与演变逻辑

### 1.1 基础发酵模型

模拟基于 12 天（288 小时）的红/白葡萄酒发酵过程，每 5 秒推进一次仿真时间（speed=3600，即 5 现实秒 = 5 仿真小时）。

#### 核心公式

| 指标 | 公式 | 说明 |
|------|------|------|
| **Brix（糖度）** | `Brix = Bf + (B0 - Bf) × e^(-k×t)` | 指数衰减，模拟糖分被酵母消耗。k = ln((B0-Bf)/0.15) / total_hours |
| **发酵进度** | `progress = (B0 - Brix) / (B0 - Bf)`，clamp 到 [0,1] | 糖度下降越多，进度越高 |
| **发酵阶段** | progress < 0.10 → initial；< 0.80 → active；< 0.98 → late；≥ 0.98 → finished | 基于进度划分 |
| **温度** | `temp = target_temp + 4.0×sin(π×progress) + 0.6×sin(2π×(t%24)/24) + noise(-0.25,0.25)` | 目标温度 + 发酵放热(最高+4°C) + 日间波动 + 随机噪声 |
| **CO2** | `co2 = 420 + 7200×exp(-(t - 0.32×T)² / (2×(0.14×T)²)) + noise(-90,90)` | 高斯峰，在约 32% 进度时达到峰值 ~7620 ppm |
| **pH** | `pH = initial_ph - 0.08×progress + noise(-0.025,0.025)` | 随发酵缓慢降低（最多降 0.08） |
| **压力** | `pressure = 101.3 + min(3.5, co2/4200) + noise(-0.15,0.15)` | 基础大气压 + CO2 贡献 |
| **酒精度** | `alcohol = max_alcohol × progress` | 线性累积 |

#### 关键源码位置

- 发酵模型公式：`wine-simulator/fermentation_model.py`
- 仿真主循环：`wine-simulator/wine_fermentation_simulator.py`
- 异常注入：`wine-simulator/anomaly_injector.py`
- 仿真配置：`configs/wine_simulation.yaml`

---

### 1.2 三个发酵罐初始参数

| 参数 | tank_01（红葡萄酒） | tank_02（红葡萄酒·高温异常） | tank_03（白葡萄酒·发酵停滞） |
|------|-------|-------|-------|
| wine_type | red | red | white |
| initial_brix | 24.5 | 25.0 | 22.5 |
| final_brix | -1.0 | -0.8 | -1.0 |
| max_alcohol | 13.2% | 13.6% | 12.1% |
| target_temp | 25°C | 26°C | 14°C |
| initial_ph | 3.45 | 3.50 | 3.30 |
| anomaly | 无 | temperature_high | stuck_fermentation |

---

### 1.3 异常注入机制

异常注入由 `anomaly_injector.py` 实现，根据配置文件中每个罐的 `anomaly` 字段在特定时间点注入异常：

| 异常类型 | 触发条件 | 效果 |
|----------|----------|------|
| **temperature_high**（tank_02） | elapsed ≥ 40h | 温度额外 +4.8°C + min(2.0, (t-40)/48)°C，即 40h 起温度逐步升高，最高额外 +6.8°C |
| **stuck_fermentation**（tank_03） | elapsed ≥ 72h | 强制 Brix 不低于 `B0 - 5.2 - (t-72)×0.015`，即糖度几乎不再下降，发酵进度被钉住 |
| ph_abnormal | elapsed ≥ 96h | pH 额外 +0.45（Demo 中未使用） |
| co2_low | 36h ≤ elapsed ≤ 120h | CO2 降至正常值的 18%（Demo 中未使用） |
| sensor_missing | 随机 12% 概率 | 温度返回 None，触发 offline 状态（Demo 中未使用） |
| sensor_spike | 随机 8% 概率 | 温度随机 ±8°C 尖峰（Demo 中未使用） |

---

### 1.4 演变时间线

```
时间(仿真小时)  tank_01            tank_02              tank_03
────────────────────────────────────────────────────────────────
0~28h          初始期(initial)     初始期(initial)       初始期(initial)
               温度正常~25°C       温度正常~26°C         温度正常~14°C

28~40h         进入活跃期(active)  进入活跃期(active)    进入活跃期(active)
               CO2快速上升         CO2快速上升           CO2快速上升
               温度升至~29°C       温度升至~30°C         温度升至~18°C

40~72h         活跃发酵中          ⚠️ 温度异常启动！      活跃发酵中
               温度峰值~29°C       温度额外+4.8起升      温度~18°C(白葡萄酒上限)
               risk=normal         → 温度达30°C以上
                                   → risk=warning(黄)
                                   → 继续升→超33°C
                                   → risk=critical(红)

72~230h        活跃→晚期发酵       持续高温告警           ⚠️ 发酵停滞启动！
               CO2开始下降         risk=warning/critical  Brix不再下降
               进度稳步推进                               发酵进度被卡住
                                                          risk=warning(黄)
                                                          CO2可能低于预期

230~288h       晚期→完成           晚期(仍有高温)         发酵停滞未恢复
               risk=finished       risk视温度而定         进度远低于100%
                                                          risk=warning
```

#### 典型现象解释

- **tank_02 变红**：约 40 仿真小时后注入温度异常，温度超出红葡萄酒警告阈值 30°C 变黄(warning)，继续上升超过 33°C 危险阈值后变红(critical)。
- **tank_03 变黄**：约 72 仿真小时后注入发酵停滞，糖度不再下降导致进度卡住，触发 warning 告警。
- **tank_01 保持绿色**：无异常注入，正常完成发酵。

---

## 二、预警策略与阈值

### 2.1 告警阈值

配置文件：`configs/alarm_rules.yaml`，评估逻辑：`winetwin-service/app/services/rules.py`

#### 红葡萄酒

| 指标 | 警告(warning) | 危险(critical) |
|------|--------------|---------------|
| 温度 | > 30°C | > 33°C |
| pH | < 3.1 或 > 3.8 | < 3.0 或 > 3.9 |
| CO2（活跃期） | < 1500 ppm | — |
| Brix 12h 下降量 | < 0.2 Bx | — |

#### 白葡萄酒

| 指标 | 警告(warning) | 危险(critical) |
|------|--------------|---------------|
| 温度 | > 18°C | > 22°C |
| pH | < 3.0 或 > 3.7 | < 3.0 或 > 3.9 |
| CO2（活跃期） | < 1200 ppm | — |
| Brix 12h 下降量 | < 0.15 Bx | — |

### 2.2 质量评分扣分规则

| 触发条件 | 扣分 |
|----------|------|
| 传感器离线 | -55 |
| 温度超危险阈值 | -32 |
| 温度超警告阈值 | -18 |
| pH 异常 | -18 |
| CO2 低于预期 | -12 |
| 发酵停滞（tank_03 专属规则） | -18 |

初始 score = 100，取值范围 [0, 100]。多个告警扣分累加。

### 2.3 风险等级颜色映射

| risk_level | 含义 | 3D 模型色值 | CSS 样式 |
|------------|------|-----------|----------|
| normal | 正常 | #2e7d32 (绿) | `.risk.normal` |
| warning | 警告 | #f9a825 (黄) | `.risk.warning` |
| critical | 危险 | #c62828 (红) | `.risk.critical` |
| offline | 离线 | #9e9e9e (灰) | `.risk.offline` |
| finished | 已完成 | #1565c0 (蓝) | `.risk.finished` |

---

## 三、History 历史数据曲线

### 3.1 数据来源

优先从 **InfluxDB** 时序数据库查询真实写入的传感器数据。如果 InfluxDB 连接失败（未配置 token 等），则 **降级为本地公式重新生成** 模拟数据（`history_service.py` 中的 `generated()` 函数），使用与仿真相同的公式回算过去 N 小时的数据点。

### 3.2 数据是否写入数据库

**是的，数据会写入 InfluxDB，但取决于配置：**

1. **写入路径**：仿真器每 5 秒通过 MQTT 发布数据 → Eclipse Ditto 接收 → Ditto InfluxDB Connector 将数据写入 InfluxDB
2. **本地备份**：仿真器同时将数据保存到本地 CSV 文件（`wine-simulator/data/generated_csv/`）
3. **查询路径**：`winetwin-service/app/services/history_service.py` 优先查询 InfluxDB，失败时用公式回算

### 3.3 判断方法

- 如果 `INFLUX_TOKEN` 环境变量已正确配置，History 查询会读取到真实写入的历史数据
- 如果 InfluxDB 连接失败，看到的是公式回算的模拟数据（曲线完全光滑，无真实噪声）
- 可通过查看 `winetwin-service` 日志中是否出现 `history fallback` 来判断是否降级

---

## 四、Simulation 仿真面板

### 4.1 Parameter Perturbation 参数含义

**Temperature delta（温度偏移量）**：一个滑动条，范围 -5°C ~ +5°C，表示对当前发酵罐目标温度的假设性偏移量。

它 **不是** 直接修改实际温度，而是用于 **what-if 分析**：如果我给这个罐降温/升温若干度，对最终质量有什么影响？

### 4.2 Run Simulation 点击后的变化

点击 **运行仿真** 后：

1. 前端调用 `POST /api/wine/tanks/{id}/simulate`，发送 `{temperature_delta: delta, nutrient_boost: 1}`
2. 后端 `prediction_service.simulate()` 计算质量变化量：
   ```
   gain = clamp(-8, 8, -delta × 0.6 + nutrient × 2.0)
   ```
   - **降温**（delta < 0）：gain 为正 → 质量提升（降温有利于发酵控制）
   - **升温**（delta > 0）：gain 为负 → 质量下降
   - **nutrient_boost** 固定为 1（前端硬编码），贡献 +2.0 的质量增益
3. 界面下方出现结果区域：**质量变化量: X.X**，以及操作建议

### 4.3 界面变化详解

| 区域 | 变化 |
|------|------|
| 左侧「24小时预测」 | 展示基于当前参数的趋势预测曲线（不受扰动影响） |
| 右侧「参数扰动」 | 滑动温度偏移量后点击运行仿真 |
| 结果区域 | 运行仿真后出现：显示 projected_quality_delta 和 recommendation |

### 4.4 注意事项

> 当前 Simulation 是一个简化的演示模型，扰动结果是一个线性估算，并非完整的物理仿真。nutrient_boost 参数前端固定传 1，用户无法调整。

---

## 五、中文化改动清单

已完成以下文件的中文化修改：

| 文件 | 修改内容 |
|------|----------|
| `wine-frontend/src/main.tsx` | 品牌名→「葡萄酒发酵数字孪生」、导航按钮（总览/历史/仿真）、指标标签（温度/糖度/pH/CO2/酒精度/进度）、风险等级翻译、页脚文字、历史标签翻译、仿真面板标题翻译 |
| `wine-frontend/src/components/panels/AlarmPanel.tsx` | "Alarms"→"告警"、"No active alarms"→"暂无活跃告警"、告警等级翻译（危险/警告/离线） |
| `wine-frontend/src/components/panels/RecommendationPanel.tsx` | "Recommendation"→"操作建议" |
| `wine-frontend/src/components/three/FermentationTank.tsx` | 3D 模型标签中风险等级中文化（正常/警告/危险/离线/已完成） |
| `winetwin-service/app/services/rules.py` | 所有告警消息和操作建议中文化 |
| `wine-simulator/wine_fermentation_simulator.py` | 仿真器推荐建议中文化 |
| `winetwin-service/app/services/prediction_service.py` | 仿真结果推荐建议中文化 |

**保留英文的部分：** pH、CO2、Brix、alcohol 等专业指标名称保持英文，仅描述性文字改为中文。

---

## 六、数据流全景

```
wine_fermentation_simulator.py
    │  每5秒调用 simulate_point() 生成一个数据点
    │  调用 apply_anomaly() 注入异常
    │  调用 risk_and_score() 计算风险和质量分
    │
    ├──→ MQTT (Eclipse Ditto) ──→ Ditto InfluxDB Connector ──→ InfluxDB
    │         ↑                        ↑
    │    wine-simulator/          winetwin-service/
    │    mqtt_client.py           clients/influx_client.py
    │
    ├──→ CSV 文件 (本地备份)
    │    wine-simulator/data/generated_csv/
    │
    └──→ winetwin-service (FastAPI)
              │
              ├── GET /api/wine/tanks        → twin_service (查询 Ditto)
              ├── GET /api/wine/tanks/:id/history → history_service (查询 InfluxDB / 公式回算)
              ├── GET /api/wine/tanks/:id/prediction → prediction_service (公式预测)
              ├── POST /api/wine/tanks/:id/simulate → prediction_service (参数扰动仿真)
              └── GET /api/wine/tanks/:id/alarms → alarm_service (规则引擎评估)
```

```
wine-frontend (React + Three.js)
    │
    ├── 每5秒轮询 GET /api/wine/tanks 获取最新状态
    ├── 3D 场景 (WineWorkshopScene) 根据风险等级渲染颜色
    ├── History 面板查询 GET /api/wine/tanks/:id/history?metric=xxx&hours=72
    └── Simulation 面板查询预测 + 提交扰动仿真
```
