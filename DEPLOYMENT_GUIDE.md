# OpenTwins + WineFermentTwin 部署与启动流程文档

## 一、整体架构概览

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Minikube (K8s 集群)                          │
│                                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌─────────┐ │
│  │ Eclipse  │ │ Mosquitto│ │ InfluxDB │ │  Grafana  │ │Telegraf │ │
│  │  Ditto   │ │  MQTT    │ │          │ │ + ERTIS   │ │         │ │
│  │(twin管理)│ │(消息代理) │ │(时序数据) │ │ (可视化)   │ │(采集桥接)│ │
│  └────┬─────┘ └────┬─────┘ └──────────┘ └───────────┘ └─────────┘ │
│       │             │         NodePort 暴露:                       │
└───────┼─────────────┼───────── 30525 (Ditto)                      │
        │             │           30526 (Extended API)                │
        │             │           30511 (Mosquitto)                   │
        │             │           30716 (InfluxDB)                    │
        │             │           30718 (Grafana)                     │
─────────┼─────────────┼──────────────────────────────────────────────
        │             │  宿主机
        │             │
   ┌────┴─────┐ ┌─────┴──────────┐  ┌────────────────┐  ┌────────────┐
   │ WineTwin │ │ Wine Simulator │  │ Wine Frontend  │  │ get_data   │
   │ Service  │ │  (虚拟传感器)   │  │  (React+3D)    │  │_simulate.py│
   │ (FastAPI)│ │  (Python)      │  │  (Vite)        │  │(原始示例)   │
   │  :8010   │ │  (MQTT发布)    │  │   :5173        │  │ (MQTT发布) │
   └──────────┘ └────────────────┘  └────────────────┘  └────────────┘
```

## 二、部署顺序与依赖关系

部署必须**按顺序**进行，因为上层依赖底层服务：

```
1. Minikube 启动 (含 Docker 代理配置)
   ↓
2. OpenTwins 基础设施 (Helm 部署: Ditto, Mosquitto, InfluxDB, Grafana, Telegraf)
   ↓
3. Post-install Job (Ditto policies 初始化)
   ↓
4. WineFermentTwin Demo
   4a. Python venv + 依赖安装
   4b. 初始化 Wine Twin 类型 (init_wine_types.py)
   4c. 创建 Wine Twin 实例 (create_wine_twins.py)
   4d. 验证 Twin 创建 (verify_wine_twins.py)
   4e. 启动 WineTwin Service (FastAPI, port 8010)
   4f. 启动 Wine Frontend (Vite, port 5173)
   4g. 启动 Wine Simulator (虚拟传感器数据发送)
```

## 三、统一部署脚本

### 3.1 完整部署（基础设施 + Demo）

```bash
./deploy_all.sh
```

这会依次执行：
- **阶段 A**: Minikube 启动 → 镜像预加载 → Grafana 插件检查 → Helm 部署 OpenTwins → 等待 Pods 就绪 → Post-install Job → Ditto Policies 验证
- **阶段 B**: 检查基础设施连通性 → Python 依赖安装 → 初始化 Wine Twin → 启动三个服务

### 3.2 仅部署基础设施

```bash
./deploy_all.sh --infra-only
```

适用于：基础设施已部署，只需要重新部署 K8s 内的服务。

### 3.3 仅部署 WineTwin Demo

```bash
./deploy_all.sh --demo-only
```

适用于：OpenTwins 基础设施已在运行，只需要部署/重启 Wine Demo。

### 3.4 其他选项

```bash
./deploy_all.sh --host-ip 192.168.1.100          # 指定本机 IP
./deploy_all.sh --opentwins-ip 192.168.49.2       # 指定 OpenTwins IP
./deploy_all.sh --skip-images                      # 跳过镜像预加载
```

### 3.5 停止服务

```bash
./stop_all.sh                # 仅停止 WineTwin Demo 进程
./stop_all.sh --infra        # 停止 Demo + 卸载 OpenTwins (helm uninstall)
./stop_all.sh --infra-full   # 停止 Demo + 卸载 + 停止 minikube
```

## 四、Python 虚拟传感器数据发送 — 详解

项目中有 **两个** Python 虚拟传感器数据发送程序，对应两个不同的 Demo：

### 4.1 Wine Fermentation Simulator（WineTwin Demo）

| 项目 | 说明 |
|------|------|
| **入口文件** | `wine-ferment-twin/wine-simulator/wine_fermentation_simulator.py` |
| **配置文件** | `wine-ferment-twin/configs/wine_simulation.yaml` |
| **何时启动** | 在 `deploy_all.sh` 阶段 B4 中自动以后台进程启动 |
| **启动方式** | `setsid -f python wine_fermentation_simulator.py --config configs/wine_simulation.yaml` |
| **也可手动启动** | `bash wine-ferment-twin/scripts/run_simulator.sh` |
| **数据目标** | Mosquitto MQTT (`${OPENTWINS_HOST_IP}:30511`) |
| **MQTT Topic** | `telemetry/wine/{tank_id}` (Ditto 协议格式) |
| **发送频率** | 每 5 秒一次 |
| **模拟内容** | 3 个发酵罐 (tank_01/02/03) 的温度、pH、Brix、CO2、压力等 9 项指标 + 风险评分 |
| **时间加速** | 速度 3600x（5 秒真实时间 = 5 小时模拟时间），12 天发酵周期约 15 分钟跑完 |
| **数据输出** | MQTT → Ditto (数字孪生更新) + CSV 文件 (`wine-simulator/data/generated_csv/`) |
| **异常注入** | tank_02 注入高温异常，tank_03 注入发酵停滞 |
| **停止方式** | `pkill -f wine_fermentation_simulator.py` 或 `./stop_all.sh` |

**数据流路径**：
```
wine_fermentation_simulator.py
  → fermentation_model.py (物理模型计算)
  → anomaly_injector.py (异常注入)
  → mqtt_client.py (DittoMqttPublisher, 发送 Ditto 协议格式消息)
  → Mosquitto MQTT broker
  → Ditto (通过 Mosquitto 连接自动同步)
  → WineTwin Service (通过 Ditto API 读取/写入)
  → Wine Frontend (通过 WineTwin Service API 获取数据展示)
```

### 4.2 get_data_simulate.py（OpenTwins 原始示例）

| 项目 | 说明 |
|------|------|
| **入口文件** | `OpenTwins/get_data_simulate.py` |
| **何时启动** | **需手动启动**，不在任何自动部署脚本中 |
| **启动方式** | `cd OpenTwins && python3 get_data_simulate.py` |
| **数据目标** | Mosquitto MQTT (硬编码 `192.168.49.2:30511`) |
| **MQTT Topic** | `opentwins/example/car_1` (Ditto 协议格式) |
| **发送频率** | 每 5 秒一次 |
| **模拟内容** | 1 辆汽车的 GPS + 4 个轮子的速度和方向 |
| **数据输出** | 仅 MQTT → Ditto |
| **停止方式** | Ctrl+C 或 `pkill -f get_data_simulate.py` |

**注意事项**：
- 此脚本中 MQTT broker 地址硬编码为 `192.168.49.2`，如果 minikube IP 变化需要手动修改
- 此脚本**不是** WineTwin Demo 的一部分，是 OpenTwins 项目自带的简单演示
- WineTwin Demo 和此示例可以同时运行（它们发送到不同的 MQTT topic namespace）

## 五、两个脚本的关系与定位

| | `OpenTwins/redeploy_steps.sh` | `wine-ferment-twin/scripts/deploy_demo.sh` | `deploy_all.sh` (统一) |
|---|---|---|---|
| **职责** | 部署 K8s 基础设施 | 部署 Wine Demo 应用 | 两者合并，顺序执行 |
| **运行环境** | 需要宿主机 Docker、minikube、helm | 需要基础设施已就绪 | 一键完成 |
| **是否自动** | 完全自动 | 完全自动 | 完全自动 |
| **单独使用** | ✅ 可独立运行 | ✅ 可独立运行 | ✅ 可独立运行 |

## 六、服务端口一览

| 服务 | 端口 | 访问方式 |
|------|------|---------|
| Grafana + ERTIS 插件 | 30718 | `http://{minikube-ip}:30718` |
| Ditto API | 30525 | `http://{minikube-ip}:30525/api/2/things` |
| Extended API | 30526 | `http://{minikube-ip}:30526` |
| InfluxDB | 30716 | `http://{minikube-ip}:30716` |
| Mosquitto MQTT | 30511 | TCP `{minikube-ip}:30511` |
| WineTwin Service (FastAPI) | 8010 | `http://{host-ip}:8010/docs` |
| Wine Frontend (React) | 5173 | `http://{host-ip}:5173` |

## 七、常见操作

### 查看各服务日志

```bash
# WineTwin Demo 日志
tail -f wine-ferment-twin/logs/winetwin-service.log    # FastAPI 服务
tail -f wine-ferment-twin/logs/wine-frontend.log       # 前端
tail -f wine-ferment-twin/logs/wine-simulator.log      # 虚拟传感器

# K8s 基础设施日志
kubectl logs -n opentwins -l app.kubernetes.io/name=ditto-gateway --tail=50
kubectl logs -n opentwins -l app.kubernetes.io/name=mosquitto --tail=50
```

### 仅重启 Wine Simulator

```bash
pkill -f wine_fermentation_simulator.py
cd wine-ferment-twin
MQTT_HOST=$(minikube ip) MQTT_PORT=30511 \
  python wine-simulator/wine_fermentation_simulator.py --config configs/wine_simulation.yaml
```

### 仅重启 WineTwin Service

```bash
pkill -f "uvicorn app.main:app"
cd wine-ferment-twin/winetwin-service
DITTO_BASE_URL="http://$(minikube ip):30525" \
INFLUX_URL="http://$(minikube ip):30716" \
uvicorn app.main:app --host 0.0.0.0 --port 8010
```
