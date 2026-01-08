# 阿里云镜像仓库配置修复

## 问题背景

在中国网络环境下，从 docker.io、quay.io、rancher 等国外镜像仓库拉取镜像经常失败或速度很慢。因此需要将所有镜像配置为使用阿里云镜像仓库。

## 修复的镜像配置

### 1. Eclipse Ditto 组件

所有 Ditto 组件镜像已配置为从阿里云拉取：

```yaml
ditto:
  # Nginx 网关
  nginx:
    image:
      repository: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/nginx
      tag: "1.24"
    initContainers:
      waitForGateway:
        image: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/curlimages-curl:7.73.0

  # Gateway 服务
  gateway:
    image:
      repository: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/ditto-gateway
      tag: 3.3.7

  # Connectivity 服务
  connectivity:
    image:
      repository: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/ditto-connectivity
      tag: 3.3.7

  # Things 服务
  things:
    image:
      repository: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/ditto-things
      tag: 3.3.7

  # Things Search 服务
  thingsSearch:
    image:
      repository: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/ditto-things-search
      tag: 3.3.7

  # Policies 服务
  policies:
    image:
      repository: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/ditto-policies
      tag: 3.3.7

  # Fixer 工具镜像
  fixerImage:
    repository: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/alpine
    tag: latest
```

### 2. Grafana

**关键点**：Grafana chart 使用 `registry/repository:tag` 格式，需要分别设置 `registry` 和 `repository`。

```yaml
grafana:
  image:
    registry: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com
    repository: opentwins/grafana
    tag: "10.2.2"

  sidecar:
    image:
      registry: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com
      repository: opentwins/k8s-sidecar
      tag: 1.30.10

  extraInitContainers:
  - name: install-opentwins-plugins
    image: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/busybox:1.31.1
```

### 3. Telegraf

**关键点**：Telegraf chart 使用 `repo` 而非 `repository`。

```yaml
telegraf:
  image:
    repo: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/telegraf
    tag: "1.36-alpine"
```

### 4. InfluxDB2

```yaml
influxdb2:
  image:
    repository: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/influxdb
    tag: "2.7.4-alpine"
```

### 5. MongoDB

```yaml
mongodb:
  image:
    repository: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/mongodb
    tag: 6.0.10-debian-11-r8
  volumePermissions:
    image:
      registry: docker.io
      repository: bitnamilegacy/os-shell
      tag: 11-debian-11-r72
```

### 6. Mosquitto

```yaml
mosquitto:
  image:
    repository: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/eclipse-mosquitto
    tag: "2.0.14"
```

### 7. Extended API

```yaml
extendedAPI:
  image:
    repository: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/ditto-extended-api
    tag: latest
```

## 常见错误和解决方案

### 错误 1: InvalidImageName - 镜像名称格式错误

**症状**：
```
Failed to apply default image tag "/crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/...": invalid reference format
```

**原因**：将 `registry` 设置为空字符串 `""`，导致渲染后的镜像名称变成 `/repository:tag`（前导斜杠）。

**解决方案**：
- 对于 Grafana：正确分离 `registry` 和 `repository`
- 对于其他组件：不要设置空的 `registry` 字段，直接在 `repository` 中包含完整路径

### 错误 2: ImagePullBackOff - 从 docker.io 拉取失败

**症状**：
```
Failed to pull image "docker.io/eclipse/ditto-connectivity:3.3.7"
```

**原因**：子 chart 的镜像配置未覆盖，使用了默认的 docker.io 仓库。

**解决方案**：在父 chart 的 `values.yaml` 中显式覆盖子 chart 的镜像配置。

### 错误 3: PVC 冲突

**症状**：
```
conflict occurred while applying object opentwins/opentwins-ditto-fixer-pvc
```

**原因**：PVC 的 `.spec.resources.requests.storage` 字段不可变，升级时发生冲突。

**解决方案**：
```bash
# 删除冲突的 PVC（会自动重建）
kubectl delete pvc -n opentwins opentwins-ditto-fixer-pvc

# 如果 PVC 处于 Terminating 状态，先删除使用它的 Pod
kubectl delete pod -n opentwins <pod-name>
```

## 验证步骤

### 1. 检查所有镜像配置

```bash
helm template opentwins ./ --namespace opentwins -f values.yaml 2>&1 | \
  grep -E "^\s+image:" | \
  grep -v "crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com" | \
  grep -v "background-image"
```

应该只看到少量测试容器镜像（如 bats/bats），没有 docker.io、quay.io、rancher 的生产镜像。

### 2. 检查 Pod 状态

```bash
kubectl get pods -n opentwins
```

所有 Pod 应该处于 Running 状态。

### 3. 检查 Grafana 容器

```bash
kubectl describe pod -n opentwins -l app.kubernetes.io/name=grafana
```

确认所有容器（grafana、grafana-sc-datasources、grafana-sc-plugins）都成功启动。

## 部署命令

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

## 关键配置文件

- `values.yaml` - 主配置文件，包含所有镜像覆盖
- `Chart.yaml` - Chart 元数据和依赖
- `charts/*.tgz` - 子 chart 压缩包

## 配置原则

1. **分离 registry 和 repository**：某些 chart（如 Grafana）需要分别设置
2. **使用正确的字段名**：注意 `repo` vs `repository` 的区别
3. **覆盖子 chart 配置**：在父 chart 中显式设置子 chart 的镜像
4. **避免空字符串**：不要将 `registry` 设为 `""`，要么删除该字段，要么设置正确的值

## 最终结果

✅ 所有主要服务组件都使用阿里云镜像仓库
✅ 部署成功，无镜像拉取失败
✅ Grafana 及其 sidecar 容器正常运行
✅ 所有 13 个 Pod 处于 Running 状态
✅ 配置已固化在 values.yaml 中，下次部署自动生效
