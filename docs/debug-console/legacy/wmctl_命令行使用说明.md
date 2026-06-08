# wmctl 命令行使用说明

## 用途

`wmctl` 是 WorldMind Debug Console 的命令行入口，面向服务器端开发和部署维护，提供 OpenTwins 数据链路的快速观测能力。

## 安装

一键部署会安装 Debug API 依赖，并给 `wmctl.py` 添加可执行权限：

```bash
cd /home/teng/programmings/git/opentwins
./deploy_all.sh --demo-only
```

手动安装 CLI 依赖：

```bash
cd /home/teng/programmings/git/opentwins/worldmind-debug/cli
python3 -m pip install -r requirements.txt
```

## 配置

CLI 默认访问：

```text
http://localhost:18080/api/debug
```

如需修改：

```bash
export WM_DEBUG_API_URL=http://127.0.0.1:18080/api/debug
export WM_DEBUG_TIMEOUT=20
```

## 启动

先启动 Debug API：

```bash
cd /home/teng/programmings/git/opentwins
./deploy_all.sh --demo-only
```

再执行：

```bash
worldmind-debug/cli/wmctl doctor
```

## 常用命令

```bash
worldmind-debug/cli/wmctl doctor
worldmind-debug/cli/wmctl mqtt tail --topic 'telemetry/#' --seconds 10
worldmind-debug/cli/wmctl twin echo wine:tank_001
worldmind-debug/cli/wmctl twin watch wine:tank_001 --feature ph --interval 2
worldmind-debug/cli/wmctl conn list
worldmind-debug/cli/wmctl conn status mosquitto-source-connection
worldmind-debug/cli/wmctl conn metrics mosquitto-source-connection
worldmind-debug/cli/wmctl conn logs mosquitto-source-connection
worldmind-debug/cli/wmctl influx recent --measurement tank_001 --minutes 60
worldmind-debug/cli/wmctl trace trace_20260608_0001
worldmind-debug/cli/wmctl config show
```

写入一条本地 trace：

```bash
worldmind-debug/cli/wmctl trace-add trace_20260608_0001 --stage mqtt --status ok --message 'message received' --payload '{"topic":"telemetry/wine/tank_001"}'
```

## 常见错误

- `[ERROR] Connection refused`：Debug API 未启动，先执行 `curl http://localhost:18080/api/debug/health`。
- `[ERROR] Ditto HTTP 404`：thingId 或 connectionId 不存在，先执行 `wmctl conn list` 或检查 Wine 初始化脚本。
- `未收到 MQTT 消息`：Wine Simulator 可能未运行，执行 `./watch_demo.sh --simulator --snapshot`。
- `InfluxDB 查询为空`：可能是 measurement 名称不匹配，或 Telegraf 没有写入。

## 排障步骤

1. `wmctl doctor`
2. `wmctl mqtt tail --topic 'telemetry/#' --seconds 10`
3. `wmctl twin echo wine:tank_001`
4. `wmctl conn list`
5. `wmctl influx recent --measurement tank_001 --minutes 60`
6. `wmctl trace <trace_id>`

## Debug 示例

场景：前端没有显示 `wine:tank_001` 的 pH。

```bash
worldmind-debug/cli/wmctl doctor
worldmind-debug/cli/wmctl mqtt tail --topic 'telemetry/#' --seconds 10
worldmind-debug/cli/wmctl twin echo wine:tank_001
worldmind-debug/cli/wmctl twin watch wine:tank_001 --feature ph --interval 2
worldmind-debug/cli/wmctl influx recent --measurement tank_001 --minutes 60
```

示例输出：

```text
2026-06-08 10:30:01 ph=3.45
2026-06-08 10:30:03 ph=3.41
2026-06-08 10:30:05 ph=3.20  [WARN below threshold]
```
