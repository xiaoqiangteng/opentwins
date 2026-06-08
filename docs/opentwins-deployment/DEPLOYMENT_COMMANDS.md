# 部署与运维命令

## 一键部署

完整部署：

```bash
cd /home/teng/programmings/git/opentwins
./deploy_all.sh
```

仅 OpenTwins 基础设施：

```bash
./deploy_all.sh --infra-only
```

仅 Wine Demo + Debug 工具：

```bash
./deploy_all.sh --demo-only
```

跳过 OpenModelica：

```bash
./deploy_all.sh --skip-modelica
```

跳过 Debug 工具：

```bash
./deploy_all.sh --skip-debug
```

指定 IP：

```bash
./deploy_all.sh --host-ip 192.168.x.x --opentwins-ip 192.168.49.2
```

## 一键停止

停止 Wine Demo 和 Debug API：

```bash
./stop_all.sh
```

停止 Demo、Debug API 并卸载 OpenTwins：

```bash
./stop_all.sh --infra
```

停止 Demo、Debug API、卸载 OpenTwins 并停止 minikube：

```bash
./stop_all.sh --infra-full
```

## 日志与状态

状态总览：

```bash
./watch_demo.sh --status
```

所有日志快照：

```bash
./watch_demo.sh --snapshot --lines 80
```

单模块日志：

```bash
./watch_demo.sh --simulator --snapshot --lines 80
./watch_demo.sh --service --snapshot --lines 80
./watch_demo.sh --frontend --snapshot --lines 80
./watch_demo.sh --modelica --snapshot --lines 80
./watch_demo.sh --debug --snapshot --lines 80
```

实时跟踪 Debug API：

```bash
./watch_demo.sh --debug
```

## Debug 验证

```bash
curl http://localhost:18080/api/debug/health
worldmind-debug/cli/wmctl doctor
worldmind-debug/cli/wmctl mqtt tail --topic 'telemetry/wine/#' --seconds 10
worldmind-debug/cli/wmctl twin echo wine:tank_01
```

## Wine Demo 验证

```bash
curl http://localhost:8010/health
curl http://localhost:8010/api/wine/overview
curl http://localhost:8020/health
curl http://localhost:5173
```

## OpenTwins 验证

```bash
curl -u ditto:ditto http://<OPENTWINS_HOST_IP>:30525/api/2/things
timeout 4 bash -c '</dev/tcp/<OPENTWINS_HOST_IP>/30511'
curl http://<OPENTWINS_HOST_IP>:30716/health
curl http://<OPENTWINS_HOST_IP>:30718/api/health
```

## 常见错误

| 错误 | 处理 |
| --- | --- |
| `python3 -m venv` 失败 | 脚本会 fallback 到 `pip --user`；如需 venv 安装 `python3.8-venv` |
| Debug API 不可达 | 查看 `worldmind-debug/logs/worldmind-debug-api.log` |
| `telemetry/#` 无消息 | 检查 Wine Simulator 是否运行 |
| Ditto NodePort 不通 | 检查 minikube、Helm release、`OPENTWINS_HOST_IP` |
| Grafana datasource 查不了 | 配置 `GRAFANA_API_TOKEN` |
| `ertis-opentwins-app.zip` / `ertis-unity-panel.zip` 缺失 | 新版 `deploy_all.sh` 会自动下载到 `/tmp` 并复制进 minikube；如果服务器 GitHub DNS 解析异常，可手动执行脚本提示的 `curl --resolve github.com:443:140.82.114.3 ...` 后重新部署 |
