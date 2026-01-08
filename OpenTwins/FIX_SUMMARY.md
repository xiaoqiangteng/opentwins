# 修复总结

## 问题分析

### 问题 1：Post-Install Job 没有创建
**原因**：Job 模板中的 image 配置格式错误

错误的配置（Helm chart 风格）：
```yaml
image:
  repository: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/curlimages-curl
  tag: "7.73.0"
  pullPolicy: IfNotPresent
```

这是 Helm chart values 的风格，但在 Kubernetes Pod 规范中是**无效的**。

正确的配置（Kubernetes Pod 规范）：
```yaml
image: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/curlimages-curl:7.73.0
imagePullPolicy: IfNotPresent
```

**后果**：
- Post-install job 无法创建或启动失败
- Policies 不会自动创建
- 用户需要手动创建 policies

### 问题 2：手动创建 Policy 时的 JSON 错误
**错误信息**：`JSON did not include required </revoke> field!`

**原因**：Ditto API 要求每个 resource 必须同时包含 `grant` 和 `revoke` 字段

错误的 JSON：
```json
"resources": {
  "policy:/": {
    "grant": ["READ", "WRITE"]
  }
}
```

正确的 JSON：
```json
"resources": {
  "policy:/": {
    "grant": ["READ", "WRITE"],
    "revoke": []
  }
}
```

## 修复内容

### 1. 修复 Post-Install Job 模板
**文件**：`templates/post-install-jobs/post-install-ditto-default.yaml`
**行号**：30-31

**修改前**：
```yaml
image:
  repository: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/curlimages-curl
  tag: "7.73.0"
  pullPolicy: IfNotPresent
```

**修改后**：
```yaml
image: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/curlimages-curl:7.73.0
imagePullPolicy: IfNotPresent
```

### 2. Policy JSON 已经正确
**文件**：`post-install/ditto-default/opentwins-policy.json`

所有 resources 都包含 `revoke: []` 字段，格式正确。

## 验证

### 当前环境
已手动创建 policy，可以验证：
```bash
curl -s -u ditto:ditto http://192.168.49.2:30525/api/2/policies/opentwins:basic_policy | jq .
```

### 重新部署测试
删除当前部署并重新安装，验证 post-install job 是否正常工作：

```bash
# 1. 卸载
helm uninstall opentwins -n opentwins
kubectl delete namespace opentwins

# 2. 重新部署
helm upgrade --install opentwins ./ \
  --namespace opentwins \
  --create-namespace \
  -f values.yaml \
  --wait \
  --dependency-update \
  --debug

# 3. 等待部署完成后，检查 job 日志
kubectl logs -n opentwins job/opentwins-post-install-ditto-default

# 应该看到：
# SUCCESS: Ditto is UP and ready.
# Adding default policy...
# SUCCESS: Operation completed [status: 201, ...]
# Adding opentwins policy...
# SUCCESS: Operation completed [status: 201, ...]

# 4. 验证 policy
curl -s -u ditto:ditto http://192.168.49.2:30525/api/2/policies/opentwins:basic_policy | jq .
```

## 教训

1. **Helm Chart Values vs Kubernetes Spec**
   - Helm chart 的 `values.yaml` 可以用嵌套的 `image.repository` 和 `image.tag`
   - 但在 Kubernetes Pod spec 中，`image` 必须是字符串，格式为 `<registry>/<image>:<tag>`

2. **Post-Install Hooks 调试**
   - Post-install hooks 失败不会阻止部署标记为"成功"
   - 需要明确检查 job 日志：`kubectl logs -n <namespace> job/<job-name>`
   - 使用 `helm.sh/hook-delete-policy: before-hook-creation` 而不是 `hook-succeeded`，这样可以保留失败的 job 用于调试

3. **Ditto API 严格性**
   - Ditto REST API 对 JSON 格式要求严格
   - 每个 resource 必须同时有 `grant` 和 `revoke`（即使 revoke 是空数组）
   - 建议始终包含所有必需字段，即使为空

## 最终状态

✅ Post-install job 模板已修复
✅ Policy JSON 格式正确
✅ 当前环境的 policy 已手动创建
✅ 下次重新部署时，policies 会自动创建

## 相关文件

- 修复的模板：`templates/post-install-jobs/post-install-ditto-default.yaml`
- Policy JSON：`post-install/ditto-default/opentwins-policy.json`
- 部署指南：`DEPLOYMENT_GUIDE.md`
- 快速参考：`QUICK_START.md`
