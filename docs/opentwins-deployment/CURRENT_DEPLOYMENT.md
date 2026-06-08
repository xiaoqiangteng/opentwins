# 当前部署识别结果

## 路径

```text
项目根目录: /home/teng/programmings/git/opentwins
OpenTwins Helm Chart: /home/teng/programmings/git/opentwins/OpenTwins
WineFermentTwin Demo: /home/teng/programmings/git/opentwins/wine-ferment-twin
Debug 工具链: /home/teng/programmings/git/opentwins/worldmind-debug
```

## 部署方式

```text
OpenTwins: minikube + Helm
release: opentwins
namespace: opentwins
WineTwin Service: 宿主机 uvicorn
Wine Frontend: 宿主机 Vite/React
Modelica Service: Docker container
Debug API: 宿主机 uvicorn
```

## 端口

| 服务 | 地址 |
| --- | --- |
| Ditto API | `http://<OPENTWINS_HOST_IP>:30525` |
| Extended API | `http://<OPENTWINS_HOST_IP>:30526` |
| Mosquitto MQTT | `<OPENTWINS_HOST_IP>:30511` |
| InfluxDB | `http://<OPENTWINS_HOST_IP>:30716` |
| Grafana | `http://<OPENTWINS_HOST_IP>:30718` |
| WineTwin Service | `http://<HOST_IP>:8010` |
| Wine Frontend | `http://<HOST_IP>:5173` |
| Modelica API | `http://<HOST_IP>:8020` |
| Debug API | `http://<HOST_IP>:18080` |

## 当前注意事项

`docs/debug-console/TOPICS_IDS_MEASUREMENTS.md` 中的 topic、thingId、feature、measurement 是以后排查链路时优先查阅的索引。
