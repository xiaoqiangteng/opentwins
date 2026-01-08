# OpenTwins 部署完成总结

## ✅ 成功部署状态

**部署时间**: 2026-01-08
**Helm Release**: opentwins (revision 9)
**命名空间**: opentwins
**所有 Pod**: 13/13 运行中

## 已解决的问题

### 1. Eclipse Ditto Policy 自动创建
- **问题**: Bootstrap 方式无法创建 `opentwins:basic_policy`
- **解决**: 使用 post-install Job 通过 REST API 创建
- **文件**:
  - `templates/post-install-jobs/post-install-ditto-default.yaml`
  - `post-install/ditto-default/opentwins-policy.json`

### 2. 阿里云镜像仓库配置
- **问题**: 容器从 docker.io、quay.io、rancher 拉取镜像失败
- **解决**: 所有镜像配置为阿里云仓库
- **关键配置**:
  - Grafana: 分离 `registry` 和 `repository`
  - Telegraf: 使用 `repo` 字段
  - Ditto: 完整路径在 `repository` 中
- **文件**: `ALIYUN_REGISTRY_FIX.md`

### 3. Grafana 数据接收问题
- **问题**: Telegraf 写入 `default` bucket，Grafana 查询 `opentwins` bucket
- **解决**: 统一使用 `opentwins` bucket
- **修改**: `values.yaml` 第 274 行
- **文件**: `GRAFANA_FIX.md`

### 4. PVC 冲突
- **问题**: `opentwins-ditto-fixer-pvc` 升级时冲突
- **解决**: 删除旧 PVC 和相关 Pod，允许重建

### 5. 示例应用禁用
- **问题**: 不需要 Raspberry Pi 示例
- **解决**: 设置 `example.enabled: false`

## 部署配置

### 服务访问地址
- **InfluxDB2**: http://192.168.49.2:30716 (admin / Test123456!)
- **Grafana**: http://192.168.49.2:30718 (admin / Test123456!)
- **Ditto API**: http://192.168.49.2:30525 (ditto / ditto)
- **Extended API**: http://192.168.49.2:30526
- **Mosquitto**: 192.168.49.2:30511
- **MongoDB**: 192.168.49.2:30717

### 数据流程
```
MQTT Publisher (get_data_simulate.py)
    ↓
Mosquitto (topic: opentwins/#)
    ↓
Telegraf (mqtt_consumer plugin)
    ↓
InfluxDB2 (bucket: opentwins, org: opentwins)
    ↓
Grafana (datasource: opentwins)
```

### InfluxDB 配置
- **Organization**: opentwins
- **Bucket**: opentwins
- **Username**: admin
- **Password**: Test123456!
- **Web UI**: http://192.168.49.2:30716
- **Token**: Hjh3ysMQ6evK=qqpFSYqn-s3JGovJLfHxyCDM=eNNZkdM-uuro93dNtJcodejLYYob2geKQ/29z3Kxui=y6FlL?dZeU9EFRxrYn284V/kZG5==jxLVAMJrYOv?LF79ahwIbhvstMN6gmfQ3DH7/IzUB7VlBZK-cd8aN7YqiFrYRLkBUv7H0QkbqPxgf2dMgCMCwZaLMk9RUeMaBfx2lQ=Mq1EEJJw-Jp!BmpCDnhlc!6D22PaE=Y3sgWWNhRv8oP

## 重要文件

### 文档
- **CLAUDE.md** - Claude Code 工作指南
- **DEPLOYMENT_GUIDE.md** - 完整部署指南
- **QUICK_START.md** - 快速启动指南
- **GRAFANA_FIX.md** - Grafana 配置修复说明
- **ALIYUN_REGISTRY_FIX.md** - 阿里云镜像配置说明
- **README.md** - 项目概述（原有）

### 配置文件
- **values.yaml** - 主配置文件（已包含所有修复）
- **Chart.yaml** - Chart 元数据
- **post-install/ditto-default/** - Ditto 初始化配置

### 脚本
- **verify_deployment.sh** - 部署验证脚本（新增）
- **verify_grafana_fix.sh** - Grafana 验证脚本（之前创建）

## 部署命令

### 完整部署
```bash
cd /home/teng/programmings/git/Helm_charts/OpenTwins

helm upgrade --install opentwins ./ \
  --namespace opentwins \
  --create-namespace \
  -f values.yaml \
  --wait \
  --timeout=10m \
  --dependency-update
```

### 验证部署
```bash
./verify_deployment.sh
```

### 卸载
```bash
helm uninstall opentwins -n opentwins
kubectl delete namespace opentwins
```

## 关键配置项

### values.yaml 重要修改

1. **Line 13**: `example.enabled: false` - 禁用示例
2. **Line 91**: `cleanupStaleConnections: true` - 清理僵尸连接
3. **Lines 269-271**: InfluxDB2 NodePort 配置
4. **Line 274**: `bucket: "opentwins"` - 统一 bucket 名称
5. **Lines 119-205**: Ditto 组件镜像配置
6. **Lines 283-312**: Grafana 镜像配置
7. **Lines 234-239**: Telegraf 镜像配置

## 数据测试

### 发送测试数据
使用你的 `get_data_simulate.py` 脚本：
```bash
python get_data_simulate.py
```

### 在 Grafana 查询
1. 打开 http://192.168.49.2:30718
2. 进入 Explore 页面
3. 选择 "opentwins" 数据源
4. 使用 Flux 查询：
```flux
from(bucket: "opentwins")
  |> range(start: -5m)
  |> filter(fn: (r) => r["_measurement"] == "mqtt_consumer")
```

## 下次部署

所有配置已固化在 `values.yaml` 中，下次重新部署只需：

```bash
# 清理旧部署（如果需要）
helm uninstall opentwins -n opentwins
kubectl delete namespace opentwins

# 重新部署
cd /home/teng/programmings/git/Helm_charts/OpenTwins
helm upgrade --install opentwins ./ \
  --namespace opentwins \
  --create-namespace \
  -f values.yaml \
  --wait \
  --timeout=10m \
  --dependency-update

# 验证
./verify_deployment.sh
```

## 故障排查

### Pod 启动失败
```bash
kubectl get pods -n opentwins
kubectl describe pod <pod-name> -n opentwins
kubectl logs <pod-name> -n opentwins
```

### 镜像拉取失败
检查镜像配置：
```bash
helm template opentwins ./ -f values.yaml | grep "image:" | grep -v "crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com"
```

### Grafana 无数据
1. 检查 Telegraf 日志：`kubectl logs -n opentwins deployment/opentwins-telegraf`
2. 检查 InfluxDB 数据：见 `GRAFANA_FIX.md`
3. 验证 bucket 配置一致性

### PVC 冲突
```bash
kubectl delete pvc <pvc-name> -n opentwins
kubectl delete pod <pod-name> -n opentwins  # 如果 PVC 卡在 Terminating
```

## 维护建议

1. **定期备份**:
   - InfluxDB 数据
   - MongoDB 数据
   - Grafana 配置

2. **监控**:
   - Pod 状态
   - 磁盘使用
   - 网络连通性

3. **升级**:
   - 更新依赖：`helm dependency update`
   - 测试新版本后再升级生产环境

## 完成清单

- ✅ 所有 Pod 运行正常
- ✅ Ditto Policy 自动创建
- ✅ 镜像全部从阿里云拉取
- ✅ Grafana 接收并显示数据
- ✅ MQTT → InfluxDB 数据流正常
- ✅ 文档完整齐全
- ✅ 验证脚本可用
- ✅ values.yaml 配置固化

---

**部署完成时间**: 2026-01-08 11:58:42
**部署者**: Claude Code
**状态**: ✅ 生产就绪
