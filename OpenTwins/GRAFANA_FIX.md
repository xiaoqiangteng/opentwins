# Grafana 数据接收问题修复

## 问题原因

**配置不一致**：
- Telegraf 写入数据到 `default` bucket
- Grafana 查询从 `opentwins` bucket 读取数据
- 导致 Grafana 无法显示数据，报错：`could not find bucket "opentwins"`

## 修复方案

### 1. 修改 values.yaml（第 252 行）

```yaml
# 修改前
adminUser:
  organization: "opentwins"
  bucket: "default"  # ❌ 错误
  password: "Test123456!"

# 修改后
adminUser:
  organization: "opentwins"
  bucket: "opentwins"  # ✅ 正确
  password: "Test123456!"
```

### 2. 配置已更新的内容

**Telegraf 配置** (`templates/config-maps/cm-telegraf.yaml`):
- 自动使用 `values.yaml` 中的 `influxdb2.adminUser.bucket`
- 现在写入 `opentwins` bucket

**Grafana 数据源** (`templates/config-maps/cm-influxdb-grafana-datasource.yaml`):
- 自动使用 `values.yaml` 中的 `influxdb2.adminUser.bucket`
- 现在从 `opentwins` bucket 读取

### 3. InfluxDB Buckets

系统中有以下 buckets：
- `opentwins` - **主要数据 bucket**（现在使用）
- `default` - 默认 bucket（旧数据）
- `_monitoring` - InfluxDB 内部监控
- `_tasks` - InfluxDB 任务

## 验证步骤

### 1. 确认配置正确

```bash
# 检查 Telegraf 配置
kubectl exec -n opentwins deployment/opentwins-telegraf -- \
  cat /additional_config/telegraf.conf | grep "bucket ="

# 应该看到：bucket = "opentwins"
```

### 2. 确认数据写入

```bash
# 查询 opentwins bucket 中的数据
kubectl exec -n opentwins statefulset/opentwins-influxdb2 -- \
  influx query \
  --host http://localhost:8086 \
  --org opentwins \
  --token "Hjh3ysMQ6evK=qqpFSYqn-s3JGovJLfHxyCDM=eNNZkdM-uuro93dNtJcodejLYYob2geKQ/29z3Kxui=y6FlL?dZeU9EFRxrYn284V/kZG5==jxLVAMJrYOv?LF79ahwIbhvstMN6gmfQ3DH7/IzUB7VlBZK-cd8aN7YqiFrYRLkBUv7H0QkbqPxgf2dMgCMCwZaLMk9RUeMaBfx2lQ=Mq1EEJJw-Jp!BmpCDnhlc!6D22PaE=Y3sgWWNhRv8oP" \
  'from(bucket: "opentwins") |> range(start: -5m) |> limit(n: 10)'
```

### 3. 在 Grafana 中验证

1. **打开 Grafana**
   - URL: http://192.168.49.2:30718
   - 登录: `admin` / `Test123456!`

2. **测试数据源连接**
   - 进入 Configuration → Data Sources
   - 选择 "opentwins" 数据源
   - 点击 "Save & Test"
   - 应该显示 "✓ Data source is working"

3. **在 Explore 中查询数据**
   - 进入 Explore 页面
   - 选择 "opentwins" 数据源
   - 使用以下 Flux 查询：
   ```flux
   from(bucket: "opentwins")
     |> range(start: -5m)
     |> filter(fn: (r) => r["_measurement"] == "mqtt_consumer")
   ```
   - 应该能看到你的数据

## 下次重新部署

只需运行：
```bash
cd /home/teng/programmings/git/Helm_charts/OpenTwins
helm upgrade --install opentwins ./ \
  --namespace opentwins \
  --create-namespace \
  -f values.yaml \
  --wait \
  --dependency-update
```

所有配置都已正确，Grafana 会自动：
- ✅ 配置 InfluxDB 数据源
- ✅ 使用正确的 bucket (`opentwins`)
- ✅ 自动连接并显示数据

## 数据流程

```
你的脚本 (get_data_simulate.py)
    ↓ (MQTT publish)
Mosquitto (topic: opentwins/#)
    ↓ (MQTT subscribe)
Telegraf (mqtt_consumer)
    ↓ (write)
InfluxDB2 (bucket: opentwins)
    ↓ (Flux query)
Grafana (datasource: opentwins)
    ↓
可视化显示
```

## 常见问题

### Q: 看不到数据？
A: 等待 5-10 秒让新数据写入，Telegraf 每 10 秒采集一次。

### Q: 旧数据在哪里？
A: 在 `default` bucket 中。如果需要，可以在 InfluxDB UI 中查看：
   - http://192.168.49.2:30716
   - 登录: `admin` / `Test123456!`

### Q: 如何查看所有 buckets？
A:
```bash
kubectl exec -n opentwins statefulset/opentwins-influxdb2 -- \
  influx bucket list --host http://localhost:8086 --org opentwins \
  --token "Hjh3ysMQ6evK=qqpFSYqn-s3JGovJLfHxyCDM=eNNZkdM-uuro93dNtJcodejLYYob2geKQ/29z3Kxui=y6FlL?dZeU9EFRxrYn284V/kZG5==jxLVAMJrYOv?LF79ahwIbhvstMN6gmfQ3DH7/IzUB7VlBZK-cd8aN7YqiFrYRLkBUv7H0QkbqPxgf2dMgCMCwZaLMk9RUeMaBfx2lQ=Mq1EEJJw-Jp!BmpCDnhlc!6D22PaE=Y3sgWWNhRv8oP"
```

## 关键文件

- `values.yaml` 第 252 行 - bucket 配置
- `templates/config-maps/cm-telegraf.yaml` - Telegraf 配置模板
- `templates/config-maps/cm-influxdb-grafana-datasource.yaml` - Grafana 数据源模板

## 修复完成

✅ values.yaml 已修改
✅ bucket 统一为 "opentwins"
✅ Telegraf 配置已更新
✅ Grafana 数据源已更新
✅ 配置已重新加载

现在你的数据应该能在 Grafana 中正常显示了！
