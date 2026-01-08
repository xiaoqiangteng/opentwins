# 快速部署参考

## ⚠️ 重要修复说明

**已修复问题**：Post-install job 的 image 配置格式错误导致 job 无法创建。

**修复内容**：
- `templates/post-install-jobs/post-install-ditto-default.yaml` 第30-31行
- 将 `image: {repository:..., tag:..., pullPolicy:...}` 改为 `image: <image>:<tag>`

**影响**：之前的部署中 post-install job 不会运行，导致 policies 不会自动创建。

---

## 一键部署命令

```bash
helm upgrade --install opentwins ./ \
  --namespace opentwins \
  --create-namespace \
  -f values.yaml \
  --wait \
  --dependency-update \
  --debug
```

## 验证部署

### 1. 检查 Pods
```bash
kubectl get pods -n opentwins
```

### 2. 查看 Policy 创建日志
```bash
kubectl logs -n opentwins job/opentwins-post-install-ditto-default
```

期望输出：
```
SUCCESS: Ditto is UP and ready.
Adding default policy...
SUCCESS: Operation completed [status: 201, ...]
Adding opentwins policy...
SUCCESS: Operation completed [status: 201, ...]
```

### 3. 验证 Policies
```bash
# 替换为你的集群 IP
curl -s -u ditto:ditto http://192.168.49.2:30525/api/2/policies/opentwins:basic_policy | jq .
```

## 修改内容

### 新增
- `post-install/ditto-default/opentwins-policy.json` - opentwins:basic_policy 定义

### 修改
- `post-install/ditto-default/setup.sh` - 添加创建 opentwins:basic_policy
- `templates/secrets/ditto-default-secret.yaml` - 包含 opentwins-policy.json
- `values.yaml` - 移除无效的 bootstrap 配置

### 删除
- `templates/config-maps/cm-ditto-bootstrap-policies.yaml` - 不需要
- `policies.json` (根目录) - 不需要

## 故障排查

如果 policy 未创建成功，手动创建：

```bash
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

详细说明见 DEPLOYMENT_GUIDE.md
