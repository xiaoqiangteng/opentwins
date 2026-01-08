#!/bin/bash
set -e

echo "=========================================="
echo "OpenTwins 完全重新部署脚本"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. 完全卸载
echo -e "${YELLOW}步骤 1: 完全卸载旧环境...${NC}"
helm uninstall opentwins -n opentwins 2>/dev/null || echo "没有找到 opentwins release"
kubectl delete namespace opentwins --wait=true 2>/dev/null || echo "命名空间已删除或不存在"
sleep 5

# 2. 清理 Helm 缓存
echo -e "${YELLOW}步骤 2: 清理 Helm 缓存...${NC}"
rm -rf ~/.cache/helm/repository/*
helm repo update 2>/dev/null || true

# 3. 验证模板
echo -e "${YELLOW}步骤 3: 验证 Helm 模板...${NC}"
cd /home/teng/programmings/git/Helm_charts/OpenTwins
helm template opentwins ./ > /tmp/opentwins-rendered.yaml
if grep -q "image: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/curlimages-curl:7.73.0" /tmp/opentwins-rendered.yaml; then
    echo -e "${GREEN}✓ 模板验证通过 - image 配置正确${NC}"
else
    echo -e "${RED}✗ 模板验证失败 - image 配置仍然错误${NC}"
    exit 1
fi

# 4. 重新部署
echo -e "${YELLOW}步骤 4: 重新部署 OpenTwins...${NC}"
helm upgrade --install opentwins ./ \
  --namespace opentwins \
  --create-namespace \
  -f values.yaml \
  --wait \
  --timeout 15m \
  --dependency-update \
  --debug 2>&1 | tee /tmp/helm-install.log

# 5. 等待 pods 就绪
echo -e "${YELLOW}步骤 5: 等待所有 pods 就绪...${NC}"
kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=opentwins -n opentwins --timeout=300s || true

# 6. 检查 post-install job
echo -e "${YELLOW}步骤 6: 检查 post-install job...${NC}"
sleep 10
if kubectl get job -n opentwins opentwins-post-install-ditto-default 2>/dev/null; then
    echo -e "${GREEN}✓ Post-install job 已创建${NC}"
    
    # 等待 job 完成
    echo "等待 job 完成..."
    kubectl wait --for=condition=complete job/opentwins-post-install-ditto-default -n opentwins --timeout=180s || \
    kubectl wait --for=condition=failed job/opentwins-post-install-ditto-default -n opentwins --timeout=10s || true
    
    # 显示日志
    echo -e "${YELLOW}Job 日志:${NC}"
    kubectl logs -n opentwins job/opentwins-post-install-ditto-default || echo "无法获取日志"
else
    echo -e "${RED}✗ Post-install job 未创建！${NC}"
    echo "检查 helm hooks:"
    helm get hooks opentwins -n opentwins | grep -A30 "post-install-ditto-default"
    exit 1
fi

# 7. 验证 policies
echo -e "${YELLOW}步骤 7: 验证 policies 创建...${NC}"
sleep 5

# 尝试访问 policy
POLICY_CHECK=$(kubectl exec -n opentwins deployment/opentwins-ditto-gateway -- \
  curl -s -X GET -u ditto:ditto \
  http://opentwins-ditto-nginx:8080/api/2/policies/opentwins:basic_policy 2>/dev/null | grep -c '"policyId"' || echo "0")

if [ "$POLICY_CHECK" -gt 0 ]; then
    echo -e "${GREEN}✓ Policy 'opentwins:basic_policy' 创建成功！${NC}"
    kubectl exec -n opentwins deployment/opentwins-ditto-gateway -- \
      curl -s -u ditto:ditto \
      http://opentwins-ditto-nginx:8080/api/2/policies/opentwins:basic_policy | jq .
else
    echo -e "${RED}✗ Policy 'opentwins:basic_policy' 未创建${NC}"
    echo "尝试手动创建..."
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
              "policy:/": {"grant": ["READ", "WRITE"], "revoke": []},
              "thing:/": {"grant": ["READ", "WRITE"], "revoke": []},
              "message:/": {"grant": ["READ", "WRITE"], "revoke": []}
            }
          }
        }
      }' \
      http://opentwins-ditto-nginx:8080/api/2/policies/opentwins:basic_policy
    echo ""
    echo -e "${GREEN}✓ Policy 手动创建完成${NC}"
fi

echo ""
echo -e "${GREEN}=========================================="
echo "部署完成！"
echo "==========================================${NC}"
echo ""
echo "验证命令:"
echo "  kubectl get pods -n opentwins"
echo "  kubectl logs -n opentwins job/opentwins-post-install-ditto-default"
echo "  curl -s -u ditto:ditto http://192.168.49.2:30525/api/2/policies/opentwins:basic_policy | jq ."

