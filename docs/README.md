# OpenTwins + WineFermentTwin 文档索引

## 目录结构

```text
docs/
  debug-console/          WorldMind Debug Console / wmctl 文档
  wine-demo/              WineFermentTwin Demo 文档
  opentwins-deployment/   OpenTwins 部署、脚本、端口与排障文档
```

## 快速入口

- [Debug Console 总览](debug-console/README.md)
- [Debug API 全量接口参考](debug-console/API_REFERENCE.md)
- [wmctl 命令全量参考](debug-console/WMCTL_REFERENCE.md)
- [Topic / Thing / Feature / Measurement 查找表](debug-console/TOPICS_IDS_MEASUREMENTS.md)
- [Wine Demo API 全量接口参考](wine-demo/API_REFERENCE.md)
- [Wine Demo 数据模型与 MQTT 链路](wine-demo/MQTT_AND_TWIN_MODEL.md)
- [部署与运维命令](opentwins-deployment/DEPLOYMENT_COMMANDS.md)

## 当前部署识别

当前工程位于：

```bash
/home/teng/programmings/git/opentwins
```

当前主要入口：

```bash
./deploy_all.sh
./stop_all.sh
./watch_demo.sh --status
worldmind-debug/cli/wmctl doctor
```

## 文档维护规则

- 新增 Debug API 时，同步更新 `docs/debug-console/API_REFERENCE.md`。
- 新增 `wmctl` 命令时，同步更新 `docs/debug-console/WMCTL_REFERENCE.md`。
- 新增 MQTT topic、Ditto thing、feature、Influx measurement 时，同步更新 `docs/debug-console/TOPICS_IDS_MEASUREMENTS.md`。
- Wine Demo API 变化时，同步更新 `docs/wine-demo/API_REFERENCE.md`。
- 脚本参数或端口变化时，同步更新 `docs/opentwins-deployment/DEPLOYMENT_COMMANDS.md`。
