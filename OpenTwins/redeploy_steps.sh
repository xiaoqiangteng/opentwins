#!/usr/bin/env bash
set -eo pipefail

CHART_DIR="/home/teng/programmings/git/opentwins/OpenTwins"
RELEASE="opentwins"
NAMESPACE="opentwins"
ALIYUN_REGISTRY="crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com"

# 绕过代理 — kubectl/helm 访问集群内 IP 不能走代理
export no_proxy="192.168.49.2,localhost,127.0.0.1,10.96.0.0/12,10.244.0.0/16,.svc,.cluster.local,minikube"
export NO_PROXY="$no_proxy"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ok()   { printf "${GREEN}✓ %s${NC}\n" "$*"; }
err()  { printf "${RED}✗ %s${NC}\n" "$*"; }
info() { printf "${BLUE}→ %s${NC}\n" "$*"; }
step() { printf "\n${YELLOW}══ %s ══${NC}\n" "$*"; }

# ── 动态提取镜像列表 ──────────────────────────────────────────────────────────
# 从 helm template 渲染结果中提取所有 image 引用，去重
# 过滤掉 CSS background-image 和测试用镜像 (bats/bats, bare busybox)
extract_images() {
    helm template "$RELEASE" "$CHART_DIR" --namespace "$NAMESPACE" -f "$CHART_DIR/values.yaml" 2>/dev/null \
      | grep 'image:' \
      | grep -v 'background-image' \
      | sed 's/.*image: *//' \
      | tr -d '"' \
      | sed 's/^docker\.io\///' \
      | grep -v '^bats/bats' \
      | grep -v '^busybox$' \
      | sort -u
}

# ── 镜像预加载 ───────────────────────────────────────────────────────────────
# 利用宿主机 Docker 作为持久缓存:
#   1. minikube 内已有 → 跳过
#   2. 宿主机 Docker 已有 → minikube image load (本地拷贝)
#   3. 都没有 → docker pull 到宿主机 (写入缓存) → minikube image load
preload_images() {
    IMAGES=$(extract_images)
    if [ -z "$IMAGES" ]; then
        err "未提取到任何镜像，请检查 helm template 是否正常"
        return 1
    fi

    TOTAL=$(echo "$IMAGES" | wc -l)
    LOADED=0
    CACHED=0
    PULLED=0

    info "共需 $TOTAL 个镜像，开始预加载..."

    while read -r IMG; do
        [ -z "$IMG" ] && continue

        # 检查 minikube 内是否已有
        if minikube ssh -- "sudo docker image inspect $IMG" </dev/null >/dev/null 2>&1; then
            ok "  $IMG — minikube 已有"
            continue
        fi

        # 检查宿主机 Docker 是否已有
        if docker image inspect "$IMG" >/dev/null 2>&1; then
            info "  $IMG — 从宿主机缓存加载..."
        else
            info "  $IMG — 拉取到宿主机缓存..."
            if ! docker pull "$IMG"; then
                err "  $IMG — 拉取失败，跳过"
                continue
            fi
        fi

        # 导入到 minikube
        if minikube image load "$IMG" </dev/null; then
            ok "  $IMG — 已导入 minikube"
        else
            err "  $IMG — 导入 minikube 失败"
        fi
    done <<< "$IMAGES"
}

echo "=========================================="
echo "  OpenTwins 完全重新部署脚本"
echo "=========================================="

# ── 前置检查 ────────────────────────────────────────────────────────────────

step "前置检查"

# 1. 宿主机代理 (Clash) — 宿主机 docker pull 走此代理
if curl -s --max-time 2 --proxy "" http://127.0.0.1:7890 > /dev/null 2>&1 \
   || ss -tlnp 2>/dev/null | grep -q ':7890'; then
    ok "宿主机代理 127.0.0.1:7890 运行中"
else
    err "宿主机代理 127.0.0.1:7890 未运行！镜像拉取将失败"
    echo "请先启动 Clash，再运行此脚本"
    exit 1
fi

# 2. minikube 启动
if ! minikube status 2>/dev/null | grep -q "host: Running"; then
    info "minikube 未运行，正在启动..."
    HOST_IP=$(ip route get 1.1.1.1 | awk '{print $7; exit}')
    if ! minikube start \
      --docker-env HTTP_PROXY="http://${HOST_IP}:7890" \
      --docker-env HTTPS_PROXY="http://${HOST_IP}:7890" \
      --docker-env NO_PROXY="localhost,127.0.0.1,${HOST_IP}" 2>&1; then
        info "minikube start 失败，尝试 minikube delete 后重启..."
        minikube delete 2>/dev/null || true
        if ! minikube start \
          --docker-env HTTP_PROXY="http://${HOST_IP}:7890" \
          --docker-env HTTPS_PROXY="http://${HOST_IP}:7890" \
          --docker-env NO_PROXY="localhost,127.0.0.1,${HOST_IP}" 2>&1; then
            err "minikube 启动失败，请手动排查"
            exit 1
        fi
    fi
    ok "minikube 已启动"
else
    ok "minikube 运行中"
fi

# 3. 宿主机 Aliyun 镜像仓库登录
info "检查宿主机 Aliyun 镜像仓库登录状态..."
if ! docker login --username=tengxiaoqiang13@163.com --password=Ubuntu123456 "$ALIYUN_REGISTRY" 2>/dev/null; then
    err "Aliyun 镜像仓库登录失败，请检查凭据"
    exit 1
fi
ok "Aliyun 镜像仓库登录成功"

# 4. 镜像预加载（核心优化：宿主机 Docker 缓存 + minikube image load）
step "镜像预加载"
preload_images

# 5. Grafana 插件文件 (hostPath: /mnt/data/grafana-plugins/)
info "检查 Grafana 插件文件..."
PLUGINS_MISSING=""
for PLUGIN in "ertis-opentwins-app.zip" "ertis-unity-panel.zip"; do
    if ! minikube ssh -- "test -f /mnt/data/grafana-plugins/$PLUGIN" 2>/dev/null; then
        PLUGINS_MISSING="$PLUGINS_MISSING $PLUGIN"
    fi
done

if [ -n "$PLUGINS_MISSING" ]; then
    info "缺失插件:${PLUGINS_MISSING}，尝试从宿主机 /tmp 复制..."
    COPY_FAILED=""
    for PLUGIN in $PLUGINS_MISSING; do
        if [ -f "/tmp/$PLUGIN" ]; then
            minikube ssh -- "sudo mkdir -p /mnt/data/grafana-plugins"
            minikube cp "/tmp/$PLUGIN" "minikube:/tmp/$PLUGIN"
            minikube ssh -- "sudo cp /tmp/$PLUGIN /mnt/data/grafana-plugins/$PLUGIN"
            ok "$PLUGIN 已复制"
        else
            COPY_FAILED="$COPY_FAILED $PLUGIN"
        fi
    done
    if [ -n "$COPY_FAILED" ]; then
        err "以下插件文件不在 /tmp/，请手动准备后重新运行："
        for PLUGIN in $COPY_FAILED; do
            echo "  # 下载 $PLUGIN :"
        done
        echo ""
        echo "  curl -sL -o /tmp/ertis-opentwins-app.zip 'https://github.com/ertis-research/opentwins-in-grafana/releases/download/latest/ertis-opentwins-app.zip'"
        echo "  curl -sL -o /tmp/ertis-unity-panel.zip 'https://github.com/ertis-research/grafana-panel-unity/releases/download/latest/ertis-unity-panel.zip'"
        echo "  minikube ssh -- 'sudo mkdir -p /mnt/data/grafana-plugins'"
        echo "  minikube cp /tmp/ertis-opentwins-app.zip minikube:/tmp/ertis-opentwins-app.zip"
        echo "  minikube cp /tmp/ertis-unity-panel.zip minikube:/tmp/ertis-unity-panel.zip"
        echo "  minikube ssh -- 'sudo cp /tmp/ertis-*.zip /mnt/data/grafana-plugins/'"
        exit 1
    fi
else
    ok "Grafana 插件文件就绪"
fi

mkdir -p "$CHART_DIR/.tmp"

ok "前置检查全部通过"

# ── 步骤 1: 完全卸载旧环境 ───────────────────────────────────────────────────

step "步骤 1: 卸载旧环境"

helm uninstall "$RELEASE" -n "$NAMESPACE" 2>/dev/null || info "未找到 $RELEASE release，跳过"
kubectl delete namespace "$NAMESPACE" --wait=true --timeout=120s 2>/dev/null || info "命名空间已不存在，跳过"

# 若 namespace 卡在 Terminating，强制清除 finalizers
if kubectl get namespace "$NAMESPACE" 2>/dev/null | grep -q Terminating; then
    info "命名空间卡在 Terminating，强制清除 finalizers..."
    kubectl get namespace "$NAMESPACE" -o json | \
      python3 -c "import sys,json; d=json.load(sys.stdin); d['spec']['finalizers']=[]; print(json.dumps(d))" | \
      kubectl replace --raw "/api/v1/namespaces/$NAMESPACE/finalize" -f -
fi
sleep 3
ok "旧环境已清理"

# ── 步骤 2: 验证 Helm 模板 ───────────────────────────────────────────────────

step "步骤 2: 验证 Helm 模板"

cd "$CHART_DIR"
helm template "$RELEASE" ./ > "$CHART_DIR/.tmp/opentwins-rendered.yaml"
if grep -q "${ALIYUN_REGISTRY}/opentwins/curlimages-curl:7.73.0" "$CHART_DIR/.tmp/opentwins-rendered.yaml"; then
    ok "模板验证通过 — image 配置正确"
else
    err "模板验证失败 — image 配置异常"
    exit 1
fi

# ── 步骤 3: 重新部署 ─────────────────────────────────────────────────────────

step "步骤 3: 重新部署 OpenTwins"

cd "$CHART_DIR"
info "正在部署（日志写入 $CHART_DIR/.tmp/helm-install.log，最长等待 15 分钟）..."
if ! helm upgrade --install "$RELEASE" ./ \
  --namespace "$NAMESPACE" \
  --create-namespace \
  -f values.yaml \
  --wait \
  --timeout 15m \
  --dependency-update \
  --debug > "$CHART_DIR/.tmp/helm-install.log" 2>&1; then
    err "Helm 部署失败！"
    echo ""
    printf "${YELLOW}── Pod 状态 ──${NC}\n"
    kubectl get pods -n "$NAMESPACE" 2>/dev/null || true
    echo ""
    printf "${YELLOW}── 失败 Pod 日志 ──${NC}\n"
    kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null \
      | awk '$3 != "Running" && $3 != "Completed" {print $1}' \
      | while read -r pod; do
          echo "--- $pod ---"
          kubectl logs -n "$NAMESPACE" "$pod" --tail=30 2>/dev/null || true
        done
    echo ""
    printf "${YELLOW}── Helm 日志末尾 ──${NC}\n"
    tail -50 "$CHART_DIR/.tmp/helm-install.log"
    exit 1
fi

ok "Helm 部署完成"

# ── 步骤 4: 等待 pods 就绪 ───────────────────────────────────────────────────

step "步骤 4: 等待所有 pods 就绪"

# telegraf 在 mosquitto 就绪前会重启 1-2 次，属于正常行为，单独等待
info "等待核心组件就绪..."
READY_PODS=$(kubectl get pods \
  -l "app.kubernetes.io/instance=$RELEASE" \
  --field-selector=status.phase!=Succeeded \
  -n "$NAMESPACE" -o name 2>/dev/null)

[ -n "$READY_PODS" ] && echo "$READY_PODS" | xargs kubectl wait --for=condition=ready -n "$NAMESPACE" --timeout=300s 2>/dev/null \
  && ok "所有 pods 就绪" \
  || {
    # 打印当前状态但不中止脚本——telegraf 的短暂重启不是致命错误
    info "部分 pod 尚未就绪，当前状态："
    kubectl get pods -n "$NAMESPACE"
    # 等待 telegraf 稳定（最多 60 秒）
    info "等待 telegraf 稳定..."
    for i in $(seq 1 12); do
      sleep 5
      TELE_STATUS=$(kubectl get pod -n "$NAMESPACE" \
        -l "app.kubernetes.io/name=telegraf" \
        --no-headers 2>/dev/null | awk '{print $3}' | head -1)
      [ "$TELE_STATUS" = "Running" ] && break
    done
    ACTUAL_NOT_READY=$(kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null \
      | awk '{split($2,a,"/"); if(a[1]!=a[2]) print $1, $3}' | grep -v Completed || true)
    if [ -z "$ACTUAL_NOT_READY" ]; then
      ok "所有 pods 就绪"
    else
      err "以下 pods 未就绪:"
      echo "$ACTUAL_NOT_READY"
      kubectl get pods -n "$NAMESPACE"
    fi
  }

# ── 步骤 5: 检查 post-install job ────────────────────────────────────────────

step "步骤 5: 检查 post-install job"

sleep 10
JOB_NAME="${RELEASE}-post-install-ditto-default"

if kubectl get job -n "$NAMESPACE" "$JOB_NAME" 2>/dev/null; then
    ok "Post-install job 已创建"
    info "等待 job 完成..."
    kubectl wait --for=condition=complete "job/$JOB_NAME" -n "$NAMESPACE" --timeout=180s \
      || kubectl wait --for=condition=failed "job/$JOB_NAME" -n "$NAMESPACE" --timeout=10s \
      || true
    printf "${YELLOW}Job 日志:${NC}\n"
    kubectl logs -n "$NAMESPACE" "job/$JOB_NAME" || info "无法获取日志"
else
    err "Post-install job 未创建！"
    info "Helm hooks 检查："
    helm get hooks "$RELEASE" -n "$NAMESPACE" 2>/dev/null | grep -A 30 "post-install-ditto-default" || true
    exit 1
fi

# ── 步骤 6: 验证 Ditto policies ──────────────────────────────────────────────

step "步骤 6: 验证 Ditto policies"

sleep 5
DITTO_GW="${RELEASE}-ditto-gateway"
DITTO_NGINX="${RELEASE}-ditto-nginx"

POLICY_CHECK=$(kubectl exec -n "$NAMESPACE" "deployment/$DITTO_GW" -- \
  curl -s -u ditto:ditto \
  "http://$DITTO_NGINX:8080/api/2/policies/opentwins:basic_policy" 2>/dev/null \
  | grep -c '"policyId"' || echo "0")

if [ "$POLICY_CHECK" -gt 0 ]; then
    ok "Policy 'opentwins:basic_policy' 已创建"
else
    info "Policy 未找到，手动创建..."
    kubectl exec -n "$NAMESPACE" "deployment/$DITTO_GW" -- \
      curl -s -o /dev/null -w "%{http_code}" -X PUT -u ditto:ditto \
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
              "thing:/":  {"grant": ["READ", "WRITE"], "revoke": []},
              "message:/":{"grant": ["READ", "WRITE"], "revoke": []}
            }
          }
        }
      }' \
      "http://$DITTO_NGINX:8080/api/2/policies/opentwins:basic_policy"
    echo ""
    ok "Policy 手动创建完成"
fi

# ── 完成摘要 ─────────────────────────────────────────────────────────────────

MINIKUBE_IP=$(minikube ip)

echo ""
printf "${GREEN}==========================================\n"
printf "  部署完成！\n"
printf "==========================================${NC}\n"
echo ""
echo "访问地址 (Minikube IP: $MINIKUBE_IP):"
echo "  Grafana:      http://$MINIKUBE_IP:30718  (admin / Test123456!)"
echo "  Ditto API:    http://$MINIKUBE_IP:30525  (ditto / ditto)"
echo "  Extended API: http://$MINIKUBE_IP:30526"
echo "  Mosquitto:    $MINIKUBE_IP:30511"
echo ""
echo "验证命令:"
echo "  kubectl get pods -n $NAMESPACE"
echo "  ./verify_deployment.sh"
echo "  python3 get_data_simulate.py"
