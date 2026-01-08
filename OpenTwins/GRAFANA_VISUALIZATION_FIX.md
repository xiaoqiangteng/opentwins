# Grafana 可视化无数据问题修复

## 问题原因

你的 Flux 查询中使用的字段名不正确。

### 错误的字段名（你的查询）
```
value_gps_properties_latitude
value_gps_properties_longitude
```

### 正确的字段名（应该使用）
```
value_gps_properties_value_latitude
value_gps_properties_value_longitude
```

## 为什么字段名不同？

### MQTT 消息格式
```json
{
  "value": {
    "gps": {
      "properties": {
        "value": {
          "latitude": -62.540978,
          "longitude": 14.983789
        }
      }
    }
  },
  "extra": {
    "thingId": "example:car_1"
  }
}
```

### Telegraf json_v2 解析规则
Telegraf 的 `json_v2` 配置会将嵌套的 JSON 对象展平为字段名：
- 路径: `value.gps.properties.value.latitude`
- 字段名: `value_gps_properties_value_latitude`（用下划线连接所有层级）

你漏掉了中间的一个 `value_`！

## 修复方案

### 方法 1：使用正确的字段名（推荐）

#### GPS 位置可视化（Geomap - 显示最后位置）

```flux
import "strings"
from(bucket: "opentwins")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "mqtt_consumer")
  |> filter(fn: (r) => r["thingId"] == "example:car_1")
  |> filter(fn: (r) =>
      r["_field"] == "value_gps_properties_value_latitude" or
      r["_field"] == "value_gps_properties_value_longitude")
  |> map(fn: (r) => ({
      r with _field: strings.replace(
        v: r["_field"],
        t: "value_gps_properties_value_",
        u: "",
        i: 1
      )
  }))
  |> keep(columns: ["_value", "_field", "_time"])
  |> sort(columns: ["_time"], desc: false)
  |> last()
```

**配置 Geomap 面板**:
1. 面板类型: **Geomap**
2. Format: **Auto**
3. Map view: 选择合适的中心点和缩放级别
4. 数据层 -> Markers: 启用

#### GPS 轨迹可视化（Geomap - 显示完整路径）

```flux
import "strings"
from(bucket: "opentwins")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "mqtt_consumer")
  |> filter(fn: (r) => r["thingId"] == "example:car_1")
  |> filter(fn: (r) =>
      r["_field"] == "value_gps_properties_value_latitude" or
      r["_field"] == "value_gps_properties_value_longitude")
  |> map(fn: (r) => ({
      r with _field: strings.replace(
        v: r["_field"],
        t: "value_gps_properties_value_",
        u: "",
        i: 1
      )
  }))
  |> keep(columns: ["_value", "_field", "_time"])
  |> sort(columns: ["_time"], desc: false)
```

**配置 Geomap 面板**:
1. 面板类型: **Geomap**
2. Format: **Auto**
3. 数据层 -> **Route** 或 **Path**: 启用（显示轨迹线）
4. 可选: 同时启用 Markers 显示路径点

### 方法 2：调试查询（找出可用字段）

如果不确定字段名，先运行这个查询查看所有可用字段：

```flux
from(bucket: "opentwins")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "mqtt_consumer")
  |> filter(fn: (r) => r["thingId"] == "example:car_1")
  |> keep(columns: ["_field"])
  |> distinct(column: "_field")
```

这会列出 `example:car_1` 的所有字段名。

## 其他有用的查询

### 1. 查看所有 thingId

```flux
from(bucket: "opentwins")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "mqtt_consumer")
  |> keep(columns: ["thingId"])
  |> distinct(column: "thingId")
```

### 2. 车轮速度时序图

```flux
from(bucket: "opentwins")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "mqtt_consumer")
  |> filter(fn: (r) =>
      r["thingId"] =~ /example:car_1:wheel_.*/)
  |> filter(fn: (r) => r["_field"] == "value_velocity_properties_value")
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
```

**面板类型**: Time series

### 3. 车轮方向时序图

```flux
from(bucket: "opentwins")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "mqtt_consumer")
  |> filter(fn: (r) =>
      r["thingId"] =~ /example:car_1:wheel_.*/)
  |> filter(fn: (r) => r["_field"] == "value_direction_properties_value")
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
```

**面板类型**: Time series

### 4. 最新的 GPS 时间戳

```flux
from(bucket: "opentwins")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "mqtt_consumer")
  |> filter(fn: (r) => r["thingId"] == "example:car_1")
  |> filter(fn: (r) => r["_field"] == "value_gps_properties_value_time")
  |> last()
```

**面板类型**: Stat

## 在 Grafana 中使用步骤

### 步骤 1: 创建新 Dashboard
1. 登录 Grafana: http://192.168.49.2:30718
2. 用户名: `admin`, 密码: `Test123456!`
3. 点击左侧 "+" -> "Dashboard"
4. 点击 "Add visualization"

### 步骤 2: 选择数据源
选择 **opentwins** 数据源

### 步骤 3: 配置查询
1. 切换到 **Code** 模式（右上角）
2. 粘贴上面的 Flux 查询
3. 设置时间范围（例如 "Last 15 minutes"）
4. 点击 "Run query"

### 步骤 4: 配置可视化
根据数据类型选择合适的面板类型：
- **GPS 数据**: Geomap
- **时序数据**: Time series
- **单值**: Stat

### 步骤 5: 保存 Dashboard
点击右上角 "Save dashboard"

## 验证数据是否存在

### 在 Grafana Explore 中
1. 进入 **Explore**（左侧菜单）
2. 选择 **opentwins** 数据源
3. 运行简单查询：
```flux
from(bucket: "opentwins")
  |> range(start: -15m)
  |> filter(fn: (r) => r["_measurement"] == "mqtt_consumer")
  |> limit(n: 10)
```

### 在 InfluxDB UI 中
1. 打开 http://192.168.49.2:30716
2. 登录: `admin` / `Test123456!`
3. 进入 Data Explorer
4. 选择 `opentwins` bucket
5. 选择 `mqtt_consumer` measurement
6. 查看可用字段

## 常见问题

### Q: 查询返回空结果？
A: 检查以下几点：
1. 时间范围是否包含数据（扩大到 Last 1 hour）
2. thingId 是否正确（大小写敏感）
3. 字段名是否完整（包含所有 `value_` 前缀）
4. Python 脚本是否正在发送数据
5. Telegraf 是否正常运行：`kubectl logs -n opentwins deployment/opentwins-telegraf --tail=20`

### Q: Geomap 不显示位置？
A: 确保：
1. 数据格式包含 `latitude` 和 `longitude` 字段
2. 纬度范围：-90 到 90
3. 经度范围：-180 到 180
4. 在 Geomap 面板设置中启用了 Markers 或 Route

### Q: 如何查看原始 MQTT 消息？
A:
```bash
kubectl exec -n opentwins deployment/opentwins-mosquitto -- \
  mosquitto_sub -h localhost -t 'opentwins/#' -C 5
```

## 数据流程确认

```
Python 脚本 (get_data_simulate.py)
    ↓ 发送 JSON 到 MQTT
Mosquitto (topic: opentwins/*)
    ↓ Telegraf 订阅
Telegraf (json_v2 解析)
    ↓ 展平 JSON，添加前缀
InfluxDB2 (bucket: opentwins)
    - measurement: mqtt_consumer
    - tags: thingId
    - fields: value_*_*_*
    ↓ Grafana 查询
Grafana Dashboard
```

## 完整示例 Dashboard JSON

如果需要，我可以提供一个完整的 Dashboard JSON 配置，包含：
- GPS 位置地图
- GPS 轨迹
- 车轮速度图表
- 车轮方向图表

只需导入到 Grafana 即可使用。

## 总结

**问题**: 字段名缺少 `value_` 前缀
**解决**: 将 `value_gps_properties_latitude` 改为 `value_gps_properties_value_latitude`

立即在 Grafana 中尝试修正后的查询，应该能看到数据了！
