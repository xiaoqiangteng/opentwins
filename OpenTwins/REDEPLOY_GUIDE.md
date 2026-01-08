# 完全重新部署 OpenTwins

## 问题原因

你重新部署后 policy 没有创建，是因为：

1. **使用了缓存的旧 chart** - Helm 可能使用了旧版本的模板
2. **post-install job 的 image 配置错误** - 导致 job 根本无法创建
3. **hook-delete-policy: hook-succeeded** - 即使 job 成功了也会立即被删除，无法查看日志

## 已修复内容

### 1. 修复 image 配置（第30-31行）
```yaml
# 修改前（错误）
image:
  repository: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/curlimages-curl
  tag: "7.73.0"
  pullPolicy: IfNotPresent

# 修改后（正确）
image: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/curlimages-curl:7.73.0
imagePullPolicy: IfNotPresent
```

### 2. 修复 hook 配置（第17-20行）
```yaml
# 修改前
"helm.sh/hook-delete-policy": hook-succeeded
spec:

# 修改后
"helm.sh/hook-delete-policy": before-hook-creation
spec:
  backoffLimit: 3
  ttlSecondsAfterFinished: 600
```

**改进**：
- `before-hook-creation`: Job 会保留，方便查看日志，只在下次部署时删除
- `backoffLimit: 3`: 失败后最多重试 3 次
- `ttlSecondsAfterFinished: 600`: 完成 10 分钟后自动清理

## 使用自动化脚本重新部署

### 方法 1：使用自动化脚本（推荐）

```bash
bash /tmp/redeploy_steps.sh
```

这个脚本会自动：
1. ✓ 完全卸载旧环境
2. ✓ 清理 Helm 缓存
3. ✓ 验证模板正确性
4. ✓ 重新部署 OpenTwins
5. ✓ 等待并检查 post-install job
6. ✓ 验证 policy 创建
7. ✓ 如果失败自动手动创建

### 方法 2：手动步骤

如果你想手动操作：

```bash
# 1. 完全卸载
helm uninstall opentwins -n opentwins
kubectl delete namespace opentwins --wait=true
sleep 5

# 2. 清理缓存
rm -rf ~/.cache/helm/repository/*

# 3. 验证模板
cd /home/teng/programmings/git/Helm_charts/OpenTwins
helm template opentwins ./ | grep -A5 "post-install-ditto-default" | grep "image:"
# 应该看到：image: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/curlimages-curl:7.73.0

# 4. 重新部署
helm upgrade --install opentwins ./ \
  --namespace opentwins \
  --create-namespace \
  -f values.yaml \
  --wait \
  --timeout 15m \
  --dependency-update \
  --debug

# 5. 等待 10 秒后检查 job
sleep 10
kubectl get job -n opentwins
kubectl logs -n opentwins job/opentwins-post-install-ditto-default

# 6. 验证 policy
kubectl exec -n opentwins deployment/opentwins-ditto-gateway -- \
  curl -s -u ditto:ditto \
  http://opentwins-ditto-nginx:8080/api/2/policies/opentwins:basic_policy | jq .
```

## 预期结果

### 成功的 Job 日志应该是：
```
INFO: Waiting for Ditto to be UP...
SUCCESS: Ditto is UP and ready.
Adding default policy [URL: http://opentwins-ditto-nginx:8080/api/2/policies/default:basic_policy]
SUCCESS: Operation completed [status: 201, response: ...]
Adding opentwins policy [URL: http://opentwins-ditto-nginx:8080/api/2/policies/opentwins:basic_policy]
SUCCESS: Operation completed [status: 201, response: ...]
```

### Policy 验证应该返回：
```json
{
  "policyId": "opentwins:basic_policy",
  "entries": {
    "DEFAULT": {
      "subjects": {
        "nginx:ditto": {
          "type": "Ditto user authenticated via nginx"
        }
      },
      "resources": {
        "policy:/": {"grant": ["READ", "WRITE"], "revoke": []},
        "thing:/": {"grant": ["READ", "WRITE"], "revoke": []},
        "message:/": {"grant": ["READ", "WRITE"], "revoke": []}
      }
    }
  }
}
```

## 故障排查

### 如果 Job 仍然失败

1. 查看 Job 状态：
```bash
kubectl describe job -n opentwins opentwins-post-install-ditto-default
```

2. 查看 Pod 日志（如果 Job 创建了 Pod）：
```bash
kubectl get pods -n opentwins -l job-name=opentwins-post-install-ditto-default
kubectl logs -n opentwins <pod-name>
```

3. 检查 Secret 是否正确创建：
```bash
kubectl get secret -n opentwins opentwins-ditto-default-data -o yaml
```

### 如果 Job 根本没创建

检查 Helm hooks 配置：
```bash
helm get hooks opentwins -n opentwins | grep -A40 "post-install-ditto-default"
```

确保 image 配置是正确格式。

## 关键修改文件

- `templates/post-install-jobs/post-install-ditto-default.yaml` - 修复 image 和 hook 配置
- `post-install/ditto-default/opentwins-policy.json` - Policy JSON（已正确）
- `post-install/ditto-default/setup.sh` - 创建 policy 的脚本（已正确）
- `templates/secrets/ditto-default-secret.yaml` - 包含 policy JSON 的 Secret（已正确）

## 现在就运行

```bash
bash /tmp/redeploy_steps.sh
```

或者如果你想手动一步步操作，按照上面的"手动步骤"执行。
