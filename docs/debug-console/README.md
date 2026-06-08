# Debug Console 文档

## 用途

`worldmind-debug` 是 OpenTwins + WineFermentTwin Demo 的旁路调试工具链，包含：

- Debug API: `http://localhost:18080/api/debug`
- CLI: `worldmind-debug/cli/wmctl`
- 本地 trace SQLite: `worldmind-debug/data/debug_trace.sqlite`
- 日志: `worldmind-debug/logs/worldmind-debug-api.log`

## 推荐阅读顺序

1. [部署与运维命令](../opentwins-deployment/DEPLOYMENT_COMMANDS.md)
2. [Topic / Thing / Feature / Measurement 查找表](TOPICS_IDS_MEASUREMENTS.md)
3. [Debug API 全量接口参考](API_REFERENCE.md)
4. [wmctl 命令全量参考](WMCTL_REFERENCE.md)
5. [排障流程](TROUBLESHOOTING.md)

## 常用验证

```bash
curl http://localhost:18080/api/debug/health
worldmind-debug/cli/wmctl doctor
worldmind-debug/cli/wmctl mqtt tail --topic 'telemetry/#' --seconds 10
worldmind-debug/cli/wmctl twin echo wine:tank_01
worldmind-debug/cli/wmctl twin watch wine:tank_01 --feature ph --interval 2
```

## legacy 文档

`legacy/` 下保留了开发初期生成的文档副本，便于追溯；以后查询优先看本目录下的全量参考文档。
