#!/bin/bash

# OpenTwins 部署验证脚本

set -e

NAMESPACE="opentwins"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "OpenTwins 部署验证"
echo "=========================================="
echo ""

# 1. 检查所有 Pod 状态
echo -e "${YELLOW}1. 检查 Pod 状态${NC}"
kubectl get pods -n $NAMESPACE
echo ""

# 2. 检查是否有失败的 Pod
FAILED_PODS=$(kubectl get pods -n $NAMESPACE --field-selector=status.phase!=Running,status.phase!=Succeeded -o name 2>/dev/null | wc -l)
if [ "$FAILED_PODS" -gt 0 ]; then
    echo -e "${RED}❌ 有 $FAILED_PODS 个 Pod 未正常运行${NC}"
    kubectl get pods -n $NAMESPACE --field-selector=status.phase!=Running,status.phase!=Succeeded
    echo ""
else
    echo -e "${GREEN}✅ 所有 Pod 正常运行${NC}"
    echo ""
fi

# 3. 检查服务
echo -e "${YELLOW}2. 检查服务${NC}"
kubectl get svc -n $NAMESPACE
echo ""

# 4. 获取 NodePort 访问地址
MINIKUBE_IP=$(minikube ip 2>/dev/null || echo "192.168.49.2")
echo -e "${YELLOW}3. 服务访问地址${NC}"
echo "Minikube IP: $MINIKUBE_IP"
echo ""
echo "- Grafana:       http://$MINIKUBE_IP:30718 (admin / Test123456!)"
echo "- Ditto API:     http://$MINIKUBE_IP:30525 (ditto / ditto)"
echo "- Extended API:  http://$MINIKUBE_IP:30526"
echo "- Mosquitto:     $MINIKUBE_IP:30511"
echo "- MongoDB:       $MINIKUBE_IP:30717"
echo ""

# 5. 检查 Grafana 数据源
echo -e "${YELLOW}4. 检查 Grafana 数据源配置${NC}"
kubectl get cm -n $NAMESPACE opentwins-influxdb2-grafana-datasource -o yaml 2>/dev/null | grep "defaultBucket:" || echo "未找到数据源配置"
echo ""

# 6. 检查 Telegraf 配置
echo -e "${YELLOW}5. 检查 Telegraf 输出配置${NC}"
kubectl exec -n $NAMESPACE deployment/opentwins-telegraf -- cat /additional_config/telegraf.conf 2>/dev/null | grep "bucket =" || echo "无法读取 Telegraf 配置"
echo ""

# 7. 检查 InfluxDB buckets
echo -e "${YELLOW}6. 检查 InfluxDB Buckets${NC}"
kubectl exec -n $NAMESPACE statefulset/opentwins-influxdb2 -- \
  influx bucket list \
  --host http://localhost:8086 \
  --org opentwins \
  --token "Hjh3ysMQ6evK=qqpFSYqn-s3JGovJLfHxyCDM=eNNZkdM-uuro93dNtJcodejLYYob2geKQ/29z3Kxui=y6FlL?dZeU9EFRxrYn284V/kZG5==jxLVAMJrYOv?LF79ahwIbhvstMN6gmfQ3DH7/IzUB7VlBZK-cd8aN7YqiFrYRLkBUv7H0QkbqPxgf2dMgCMCwZaLMk9RUeMaBfx2lQ=Mq1EEJJw-Jp!BmpCDnhlc!6D22PaE=Y3sgWWNhRv8oP" 2>/dev/null | grep -E "Name|opentwins" || echo "无法连接 InfluxDB"
echo ""

# 8. 检查 Ditto policies
echo -e "${YELLOW}7. 检查 Ditto Policies${NC}"
kubectl exec -n $NAMESPACE deployment/opentwins-ditto-gateway -- \
  curl -s -u ditto:ditto http://opentwins-ditto-nginx:8080/api/2/policies 2>/dev/null | \
  grep -o '"policyId":"[^"]*"' || echo "无法连接 Ditto API"
echo ""

# 9. 总结
echo "=========================================="
echo -e "${GREEN}验证完成${NC}"
echo "=========================================="
echo ""
echo "数据流程："
echo "  MQTT Publisher"
echo "       ↓"
echo "  Mosquitto (opentwins/#)"
echo "       ↓"
echo "  Telegraf (mqtt_consumer)"
echo "       ↓"
echo "  InfluxDB2 (bucket: opentwins)"
echo "       ↓"
echo "  Grafana (datasource: opentwins)"
echo ""
echo "下一步："
echo "1. 打开 Grafana: http://$MINIKUBE_IP:30718"
echo "2. 使用 get_data_simulate.py 发送测试数据"
echo "3. 在 Grafana Explore 中查询数据"
echo ""
