# OpenTwins 数字孪生平台 — 项目现状总结

> 本文档旨在为 ChatGPT 提供完整的项目上下文，以便其后续生成数字孪生项目的开发计划书和具体实施细节。

---

## 1. 项目概述

**OpenTwins** 是一个开源的数字孪生（Digital Twin）平台，由西班牙马拉加大学 ERTIS 研究组开发（GitHub: ertis-research/opentwins）。项目当前版本为 **v0.5.0**（Helm Chart v0.6.1），核心定位是：

- 提供一个**模块化、可扩展**的 IoT 数字孪生基础设施
- 通过** Helm Chart** 一键部署到 **Kubernetes** 集群
- 集成多个 Eclipse 基金会和开源生态组件，形成完整的数据采集→孪生建模→可视化链路

我们目前基于该项目进行**二次开发和本地化部署**，主要工作包括：镜像仓库迁移至阿里云（解决国内网络拉取问题）、Minikube 本地开发环境搭建、部署流程自动化、Bug 修复等。

---

## 2. 系统架构

### 2.1 整体数据流

```
物理设备 / IoT 传感器
        │
        ▼
  ┌─────────────┐    ┌──────────────────┐
  │  Mosquitto  │◄───│  Eclipse Hono     │  (可选，设备接入网关)
  │  (MQTT 5.0) │    │  (AMQP/HTTP/MQTT) │
  └──────┬──────┘    └──────────────────┘
         │
         ▼ (Ditto Source Connection: telemetry/#)
  ┌──────────────┐
  │ Eclipse Ditto │  ← 数字孪生核心引擎
  │ (Things 模型) │    管理 Thing / Feature / Policy
  └──────┬───────┘
         │ (Ditto Target Connection: opentwins/#)
         ▼
  ┌─────────────┐         ┌───────────┐
  │  Mosquitto  │◄────────│   Kafka   │  (可选消息中间件)
  │  (目标Topic) │         │           │
  └──────┬──────┘         └───────────┘
         │
         ▼ (Telegraf MQTT Consumer)
  ┌─────────────┐
  │   Telegraf   │  ← 数据采集代理
  └──────┬──────┘
         │
         ▼ (InfluxDB v2 Output)
  ┌─────────────┐         ┌───────────────┐
  │  InfluxDB 2  │◄───────│    MongoDB     │  (Ditto 状态存储 + Extended API)
  │  (时序数据库) │        │  (文档数据库)   │
  └──────┬──────┘         └───────────────┘
         │
         ▼ (Grafana Data Source)
  ┌─────────────────────────────────────┐
  │           Grafana                    │
  │  ┌─────────────────────────────────┐ │
  │  │  OpenTwins 插件                  │ │
  │  │  · ertis-opentwins-app          │ │  ← 数字孪生管理 UI
  │  │  · ertis-unity-panel            │ │  ← 3D 可视化面板
  │  └─────────────────────────────────┘ │
  └─────────────────────────────────────┘
```

### 2.2 核心组件说明

| 组件 | 版本 | 功能 | 部署状态 |
|------|------|------|----------|
| **Eclipse Ditto** | 3.3.7 | 数字孪生核心引擎，管理 Thing（设备影子）、Feature（属性/传感器）、Policy（访问策略） | ✅ 已部署 |
| **Eclipse Hono** | 2.6.6 | IoT 设备接入网关，支持 MQTT/HTTP/AMQP 协议适配 | ❌ 默认关闭 |
| **Mosquitto** | 2.0.14 | MQTT 5.0 消息代理，连接设备与 Ditto | ✅ 已部署 |
| **Kafka** | 22.0.3 | 高吞吐消息队列（替代 Mosquitto 作为 Ditto 目标） | ❌ 默认关闭 |
| **Telegraf** | 1.36-alpine | 数据采集代理，从 MQTT 消费数据写入 InfluxDB | ✅ 已部署 |
| **InfluxDB 2** | 2.7.4-alpine | 时序数据库，存储传感器历史数据 | ✅ 已部署 |
| **MongoDB** | 6.0.10 | 文档数据库，存储 Ditto 状态 + Extended API 元数据 | ✅ 已部署 |
| **Grafana** | 10.2.2 | 可视化仪表盘 + OpenTwins 管理界面 | ✅ 已部署 |
| **Ditto Extended API** | latest | Ditto 扩展 REST API，支持 Type（类型模板）和 Twin 批量操作 | ✅ 已部署 |
| **Ditto Fixer** | alpine | 后台守护进程，检测并修复 Ditto 僵尸连接 | ✅ 已部署 |
| **MQTT-to-Mongo** | ertis/mqtttomongo | MQTT 消息转存 MongoDB 的桥接服务（轻量版使用） | 代码存在但未集成到主 Chart |

---

## 3. 关键技术细节

### 3.1 Eclipse Ditto — 数字孪生核心

Ditto 是整个平台的灵魂，其核心概念：

- **Thing**：一个数字孪生实体（如一辆车、一个传感器），包含 `namespace:name` 形式的 ID
- **Feature**：Thing 的功能属性（如温度、湿度、GPS 坐标），结构为 `properties.value`
- **Policy**：访问控制策略，定义谁可以对 Thing 执行什么操作
- **Connection**：Ditto 与外部系统（MQTT、AMQP、Kafka）的连接通道

**连接配置**（自动创建）：
- **Source Connection**：Ditto 从 Mosquitto 订阅 `telemetry/#` 主题，接收设备上报数据
- **Target Connection**：Ditto 将孪生变更事件发布到 Mosquitto 的 `opentwins/#` 主题，携带额外字段（thingId、_parents、idSimulationRun）

**策略配置**（post-install 自动创建）：
- `default:basic_policy` — 默认策略，允许 Hono 和 KafkaML 连接的预认证访问
- `opentwins:basic_policy` — OpenTwins 专用策略，额外允许 nginx:ditto 用户访问

### 3.2 Ditto Extended API

自研的 Node.js 服务（端口 3000，通过 Nginx 反代到 8080），提供比原生 Ditto API 更高级的操作：

- **Type 管理**：定义数字孪生类型模板（如"树莓派类型"、"DHT22 传感器类型"），包含属性和 Feature 定义
- **Twin 创建**：基于 Type 批量实例化数字孪生
- **层级关系**：支持 Twin 之间的父子关系（如树莓派→传感器）
- **环境变量**：
  - `MONGO_URI_POLICIES`：连接 MongoDB 存储 Policy 元数据
  - `DITTO_URI_THINGS`：连接 Ditto 进行 Thing CRUD
  - 认证信息通过 Ditto basic auth 传递

### 3.3 数据采集链路 (Telegraf + InfluxDB)

**Telegraf 配置**（由 ConfigMap 动态生成）：
- **输入**：`mqtt_consumer` 插件，订阅 `opentwins/#` 主题
- **JSON 解析**：使用 `json_v2` 格式，提取：
  - `extra.thingId` → tag（用于查询过滤）
  - `extra.attributes._parents` → tag（父孪生关联）
  - `headers.ditto-originator` → tag
  - `value.features.*` → measurement 字段
- **输出**：`influxdb_v2` 插件，写入 InfluxDB 2（organization: opentwins, bucket: opentwins）

**Grafana 集成**：
- InfluxDB 2 作为数据源自动注册到 Grafana（通过 sidecar ConfigMap）
- 使用 Flux 查询语言
- OpenTwins 插件直接调用 Ditto API + Extended API 进行孪生管理

### 3.4 Ditto Fixer — 连接修复守护进程

一个 Alpine 容器中运行的 Shell 脚本，每 30 秒执行一次：

1. **健康检查**：调用 Ditto Gateway 的 `/status/health` 接口
2. **备份**：当 Ditto UP 时，将所有 `open` 状态的 Connection ID 持久化到 PVC
3. **恢复**：当 Ditto 重启后，检测 recovery flag，重新打开之前活跃的连接
4. **僵尸连接防护**：API 返回空列表时不覆盖快照，保留最后已知良好状态

---

## 4. 部署架构

### 4.1 当前部署环境

- **平台**：Minikube（单节点 Kubernetes）
- **部署方式**：Helm Chart（`helm upgrade --install`）
- **命名空间**：`opentwins`
- **镜像仓库**：阿里云容器镜像服务（`crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/`）

### 4.2 服务暴露（NodePort）

| 服务 | NodePort | 集群内端口 | 用途 |
|------|----------|-----------|------|
| Grafana | 30718 | 80 | 可视化界面 (admin/Test123456!) |
| Ditto Nginx | 30525 | 80 | Ditto REST API (ditto/ditto) |
| Extended API | 30526 | 8080 | 扩展 API |
| Mosquitto | 30511 | 1883 | MQTT Broker |
| InfluxDB 2 | 30716 | 80 | 时序数据库 |
| MongoDB | 30717 | 27017 | 文档数据库 |

### 4.3 部署自动化脚本

`redeploy_steps.sh` 实现了完全自动化的一键重新部署流程：

1. **前置检查**：Clash 代理状态、Minikube 运行状态、阿里云镜像仓库登录
2. **镜像预加载**：从 Helm template 提取镜像列表 → 检查 minikube/宿主机缓存 → docker pull → minikube image load
3. **Grafana 插件**：检查 hostPath `/mnt/data/grafana-plugins/` 中的 `ertis-opentwins-app.zip` 和 `ertis-unity-panel.zip`
4. **完全卸载**：helm uninstall → namespace 删除 → 强制清除 Terminating 状态的 finalizers
5. **模板验证**：`helm template` 渲染并检查 image 配置
6. **Helm 部署**：`--wait --timeout 15m --dependency-update`
7. **Pod 就绪检查**：等待所有 Pod Running（telegraf 可能有短暂重启属正常）
8. **Post-install Job 验证**：检查 Ditto policies 创建是否成功
9. **Policy 手动修复**：如自动创建失败，手动创建 `opentwins:basic_policy`

### 4.4 Helm Chart 依赖关系

```
OpenTwins (umbrella chart)
├── ditto 3.3.7          (oci://registry-1.docker.io/eclipse)
├── mongodb ~13.18.5     (oci://registry-1.docker.io/bitnamicharts)
├── grafana ~10.1.2      (https://grafana.github.io/helm-charts)
├── influxdb2 ~2.1.1     (https://helm.influxdata.com/)
├── telegraf ^1.8.27     (https://helm.influxdata.com/)
├── mosquitto ~0.3.1     (https://ertis-research.github.io/Helm-charts/)
├── kafka ~22.0.0        (https://charts.bitnami.com/bitnami) [默认关闭]
└── hono ^2.5.5          (https://eclipse.org/packages/charts/) [默认关闭]
```

---

## 5. Grafana 插件体系

### 5.1 ertis-opentwins-app

OpenTwins 的核心 Grafana 应用插件，提供：
- 数字孪生管理界面（创建/编辑/删除 Thing）
- Type 模板管理
- 孪生层级关系可视化
- 实时数据查看

### 5.2 ertis-unity-panel

3D 可视化面板插件，基于 Unity 引擎：
- 将数字孪生数据映射到 3D 模型
- 实时更新 3D 场景中的设备状态

### 5.3 插件安装机制

由于网络限制，插件通过 initContainer 从 hostPath 拷贝安装：
```yaml
extraInitContainers:
- name: install-opentwins-plugins
  image: busybox:1.31.1
  command:
    - /bin/sh
    - -c
    - |
      mkdir -p /grafana-storage/plugins
      cd /grafana-storage/plugins
      cp /plugins-src/ertis-opentwins-app.zip .
      unzip -o ertis-opentwins-app.zip
      cp /plugins-src/ertis-unity-panel.zip .
      unzip -o ertis-unity-panel.zip
```

插件配置通过 sidecar ConfigMap 自动注入，包含 Ditto URL、Extended API URL 和认证信息。

---

## 6. 示例数字孪生

项目提供了一个 Raspberry Pi + DHT22 温湿度传感器的示例：

**孪生层级**：
```
Raspberry Pi 3B (example:raspberry)
├── DHT22_1 (raspberry:DHT22_1) — 温湿度传感器 1
│   ├── feature: humidity → { value: null }
│   └── feature: temperature → { value: null }
└── DHT22_2 (raspberry:DHT22_2) — 温湿度传感器 2
    ├── feature: humidity → { value: null }
    └── feature: temperature → { value: null }
```

**数据模拟器**（`get_data_simulate.py`）：
- 使用 `paho-mqtt` 库连接 Mosquitto
- 按照 Ditto 协议格式发送数据：
  ```json
  {
    "topic": "namespace/thing_name/things/twin/commands/merge",
    "headers": { "content-type": "application/merge-patch+json" },
    "path": "/features",
    "value": { ... },
    "extra": { "thingId": "namespace:thing_name", "attributes": { "_parents": [...] } }
  }
  ```
- 示例包含汽车 GPS + 4 个轮子的速度/方向数据模拟

---

## 7. OpenTwins 轻量版

`OpenTwins-Lightweight`（v0.4.1）是精简版部署方案：
- 仅包含 Eclipse Ditto + MongoDB + Mosquitto
- 不含 InfluxDB、Grafana、Telegraf 等可视化和数据采集组件
- 适合只需要数字孪生建模核心能力的场景
- 连接配置需手动完成（尚未自动化）

---

## 8. 本地化与定制化工作

### 8.1 镜像仓库迁移

所有 Docker Hub 镜像已迁移至阿里云容器镜像服务：
- 原地址：`docker.io/eclipse/ditto-gateway:3.3.7` 等
- 新地址：`crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/ditto-gateway:3.3.7` 等

### 8.2 网络代理配置

- Minikube Docker daemon 通过 `192.168.49.1:7890` 代理拉取镜像
- 宿主机 Clash 代理提供网络出口
- kubectl/helm 访问集群内 IP 不走代理（`no_proxy` 配置）

### 8.3 Grafana 插件本地化

- 原方案：从 GitHub Releases 下载（国内网络不可用，OSS URL 过期，代理 502）
- 当前方案：预下载到 `/tmp/`，通过 `minikube cp` 拷贝到 hostPath `/mnt/data/grafana-plugins/`

---

## 9. 已知问题与待改进项

### 9.1 当前已知问题
- Ditto Policies Bootstrap 不适用于 Chart v3.3.7（环境变量被 subchart 默认值覆盖），改用 post-install job 创建
- Ditto 可能出现僵尸连接（既非 open 也非 closed 状态），需要 Fixer 守护进程修复
- Telegraf 在 Mosquitto 就绪前会重启 1-2 次（正常现象但影响部署体验）
- Namespace 删除可能卡在 Terminating 状态，需手动清除 finalizers

### 9.2 功能缺失 / 待开发
- ❌ 设备认证与安全机制（当前 Mosquitto 和 Ditto 均关闭了 Policy 强制执行）
- ❌ 多租户支持
- ❌ 告警与通知系统
- ❌ 数字孪生仿真引擎（当前仅支持数据镜像，不支持仿真推演）
- ❌ 规则引擎（事件触发自动操作）
- ❌ 设备管理生命周期（注册→上线→下线→注销）
- ❌ 3D 可视化深度集成（Unity Panel 功能有限）
- ❌ 历史数据回放与时间旅行（查看孪生在过去某时刻的状态）
- ❌ API Gateway / 统一入口
- ❌ 多集群 / 边缘部署支持
- ❌ CI/CD 流水线
- ❌ 性能监控与可观测性（Prometheus metrics）
- ❌ 数据备份与灾难恢复

---

## 10. 技术栈汇总

| 层次 | 技术 |
|------|------|
| 容器编排 | Kubernetes (Minikube) |
| 包管理 | Helm 3 |
| 数字孪生引擎 | Eclipse Ditto 3.3.7 |
| 设备接入 | Eclipse Hono 2.6.6 / Mosquitto 2.0.14 |
| 消息中间件 | Mosquitto (MQTT 5.0) / Kafka (可选) |
| 数据采集 | Telegraf 1.36 |
| 时序数据库 | InfluxDB 2.7.4 |
| 文档数据库 | MongoDB 6.0.10 |
| 可视化 | Grafana 10.2.2 + 自研插件 |
| 扩展 API | Node.js (Ditto Extended API) + Nginx 反代 |
| 数据模拟 | Python 3 (paho-mqtt) |
| 镜像仓库 | 阿里云容器镜像服务 |
| 代理 | Clash (HTTP Proxy) |

---

## 11. 项目目录结构

```
opentwins/
├── OpenTwins/                      # 主 Helm Chart（完整版）
│   ├── Chart.yaml                  # Chart 元数据 (v0.6.1, appVersion 0.5.0)
│   ├── values.yaml                 # 核心配置文件（所有组件参数）
│   ├── requirements.yaml           # Chart 依赖定义
│   ├── charts/                     # 依赖 Chart 的 .tgz 包
│   ├── templates/                  # Kubernetes 资源模板
│   │   ├── config-maps/            #   Telegraf、Grafana 数据源、插件配置
│   │   ├── extended-api/           #   Ditto Extended API 部署、Nginx 配置、Service
│   │   ├── fixers/                 #   Ditto 僵尸连接修复守护进程
│   │   ├── persistent-volumes/     #   Grafana/Hono/InfluxDB 的 PV 和 StorageClass
│   │   ├── post-install-jobs/      #   Helm post-install Hook（创建连接/策略/示例）
│   │   └── secrets/                #   各种连接凭据 Secret
│   ├── post-install/               # Post-install 脚本和 JSON 配置
│   │   ├── ditto-connection/       #   通用 Ditto 连接管理函数库
│   │   ├── ditto-default/          #   默认 Policy 创建脚本
│   │   ├── ditto-hono-connection/  #   Hono AMQP/Kafka 连接配置
│   │   ├── ditto-mosquitto-connection/ # Mosquitto Source/Target 连接配置
│   │   └── example-raspberry/      #   树莓派+DHT22 示例孪生
│   ├── get_data_simulate.py        # 数据模拟脚本（汽车 GPS+轮子）
│   ├── redeploy_steps.sh           # 完全重新部署自动化脚本
│   └── opentwins_ditto_fixer_pvc.yaml # Ditto Fixer PVC 手动资源
│
├── OpenTwins-Lightweight/          # 轻量版 Helm Chart（仅 Ditto+MongoDB+Mosquitto）
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
│
├── OpenTwins-MongoDB/              # 独立 MongoDB Helm Chart（备选，当前用 Bitnami）
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/                  # 自定义 PV/PVC/StorageClass
│
├── mosquitto/                      # Mosquitto Helm Chart
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/                  # Deploy/Service/ConfigMap/Secret
│
├── mqtttomongo/                    # MQTT→MongoDB 桥接服务 Chart
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
│
└── passwd                          # Mosquitto 密码文件
```

---

## 12. 对下一步开发的期望

本项目的当前状态是一个**可运行的 MVP（最小可行产品）**，具备基本的数字孪生数据镜像和可视化能力。下一步数字孪生项目开发计划应重点考虑：

1. **仿真推演能力**：从"数据镜像"升级到"仿真预测"，支持基于模型的状态推演
2. **安全加固**：启用 Ditto Policy 强制执行、Mosquitto 认证、TLS 加密通信
3. **规则引擎**：基于孪生状态变化触发告警或自动操作
4. **多协议接入**：扩展 Hono 部署，支持更多 IoT 协议（CoAP、LoRaWAN 等）
5. **3D 可视化深化**：增强 Unity Panel 或替换为 Web-based 3D 方案（Three.js/xeokit）
6. **边缘部署**：支持 K3s 等轻量级 Kubernetes，在边缘节点运行数字孪生
7. **数据治理**：历史数据回放、数据质量监控、数据生命周期管理
8. **可观测性**：Prometheus 指标采集、链路追踪、统一日志
9. **CI/CD**：自动化测试、持续集成、GitOps 部署
10. **多租户与权限**：企业级多租户隔离、RBAC 权限模型
