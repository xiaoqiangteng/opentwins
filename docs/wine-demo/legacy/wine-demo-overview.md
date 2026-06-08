# WineFermentTwin Demo — 完整说明文档

> 本文档为 ChatGPT 迭代优化提供完整上下文，涵盖 Wine Demo 的业务逻辑、技术架构、实现细节和已知局限。

---

## 1. 项目定位

WineFermentTwin 是基于 **OpenTwins 数字孪生平台**构建的葡萄酒发酵过程数字孪生演示应用。它将 OpenTwins 的底层基础设施（Eclipse Ditto 孪生引擎、MQTT 消息、InfluxDB 时序存储）与行业场景结合，展示数字孪生在食品发酵领域的能力：

- **实时状态镜像**：3 个发酵罐的传感器数据实时映射到数字孪生
- **智能告警**：基于规则引擎自动评估风险等级并生成告警
- **历史回溯**：指标数据曲线查询与可视化
- **仿真推演**：参数扰动 what-if 分析和 24 小时趋势预测
- **3D 可视化**：Three.js 渲染的车间场景，风险等级颜色联动

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Minikube (K8s 集群)                            │
│                                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌─────────┐ │
│  │ Eclipse  │ │ Mosquitto│ │ InfluxDB │ │  Grafana  │ │Telegraf │ │
│  │  Ditto   │ │  MQTT    │ │          │ │ + ERTIS   │ │         │ │
│  │(孪生引擎)│ │(消息代理) │ │(时序存储) │ │ (可视化)   │ │(采集桥接)│ │
│  └────┬─────┘ └────┬─────┘ └──────────┘ └───────────┘ └─────────┘ │
│       │             │         NodePort 暴露:                       │
└───────┼─────────────┼───────── 30525 (Ditto)                      │
        │             │           30526 (Extended API)                │
        │             │           30511 (Mosquitto)                   │
        │             │           30716 (InfluxDB)                    │
─────────┼─────────────┼──────────────────────────────────────────────
        │             │  宿主机
        │             │
   ┌────┴─────┐ ┌─────┴──────────┐  ┌────────────────┐
   │ WineTwin │ │ Wine Simulator │  │ Wine Frontend  │
   │ Service  │ │  (虚拟传感器)   │  │  (React+3D)    │
   │ (FastAPI)│ │  (Python)      │  │  (Vite)        │
   │  :8010   │ │  (MQTT发布)    │  │   :5173        │
   └──────────┘ └────────────────┘  └────────────────┘
```

### 2.2 数据流

```
wine_fermentation_simulator.py
    │  每5秒: simulate_point() → apply_anomaly() → risk_and_score()
    │
    ├──→ MQTT (Mosquitto, Ditto 协议格式) ──→ Ditto (孪生状态更新)
    │         wine-simulator/mqtt_client.py
    │
    ├──→ CSV 文件 (本地备份)
    │    wine-simulator/data/generated_csv/
    │
    └──→ Ditto ──→ Telegraf (MQTT Consumer) ──→ InfluxDB (时序存储)

winetwin-service (FastAPI, :8010)
    │
    ├── GET /api/wine/overview           → twin_service → Ditto API
    ├── GET /api/wine/tanks              → twin_service → Ditto API + 规则引擎
    ├── GET /api/wine/tanks/:id          → twin_service → Ditto API + 规则引擎
    ├── GET /api/wine/tanks/:id/history  → history_service → InfluxDB / 公式回算
    ├── GET /api/wine/tanks/:id/prediction → prediction_service → 公式预测
    ├── POST /api/wine/tanks/:id/simulate → prediction_service → 参数扰动计算
    └── GET /api/wine/tanks/:id/alarms   → alarm_service → 规则引擎

wine-frontend (React + Three.js, :5173)
    │
    ├── 每5秒轮询 GET /api/wine/tanks
    ├── 3D 车间场景 (WineWorkshopScene + FermentationTank)
    ├── History 面板 (ECharts 曲线)
    └── Simulation 面板 (预测 + 参数扰动)
```

---

## 3. 数字孪生模型

### 3.1 孪生层级结构

```
wine:winery_01 (酒庄)
  └── wine:workshop_01 (发酵车间)
       ├── wine:tank_01 (红葡萄酒·正常)
       ├── wine:tank_02 (红葡萄酒·高温异常)
       └── wine:tank_03 (白葡萄酒·发酵停滞)
```

### 3.2 孪生类型定义

| 类型 ID | 名称 | Feature 列表 |
|---------|------|-------------|
| wine:Winery | Winery | status, risk_level |
| wine:Workshop | Workshop | status, tank_count, risk_level |
| wine:FermentationTank | FermentationTank | temperature, ph, brix, specific_gravity, co2, pressure, liquid_level, alcohol_estimation, fermentation_progress, fermentation_stage, quality_score, risk_level, recommendation |

### 3.3 每个 Feature 的数据结构

```json
{
  "temperature": {
    "properties": {
      "value": 28.5,
      "unit": "C",
      "observed_at": "2026-06-05T10:30:00+00:00"
    }
  }
}
```

### 3.4 孪生初始化流程

1. `init_wine_types.py` → 向 Extended API 注册三种类型 (Winery/Workshop/FermentationTank)
2. `create_wine_twins.py` → 读取 JSON Schema，在 Ditto 中创建 Winery/Workshop/3 个 Tank 的 Thing 实例
3. `verify_wine_twins.py` → 验证所有 Thing 是否创建成功

---

## 4. 仿真模拟器

### 4.1 概述

仿真器模拟 12 天（288 小时）的葡萄酒发酵过程，时间加速 3600 倍（5 现实秒 = 5 仿真小时），约 15 分钟跑完一个完整发酵周期。

**配置文件**：`configs/wine_simulation.yaml`

```yaml
simulation:
  interval_seconds: 5       # 每5秒发送一次数据
  speed: 3600               # 时间加速倍率
  total_days: 12            # 发酵总时长
  save_csv: true            # 同时保存CSV
  mqtt_topic_prefix: "telemetry"
```

### 4.2 三个发酵罐初始参数

| 参数 | tank_01（红葡萄酒） | tank_02（红葡萄酒·高温异常） | tank_03（白葡萄酒·发酵停滞） |
|------|-------|-------|-------|
| wine_type | red | red | white |
| initial_brix | 24.5 | 25.0 | 22.5 |
| final_brix | -1.0 | -0.8 | -1.0 |
| max_alcohol | 13.2% | 13.6% | 12.1% |
| target_temp | 25°C | 26°C | 14°C |
| initial_ph | 3.45 | 3.50 | 3.30 |
| anomaly | 无 | temperature_high | stuck_fermentation |

### 4.3 发酵物理模型（核心公式）

源码：`wine-simulator/fermentation_model.py`

#### 糖度（Brix）— 指数衰减模型

```
k = ln((B0 - Bf) / 0.15) / total_hours
Brix(t) = Bf + (B0 - Bf) × exp(-k × t)
```

- B0 = 初始糖度，Bf = 最终糖度
- 模拟酵母消耗糖分的指数衰减过程
- 0.15 是残余未发酵糖的基线修正

#### 发酵进度

```
progress = clamp((B0 - Brix(t)) / (B0 - Bf), 0, 1)
```

#### 发酵阶段

| 进度范围 | 阶段 | 说明 |
|----------|------|------|
| 0% ~ 10% | initial | 初始期，酵母活化 |
| 10% ~ 80% | active | 活跃发酵期，CO2 大量产生 |
| 80% ~ 98% | late | 晚期发酵，速度放缓 |
| ≥ 98% | finished | 发酵完成 |

#### 温度

```
temp(t) = target_temp + 4.0 × sin(π × progress) + 0.6 × sin(2π × (t%24)/24) + U(-0.25, 0.25)
```

- 4.0 × sin(π × progress)：发酵放热效应，在 50% 进度时达到峰值 +4°C
- 0.6 × sin(...)：日间温度波动（昼夜节律）
- U(-0.25, 0.25)：均匀分布的随机噪声

#### CO2 浓度 — 高斯峰模型

```
co2(t) = 420 + 7200 × exp(-(t - 0.32×T)² / (2 × (0.14×T)²)) + U(-90, 90)
```

- 基线 420 ppm（大气背景）
- 高斯峰在 32% 进度处达到最大值 ~7620 ppm
- T = total_hours（288h），峰值约在 92h 出现

#### pH

```
pH(t) = initial_ph - 0.08 × progress + U(-0.025, 0.025)
```

- 随发酵缓慢下降（最多降 0.08）
- 反映有机酸积累

#### 压力

```
pressure(t) = 101.3 + min(3.5, co2/4200) + U(-0.15, 0.15)
```

- 101.3 kPa 大气压基线
- CO2 贡献的压力增量（封顶 3.5 kPa）

#### 酒精度

```
alcohol(t) = max_alcohol × progress
```

#### 液位

```
liquid_level = 配置固定值（默认 82%）
```

### 4.4 异常注入机制

源码：`wine-simulator/anomaly_injector.py`

| 异常类型 | 触发条件 | 效果 | 使用场景 |
|----------|----------|------|----------|
| temperature_high | elapsed ≥ 40h | 温度额外 +4.8 + min(2.0, (t-40)/48)°C，最高额外 +6.8°C | tank_02 |
| stuck_fermentation | elapsed ≥ 72h | Brix 不低于 B0-5.2-(t-72)×0.015，发酵进度被卡住 | tank_03 |
| ph_abnormal | elapsed ≥ 96h | pH 额外 +0.45 | 未使用 |
| co2_low | 36h ≤ t ≤ 120h | CO2 降至正常值 18% | 未使用 |
| sensor_missing | 随机 12% | 温度返回 None → offline | 未使用 |
| sensor_spike | 随机 8% | 温度 ±8°C 尖峰 | 未使用 |

### 4.5 演变时间线

```
仿真时间    tank_01             tank_02                tank_03
─────────────────────────────────────────────────────────────────
0~28h     初始期(initial)      初始期(initial)         初始期(initial)
          温度~25°C            温度~26°C               温度~14°C

28~40h    活跃期(active)       活跃期(active)          活跃期(active)
          CO2快速上升           CO2快速上升              CO2快速上升
          温度升至~29°C         温度升至~30°C            温度升至~18°C

40~72h    活跃发酵中           ⚠️ 温度异常启动！        活跃发酵中
          温度峰值~29°C         +4.8°C起升               温度~18°C
          risk=normal          → 超30°C → warning(黄)
                               → 超33°C → critical(红)

72~230h   活跃→晚期            持续高温告警             ⚠️ 发酵停滞启动！
          CO2开始下降           risk=warning/critical    Brix不再下降
          进度稳步推进                                   进度被卡住
                                                   risk=warning(黄)

230~288h  晚期→完成            晚期(仍有高温)           发酵停滞未恢复
          risk=finished         risk视温度而定           进度远低于100%
                                                          risk=warning
```

### 4.6 MQTT 消息格式

仿真器通过 `DittoMqttPublisher` 发送 Ditto 协议格式的 MQTT 消息：

```json
{
  "topic": "wine/tank_01/things/twin/commands/merge",
  "headers": { "content-type": "application/merge-patch+json" },
  "path": "/features",
  "value": {
    "temperature": { "properties": { "value": 28.5, "unit": "C", "observed_at": "..." } },
    "ph": { "properties": { "value": 3.38, "unit": "", "observed_at": "..." } },
    "...": "..."
  },
  "extra": {
    "thingId": "wine:tank_01",
    "attributes": { "_parents": ["wine:workshop_01"] }
  }
}
```

MQTT Topic：`telemetry/wine/tank_01`（前缀可配置）

---

## 5. 预警策略与规则引擎

### 5.1 告警阈值

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

### 5.2 质量评分扣分规则

| 触发条件 | 扣分 | 对应告警类型 |
|----------|------|-------------|
| 传感器离线 | -55 | sensor_missing |
| 温度超危险阈值 | -32 | temperature_high (critical) |
| 温度超警告阈值 | -18 | temperature_high (warning) |
| pH 异常 | -18 | ph_abnormal |
| CO2 低于预期 | -12 | co2_low |
| 发酵停滞（tank_03 专属） | -18 | stuck_fermentation |

初始 score = 100，多重告警累加，clamp 到 [0, 100]。

### 5.3 风险等级

| risk_level | 含义 | 3D 模型色值 | UI 样式 |
|------------|------|-----------|---------|
| normal | 正常 | #2e7d32 (绿) | 绿底深色字 |
| warning | 警告 | #f9a825 (黄) | 黄底深色字 |
| critical | 危险 | #c62828 (红) | 红底深色字 |
| offline | 离线 | #9e9e9e (灰) | 灰底深色字 |
| finished | 已完成 | #1565c0 (蓝) | 蓝底深色字 |

### 5.4 规则评估流程

```
Ditto 中的 Thing 数据
    │
    ▼
twin_service.normalize()
    │  提取 attributes + features
    ▼
rules.evaluate(attrs, features, alarm_rules)
    │  1. 判断酒类型 → 选择阈值集
    │  2. 温度检查 → warning / critical
    │  3. pH 检查 → warning / critical
    │  4. CO2 检查（仅 active 期）
    │  5. 发酵停滞检查（tank_03 专属硬编码）
    │  6. 完成判断 (progress ≥ 98%)
    ▼
输出: { risk_level, quality_score, alarms[], recommendation, stage }
```

> **注意**：规则引擎在两个地方独立实现：
> - `wine-simulator/wine_fermentation_simulator.py` 中的 `risk_and_score()` — 仿真器本地计算，通过 MQTT 发布到 Ditto
> - `winetwin-service/app/services/rules.py` 中的 `evaluate()` — 后端服务实时计算，前端直接使用
>
> 两者逻辑一致但代码独立，修改时需同步。

---

## 6. WineTwin Service 后端

### 6.1 技术栈

- **框架**：FastAPI (Python 3)
- **端口**：8010
- **外部依赖**：Eclipse Ditto API、InfluxDB、MongoDB

### 6.2 API 端点

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | /health | 健康检查 |
| GET | /api/wine/overview | 总览（酒庄+车间+告警统计+质量均分） |
| GET | /api/wine/tanks | 列出所有发酵罐状态 |
| GET | /api/wine/tanks/:id | 单个发酵罐详情 |
| GET | /api/wine/tanks/:id/history?metric=xxx&hours=72 | 历史数据查询 |
| GET | /api/wine/tanks/:id/alarms | 告警列表 |
| GET | /api/wine/tanks/:id/prediction | 24小时趋势预测 |
| POST | /api/wine/tanks/:id/simulate | 参数扰动仿真 |
| GET | /api/wine/rules | 查看告警规则配置 |

### 6.3 服务分层

```
main.py (FastAPI 路由)
    │
    ├── services/twin_service.py     — 孪生数据查询 + 规则评估
    │     └── clients/ditto_client.py — Ditto REST API 封装
    │
    ├── services/history_service.py  — 历史数据查询
    │     └── clients/influx_client.py — InfluxDB Flux 查询
    │     └── generated() (降级回算)   — 公式回算（InfluxDB 不可用时）
    │
    ├── services/prediction_service.py — 预测 + 仿真
    │     └── history_service.generated() — 复用公式预测未来
    │
    ├── services/alarm_service.py    — 告警查询
    │     └── services/rules.py      — 规则引擎
    │
    ├── services/quality_service.py  — 质量评分
    │     └── services/rules.py
    │
    └── services/recommendation_service.py — 推荐建议
          └── services/rules.py
```

### 6.4 历史数据查询策略

```python
def history(tank_id, metric, hours):
    pts = []
    try:
        # 优先从 InfluxDB 查询真实写入的数据
        pts = InfluxClient(...).query_metric(tank_id, metric, hours)
    except Exception:
        print('history fallback', e)
    # InfluxDB 无数据则用公式回算
    return {'points': pts or generated(tank_id, metric, hours)}
```

InfluxDB 查询使用 Flux 语言：
```flux
from(bucket: "opentwins")
  |> range(start: -72h)
  |> filter(fn: (r) => r._measurement == "mqtt_consumer")
  |> filter(fn: (r) => r.thingId == "wine:tank_01")
  |> filter(fn: (r) => r._field == "value_temperature_properties_value")
```

---

## 7. Wine Frontend 前端

### 7.1 技术栈

- **框架**：React 18 + TypeScript
- **构建**：Vite
- **3D 渲染**：Three.js（react-three-fiber 未使用，直接 Three.js imperative）
- **图表**：ECharts
- **图标**：Lucide React
- **端口**：5173（开发），80（Docker 生产）

### 7.2 页面结构

```
App
 ├── header (品牌 + 导航 + 刷新)
 │     ├── 总览 / 历史 / 仿真 标签页
 │
 ├── workspace (左右分栏)
 │     ├── 左侧: WineWorkshopScene (3D 车间)
 │     │     └── 3 个 FermentationTank 模型
 │     │           └── 颜色随 risk_level 变化
 │     │           └── 标签显示 tank_id + 风险等级
 │     │           └── 点击选择
 │     │
 │     └── 右侧: 侧边面板
 │           ├── 基本信息头 (thing_id + name + risk_level 标签)
 │           ├── 6 个指标卡片 (温度/糖度/pH/CO2/酒精度/进度)
 │           ├── 操作建议面板
 │           └── 告警面板
 │
 ├── History 面板 (tab=history 时显示)
 │     ├── 指标切换按钮 (温度/糖度/pH/CO2/酒精度/进度)
 │     └── ECharts 折线图
 │
 └── Simulation 面板 (tab=simulation 时显示)
       ├── 左: 24小时预测曲线
       └── 右: 参数扰动面板
             ├── 温度偏移量滑动条 (-5 ~ +5°C)
             ├── 运行仿真按钮
             └── 仿真结果 (质量变化量 + 建议)
```

### 7.3 关键交互逻辑

- **数据刷新**：每 5 秒轮询 `GET /api/wine/tanks` 更新全部状态
- **罐体选择**：3D 场景中点击罐体或从下拉选择，右侧面板联动更新
- **3D 颜色映射**：根据 `risk_level` 字段选择材质颜色（绿/黄/红/灰/蓝）
- **选中高亮**：选中罐体的顶部圆环变为黑色

### 7.4 3D 场景细节

- **模型**：圆柱体(罐体) + 半球体(罐顶) + 4 个圆柱(支腿) + 圆环(装饰)
- **标签**：Canvas 2D 绘制 → CanvasTexture → Sprite
- **场景**：平面地板 + 背墙 + 半球光 + 方向光 + 微幅旋转动画
- **交互**：Raycaster 拾取 → userData.id 匹配 → onSelect 回调

---

## 8. Simulation 面板详解

### 8.1 Parameter Perturbation（参数扰动）

**Temperature delta（温度偏移量）**：滑动条范围 -5°C ~ +5°C，对目标温度的假设性偏移。

**Nutrient boost（营养增强）**：前端硬编码为 1，用户不可调整。

### 8.2 仿真计算逻辑

```python
def simulate(tank_id, payload):
    temp_delta = payload.get('temperature_delta', 0)   # 用户输入
    nutrient = payload.get('nutrient_boost', 0)         # 固定为1
    gain = clamp(-8, 8, -temp_delta × 0.6 + nutrient × 2.0)
    return {
        'projected_quality_delta': round(gain, 1),
        'recommendation': '...'
    }
```

| 温度偏移 | nutrient_boost | 质量变化量 | 解读 |
|---------|---------------|-----------|------|
| -5°C | 1 | +5.0 | 大幅降温 + 营养补充 → 质量显著提升 |
| -2°C | 1 | +3.2 | 适度降温 → 质量提升 |
| 0°C | 1 | +2.0 | 仅营养补充 → 小幅提升 |
| +2°C | 1 | +0.8 | 升温但营养补偿 → 几乎持平 |
| +5°C | 1 | -1.0 | 大幅升温 → 质量下降 |

### 8.3 24小时预测

```python
def prediction(tank_id):
    pts = generated(tank_id, 'fermentation_progress', 24)
    cur = pts[-1]['value']          # 当前进度
    hours_left = max(0, (98 - cur) / 2.4)  # 线性估算剩余时间
    return {
        'estimated_completion_time': now + hours_left,
        'current_progress': cur,
        'future_progress': pts[-24:]
    }
```

> 预测基于当前参数的趋势外推，不考虑异常注入的影响，是一个简化模型。

---

## 9. 部署与启动

### 9.1 一键部署

```bash
./deploy_all.sh              # 完整部署（基础设施 + Demo）
./deploy_all.sh --infra-only # 仅基础设施
./deploy_all.sh --demo-only  # 仅 Demo
```

### 9.2 手动启动

```bash
# 1. 初始化孪生
cd wine-ferment-twin
bash scripts/init_wine_twins.sh

# 2. 启动后端
cd winetwin-service
DITTO_BASE_URL="http://$(minikube ip):30525" \
uvicorn app.main:app --host 0.0.0.0 --port 8010

# 3. 启动前端
cd wine-frontend
npm run dev

# 4. 启动仿真器
cd wine-ferment-twin
MQTT_HOST=$(minikube ip) MQTT_PORT=30511 \
python wine-simulator/wine_fermentation_simulator.py --config configs/wine_simulation.yaml
```

### 9.3 服务端口

| 服务 | 端口 | 访问地址 |
|------|------|---------|
| Wine Frontend | 5173 | http://localhost:5173 |
| WineTwin Service | 8010 | http://localhost:8010/docs |
| Grafana | 30718 | http://minikube-ip:30718 |
| Ditto API | 30525 | http://minikube-ip:30525/api/2/things |
| InfluxDB | 30716 | http://minikube-ip:30716 |
| Mosquitto | 30511 | TCP minikube-ip:30511 |

### 9.4 Docker Compose

```yaml
services:
  winetwin-service:
    build: ./winetwin-service
    ports: ["8010:8010"]
    environment:
      DITTO_BASE_URL: http://192.168.49.2:30525
      INFLUX_URL: http://192.168.49.2:30716

  wine-frontend:
    build: ./wine-frontend
    ports: ["5173:80"]
```

---

## 10. 目录结构

```
wine-ferment-twin/
├── configs/
│   ├── alarm_rules.yaml           # 告警阈值配置
│   ├── wine_simulation.yaml       # 仿真参数配置
│   ├── wine_twin_schema.json      # 孪生实例 Schema
│   └── service_config.yaml        # 服务配置
│
├── wine-simulator/                # Python 仿真器
│   ├── wine_fermentation_simulator.py  # 主入口 + 风险评估
│   ├── fermentation_model.py      # 发酵物理模型公式
│   ├── anomaly_injector.py        # 异常注入逻辑
│   ├── mqtt_client.py             # Ditto MQTT 协议发布
│   └── data/generated_csv/        # CSV 数据输出
│
├── winetwin-service/              # FastAPI 后端
│   ├── app/
│   │   ├── main.py                # API 路由
│   │   ├── core/config.py         # 配置加载
│   │   ├── clients/
│   │   │   ├── ditto_client.py    # Ditto REST API
│   │   │   ├── influx_client.py   # InfluxDB Flux 查询
│   │   │   └── mongo_client.py    # MongoDB (预留)
│   │   ├── services/
│   │   │   ├── twin_service.py    # 孪生数据 + 规则评估
│   │   │   ├── rules.py           # 规则引擎
│   │   │   ├── history_service.py # 历史查询 + 降级回算
│   │   │   ├── prediction_service.py  # 预测 + 仿真
│   │   │   ├── alarm_service.py   # 告警查询
│   │   │   ├── quality_service.py # 质量评分
│   │   │   └── recommendation_service.py
│   │   └── schemas/wine.py        # Pydantic 模型
│   └── Dockerfile
│
├── wine-frontend/                 # React 前端
│   ├── src/
│   │   ├── main.tsx               # 主应用入口（含 History/Simulation 组件）
│   │   ├── api/wineApi.ts         # API 调用封装
│   │   ├── components/
│   │   │   ├── three/
│   │   │   │   ├── WineWorkshopScene.tsx  # 3D 车间场景
│   │   │   │   └── FermentationTank.tsx   # 3D 发酵罐模型
│   │   │   ├── charts/
│   │   │   │   └── MetricLineChart.tsx    # ECharts 折线图
│   │   │   └── panels/
│   │   │       ├── AlarmPanel.tsx         # 告警面板
│   │   │       └── RecommendationPanel.tsx # 建议面板
│   │   ├── pages/                 # 页面组件（备用，主入口在 main.tsx）
│   │   └── styles.css             # 全局样式
│   └── Dockerfile
│
├── wine-init/                     # 孪生初始化脚本
│   ├── init_wine_types.py         # 注册类型到 Extended API
│   ├── create_wine_twins.py       # 创建 Thing 实例到 Ditto
│   ├── verify_wine_twins.py       # 验证创建结果
│   └── templates/
│       ├── winery_type.json
│       ├── workshop_type.json
│       └── fermentation_tank_type.json
│
├── scripts/                       # 运维脚本
│   ├── deploy_demo.sh
│   ├── init_wine_twins.sh
│   ├── run_simulator.sh
│   ├── stop_demo.sh
│   ├── check_opentwins.sh
│   └── print_access_urls.sh
│
├── docs/
│   └── simulation-logic.md        # 仿真逻辑详细文档
│
└── docker-compose.yml
```

---

## 11. 技术栈汇总

| 层次 | 技术 | 用途 |
|------|------|------|
| 数字孪生引擎 | Eclipse Ditto 3.3.7 | Thing/Feature/Policy 管理 |
| 消息代理 | Mosquitto 2.0.14 | MQTT 5.0 设备数据接入 |
| 时序数据库 | InfluxDB 2.7.4 | 传感器历史数据存储 |
| 数据采集 | Telegraf 1.36 | MQTT→InfluxDB 桥接 |
| 文档数据库 | MongoDB 6.0.10 | Ditto 状态存储 |
| 可视化 | Grafana 10.2.2 | 仪表盘 + OpenTwins 管理界面 |
| 扩展 API | Node.js | Ditto 类型模板管理 |
| 业务后端 | Python / FastAPI | WineTwin Service |
| 发酵仿真 | Python / paho-mqtt | 虚拟传感器数据生成 |
| 前端 | React 18 + TypeScript | UI 交互 |
| 3D 渲染 | Three.js | 车间场景可视化 |
| 图表 | ECharts | 历史曲线 + 预测曲线 |
| 构建 | Vite | 前端开发服务器 |
| 容器编排 | Kubernetes (Minikube) | 基础设施部署 |
| 包管理 | Helm 3 | K8s 资源编排 |

---

## 12. 已知局限与待改进项

### 12.1 仿真模型

- [ ] 发酵模型为简化的经验公式，未基于真实化学反应动力学
- [ ] CO2 高斯峰与 Brix 指数衰减独立计算，无耦合关系
- [ ] 温度放热项仅与进度相关，未考虑环境温度和冷却系统响应
- [ ] 预测为线性外推，不考虑异常场景

### 12.2 规则引擎

- [ ] 发酵停滞检测硬编码为 `tank_id.endswith('03')`，应为通用逻辑
- [ ] Brix 12h 下降量阈值已定义但未在规则中实现
- [ ] 规则引擎在仿真器和后端独立实现，需维护一致性
- [ ] 无告警抑制/去重/升级机制

### 12.3 前端

- [ ] 3D 场景每次数据更新都重建（useEffect deps 包含 tanks），性能有优化空间
- [ ] Simulation 面板 nutrient_boost 固定为 1，用户无法调整
- [ ] History 面板指标曲线无时间范围选择器
- [ ] 无移动端适配优化
- [ ] 3D 罐体模型较简单，无管道/阀门等细节

### 12.4 后端

- [ ] InfluxDB token 未配置时静默降级，用户无感知
- [ ] 历史降级回算未应用异常注入（回算数据与实时数据不一致）
- [ ] MongoDB client 已创建但未使用
- [ ] 无认证/鉴权机制
- [ ] 无 API 限流

### 12.5 运维

- [ ] 仿真器重启后 elapsed 归零，无法续跑
- [ ] 无数据持久化策略（仿真结束即停止）
- [ ] 日志仅本地文件，无集中收集
- [ ] 无性能监控（Prometheus metrics）

---

## 13. 迭代优化方向建议

### 高优先级

1. **仿真模型升级**：引入基于 Michaelis-Menten 动力学的发酵模型，使温度/CO2/Brix 耦合
2. **规则引擎统一**：将仿真器和后端的规则逻辑抽取为共享库
3. **3D 可视化增强**：添加管道连接、液位动画、气泡效果、温度热力图
4. **历史降级一致性**：回算时应用 anomaly_injector，确保 History 数据与实时一致

### 中优先级

5. **仿真续跑**：支持 elapsed offset 参数，重启后可从断点继续
6. **告警机制完善**：告警抑制/去重/升级/恢复通知
7. **移动端适配**：响应式布局优化
8. **参数扰动增强**：开放 nutrient_boost 滑动条，增加更多可调参数
9. **InfluxDB 状态检测**：前端展示数据来源标识（实时/回算）

### 低优先级

10. **认证鉴权**：JWT / OAuth2 集成
11. **API 限流与熔断**
12. **Prometheus 监控集成**
13. **Docker Compose 全栈部署**（含 Minikube 外的服务）
14. **多语言支持（i18n）**
