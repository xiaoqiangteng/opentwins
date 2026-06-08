# WineFermentTwin Demo 文档

## 用途

本目录集中整理 WineFermentTwin Demo 的业务 API、仿真服务、数据模型、MQTT 链路和旧文档归档。

## 快速入口

- [Wine Demo API 全量接口参考](API_REFERENCE.md)
- [MQTT 与 Twin 数据模型](MQTT_AND_TWIN_MODEL.md)
- [旧文档归档](legacy/)

## 当前服务端口

```text
WineTwin Service: http://localhost:8010
Wine Frontend:   http://localhost:5173
Modelica API:    http://localhost:8020
```

## 常用命令

```bash
cd /home/teng/programmings/git/opentwins
./deploy_all.sh --demo-only
./watch_demo.sh --status
./watch_demo.sh --service --snapshot
./watch_demo.sh --simulator --snapshot
```
