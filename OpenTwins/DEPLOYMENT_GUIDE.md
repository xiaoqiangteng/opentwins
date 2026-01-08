# OpenTwins Helm 部署说明

## 快速部署

使用以下命令一键部署 OpenTwins，会自动创建 `default:basic_policy` 和 `opentwins:basic_policy` 两个 policies：

```bash
helm upgrade --install opentwins ./ \
  --namespace opentwins \
  --create-namespace \
  -f values.yaml \
  --wait \
  --dependency-update \
  --debug
```

## 配置说明

### Policy 自动创建机制

OpenTwins 使用 **Helm Post-Install Job** 自动创建 policies，而不是使用 Ditto 的 bootstrap 机制。

**原因**：
- Ditto Helm chart v3.3.7 的环境变量配置会被默认值覆盖
- Bootstrap 机制无法在当前 chart 版本中正常工作
- Post-install job 更可靠，支持重试和错误处理

### 已配置的 Policies

部署成功后，会自动创建以下 policies：

#### 1. default:basic_policy
- 用于默认的 Ditto 资源访问
- Subjects: `{{ request:subjectId }}`, `pre-authenticated:kafkaml-connection`, `pre-authenticated:hono-connection`
- Resources: `policy:/`, `thing:/`, `message:/` (READ, WRITE)

#### 2. opentwins:basic_policy
- 用于 OpenTwins 平台资源访问
- Subjects: `{{ request:subjectId }}`, `nginx:ditto`, `pre-authenticated:kafkaml-connection`, `pre-authenticated:hono-connection`
- Resources: `policy:/`, `thing:/`, `message:/` (READ, WRITE)

## 验证部署

### 1. 检查所有 Pods 状态

```bash
kubectl get pods -n opentwins
```

所有 pods 应该处于 `Running` 状态。

### 2. 检查 Post-Install Job 日志

```bash
kubectl logs -n opentwins job/opentwins-post-install-ditto-default
```

应该看到类似输出：
```
INFO: Waiting for Ditto to be UP...
SUCCESS: Ditto is UP and ready.
Adding default policy [URL: http://opentwins-ditto-nginx:8080/api/2/policies/default:basic_policy]
SUCCESS: Operation completed [status: 201, response: ...]
Adding opentwins policy [URL: http://opentwins-ditto-nginx:8080/api/2/policies/opentwins:basic_policy]
SUCCESS: Operation completed [status: 201, response: ...]
```

### 3. 验证 Policies 创建成功

通过 NodePort 访问（假设你的集群 IP 是 192.168.49.2）：

```bash
# 查看 opentwins:basic_policy
curl -s -u ditto:ditto \
  http://192.168.49.2:30525/api/2/policies/opentwins:basic_policy | jq .

# 查看 default:basic_policy
curl -s -u ditto:ditto \
  http://192.168.49.2:30525/api/2/policies/default:basic_policy | jq .
```

### 4. 访问 Ditto API

```bash
# Ditto Swagger UI (如果启用)
http://192.168.49.2:30525/

# Ditto REST API
curl -s -u ditto:ditto http://192.168.49.2:30525/api/2/things
```

## 修改内容总结

### 新增文件

1. **post-install/ditto-default/opentwins-policy.json**
   - 定义 `opentwins:basic_policy` 的完整配置
   - 包含 `nginx:ditto` subject 用于通过 nginx 认证的用户

### 修改文件

1. **post-install/ditto-default/setup.sh**
   - 添加创建 `opentwins:basic_policy` 的命令
   - 使用相同的错误处理和重试机制

2. **templates/secrets/ditto-default-secret.yaml**
   - 添加 `opentwins-policy.json` 到 Secret
   - Post-install job 会挂载这个 Secret

3. **values.yaml**
   - 移除无效的 bootstrap 配置（`policies.env`, `extraVolumes`, `extraVolumeMounts`）
   - 添加注释说明为什么使用 post-install job
   - 保持 `ditto.enabled: true` 和 `policies.enabled: true`

### 删除文件

1. **templates/config-maps/cm-ditto-bootstrap-policies.yaml** (已删除)
   - Bootstrap 方式不工作，不再需要

2. **policies.json** (根目录，已删除)
   - 迁移到 `post-install/ditto-default/opentwins-policy.json`

## 故障排查

### Post-Install Job 失败

如果 post-install job 失败：

```bash
# 查看详细日志
kubectl logs -n opentwins job/opentwins-post-install-ditto-default

# 删除失败的 job
kubectl delete job -n opentwins opentwins-post-install-ditto-default

# 手动创建 policy（临时方案）
kubectl exec -n opentwins deployment/opentwins-ditto-gateway -- \
  curl -s -X PUT -u ditto:ditto \
  -H 'Content-Type: application/json' \
  -d '{
    "policyId": "opentwins:basic_policy",
    "entries": {
      "DEFAULT": {
        "subjects": {
          "nginx:ditto": {"type": "Ditto user authenticated via nginx"}
        },
        "resources": {
          "policy:/": {"grant": ["READ", "WRITE"]},
          "thing:/": {"grant": ["READ", "WRITE"]},
          "message:/": {"grant": ["READ", "WRITE"]}
        }
      }
    }
  }' \
  http://opentwins-ditto-nginx:8080/api/2/policies/opentwins:basic_policy
```

### Ditto 健康检查超时

Post-install job 会等待最多 2.5 分钟（30次 × 5秒）让 Ditto 启动。

如果超时：
- 检查 MongoDB 是否正常运行
- 检查 Ditto pods 日志：`kubectl logs -n opentwins deployment/opentwins-ditto-gateway`
- 增加等待时间（修改 `post-install/ditto-connection/ditto-connection.sh` 中的 `max_retries`）

### Policy 已存在错误

Post-install job 会忽略 HTTP 409 (Conflict) 错误，所以重复部署不会失败。

## 卸载

```bash
helm uninstall opentwins -n opentwins
kubectl delete namespace opentwins
```

## 技术细节

### 为什么不使用 Bootstrap？

Ditto 支持通过 `-Dditto.bootstrap.policies.file=/path/to/policies.json` 在启动时加载 policies。

但在 OpenTwins Helm chart 中这种方式不工作，因为：

1. **环境变量被覆盖**：Ditto subchart 的默认 `JAVA_TOOL_OPTIONS` 会完全覆盖 `values.yaml` 中的自定义配置
2. **配置不支持 merge**：Ditto chart v3.3.7 的 `env` 参数不支持与默认配置合并
3. **Volume 挂载问题**：`extraVolumes` 和 `extraVolumeMounts` 在 policies service 中未生效

### Post-Install Job 的优势

1. ✅ **可靠性**：独立的 Job，失败可以重试
2. ✅ **可调试**：可以查看日志，了解失败原因
3. ✅ **幂等性**：使用 PUT 请求，重复执行不会出错
4. ✅ **灵活性**：可以创建多个 policies，执行复杂的初始化逻辑
5. ✅ **兼容性**：不依赖特定版本的 Ditto chart

## 相关文件

- Post-install job 定义: `templates/post-install-jobs/post-install-ditto-default.yaml`
- Policy JSON: `post-install/ditto-default/opentwins-policy.json`
- Setup 脚本: `post-install/ditto-default/setup.sh`
- 工具函数: `post-install/ditto-connection/ditto-connection.sh`
- Secret 模板: `templates/secrets/ditto-default-secret.yaml`
