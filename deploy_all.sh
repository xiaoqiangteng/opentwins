#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# OpenTwins + WineFermentTwin 统一部署脚本
# ═══════════════════════════════════════════════════════════════════════════════
# 用法:
#   ./deploy_all.sh                        # 全部部署（基础设施 + WineTwin Demo）
#   ./deploy_all.sh --infra-only           # 仅部署 OpenTwins 基础设施
#   ./deploy_all.sh --demo-only            # 仅部署 WineTwin Demo（假设基础设施已就绪）
#   ./deploy_all.sh --host-ip x.x.x.x      # 指定本机 IP（默认自动检测）
#   ./deploy_all.sh --opentwins-ip x.x.x.x # 指定 OpenTwins 基础设施 IP（默认 = 本机 IP 或 minikube IP）
#   ./deploy_all.sh --skip-images          # 跳过镜像预加载（已手动加载时使用）
# ═══════════════════════════════════════════════════════════════════════════════
set -eo pipefail

# ── 路径定义 ──────────────────────────────────────────────────────────────────
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENTWINS_CHART_DIR="$PROJECT_ROOT/OpenTwins"
WINE_DEMO_DIR="$PROJECT_ROOT/wine-ferment-twin"

RELEASE="opentwins"
NAMESPACE="opentwins"
ALIYUN_REGISTRY="crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com"

# ── 参数解析 ──────────────────────────────────────────────────────────────────
DEPLOY_INFRA=true
DEPLOY_DEMO=true
SKIP_IMAGES=false
HOST_IP=""
OPENTWINS_HOST_IP=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --infra-only)    DEPLOY_DEMO=false;  shift ;;
    --demo-only)     DEPLOY_INFRA=false; shift ;;
    --skip-images)   SKIP_IMAGES=true;   shift ;;
    --host-ip)       HOST_IP="$2";       shift 2 ;;
    --opentwins-ip)  OPENTWINS_HOST_IP="$2"; shift 2 ;;
    -h|--help)
      head -12 "$0" | tail -10
      exit 0 ;;
    *) echo "未知参数: $1"; exit 1 ;;
  esac
done

# ── 颜色 & 工具函数 ──────────────────────────────────────────────────────────
export no_proxy="192.168.49.2,localhost,127.0.0.1,10.96.0.0/12,10.244.0.0/16,.svc,.cluster.local,minikube"
export NO_PROXY="$no_proxy"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
ok()   { printf "${GREEN}✓ %s${NC}\n" "$*"; }
err()  { printf "${RED}✗ %s${NC}\n" "$*"; }
info() { printf "${BLUE}→ %s${NC}\n" "$*"; }
step() { printf "\n${YELLOW}══ %s ══${NC}\n" "$*"; }
die()  { err "$*"; exit 1; }

# ── 检测 IP ──────────────────────────────────────────────────────────────────
[[ -z "$HOST_IP" ]] && HOST_IP="$(hostname -I | awk '{print $1}')"
if [[ -z "$OPENTWINS_HOST_IP" ]]; then
  OPENTWINS_HOST_IP="$HOST_IP"
  # 如果本机访问不到 Ditto，尝试 minikube IP
  if ! curl -fsS --max-time 3 -u "ditto:ditto" "http://${OPENTWINS_HOST_IP}:30525/api/2/things" >/dev/null 2>&1 \
     && command -v minikube >/dev/null 2>&1; then
    MK_IP="$(minikube ip 2>/dev/null || true)"
    [[ -n "$MK_IP" ]] && OPENTWINS_HOST_IP="$MK_IP"
  fi
fi

echo "=========================================="
echo "  OpenTwins + WineFermentTwin 统一部署"
echo "=========================================="
echo "  本机 IP:           $HOST_IP"
echo "  OpenTwins 基础设施: $OPENTWINS_HOST_IP"
echo "  部署基础设施:       $DEPLOY_INFRA"
echo "  部署 WineTwin Demo: $DEPLOY_DEMO"
echo "=========================================="

# ═════════════════════════════════════════════════════════════════════════════
# 阶段 A: OpenTwins 基础设施部署 (minikube + helm)
# ═════════════════════════════════════════════════════════════════════════════

if [[ "$DEPLOY_INFRA" == true ]]; then

  # ── 动态提取镜像列表 ──────────────────────────────────────────────────────
  extract_images() {
    helm template "$RELEASE" "$OPENTWINS_CHART_DIR" --namespace "$NAMESPACE" -f "$OPENTWINS_CHART_DIR/values.yaml" 2>/dev/null \
      | grep 'image:' \
      | grep -v 'background-image' \
      | sed 's/.*image: *//' \
      | tr -d '"' \
      | sed 's/^docker\.io\///' \
      | grep -v '^bats/bats' \
      | grep -v '^busybox$' \
      | sort -u
  }

  # ── 镜像预加载 ───────────────────────────────────────────────────────────
  preload_images() {
    IMAGES=$(extract_images)
    if [ -z "$IMAGES" ]; then
      die "未提取到任何镜像，请检查 helm template 是否正常"
    fi
    TOTAL=$(echo "$IMAGES" | wc -l)
    info "共需 $TOTAL 个镜像，开始预加载..."
    while read -r IMG; do
      [ -z "$IMG" ] && continue
      if minikube ssh -- "sudo docker image inspect $IMG" </dev/null >/dev/null 2>&1; then
        ok "  $IMG — minikube 已有"; continue
      fi
      if docker image inspect "$IMG" >/dev/null 2>&1; then
        info "  $IMG — 从宿主机缓存加载..."
      else
        info "  $IMG — 拉取到宿主机缓存..."
        if ! docker pull "$IMG"; then err "  $IMG — 拉取失败，跳过"; continue; fi
      fi
      if minikube image load "$IMG" </dev/null; then
        ok "  $IMG — 已导入 minikube"
      else
        err "  $IMG — 导入 minikube 失败"
      fi
    done <<< "$IMAGES"
  }

  # ── A1: 前置检查 ──────────────────────────────────────────────────────────
  step "A1: 前置检查"

  # 1) 宿主机代理
  if curl -s --max-time 2 --proxy "" http://127.0.0.1:7890 >/dev/null 2>&1 \
     || ss -tlnp 2>/dev/null | grep -q ':7890'; then
    ok "宿主机代理 127.0.0.1:7890 运行中"
  else
    die "宿主机代理 127.0.0.1:7890 未运行！请先启动 Clash"
  fi

  # 2) minikube
  if ! minikube status 2>/dev/null | grep -q "host: Running"; then
    info "minikube 未运行，正在启动..."
    _PROXY_IP="$(ip route get 1.1.1.1 | awk '{print $7; exit}')"
    if ! minikube start \
      --docker-env HTTP_PROXY="http://${_PROXY_IP}:7890" \
      --docker-env HTTPS_PROXY="http://${_PROXY_IP}:7890" \
      --docker-env NO_PROXY="localhost,127.0.0.1,${_PROXY_IP}" 2>&1; then
      info "minikube start 失败，尝试 minikube delete 后重启..."
      minikube delete 2>/dev/null || true
      minikube start \
        --docker-env HTTP_PROXY="http://${_PROXY_IP}:7890" \
        --docker-env HTTPS_PROXY="http://${_PROXY_IP}:7890" \
        --docker-env NO_PROXY="localhost,127.0.0.1,${_PROXY_IP}" 2>&1 \
        || die "minikube 启动失败"
    fi
    ok "minikube 已启动"
  else
    ok "minikube 运行中"
  fi

  # 3) Aliyun 登录
  info "检查 Aliyun 镜像仓库登录..."
  docker login --username=tengxiaoqiang13@163.com --password=Ubuntu123456 "$ALIYUN_REGISTRY" 2>/dev/null \
    || die "Aliyun 镜像仓库登录失败"
  ok "Aliyun 登录成功"

  # 4) 镜像预加载
  if [[ "$SKIP_IMAGES" == false ]]; then
    step "A2: 镜像预加载"
    preload_images
  else
    info "跳过镜像预加载 (--skip-images)"
  fi

  # 5) Grafana 插件
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
      err "以下插件文件不在 /tmp/:"
      for PLUGIN in $COPY_FAILED; do echo "  $PLUGIN"; done
      echo ""
      echo "  请先下载后重新运行："
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

  mkdir -p "$OPENTWINS_CHART_DIR/.tmp"
  ok "前置检查全部通过"

  # ── A3: 卸载旧环境 ────────────────────────────────────────────────────────
  step "A3: 卸载旧 OpenTwins 环境"
  helm uninstall "$RELEASE" -n "$NAMESPACE" 2>/dev/null || info "未找到 $RELEASE release，跳过"
  kubectl delete namespace "$NAMESPACE" --wait=true --timeout=120s 2>/dev/null || info "命名空间已不存在"
  if kubectl get namespace "$NAMESPACE" 2>/dev/null | grep -q Terminating; then
    info "命名空间卡在 Terminating，强制清除 finalizers..."
    kubectl get namespace "$NAMESPACE" -o json | \
      python3 -c "import sys,json; d=json.load(sys.stdin); d['spec']['finalizers']=[]; print(json.dumps(d))" | \
      kubectl replace --raw "/api/v1/namespaces/$NAMESPACE/finalize" -f -
  fi
  sleep 3
  ok "旧环境已清理"

  # ── A4: Helm 部署 ─────────────────────────────────────────────────────────
  step "A4: Helm 部署 OpenTwins"

  cd "$OPENTWINS_CHART_DIR"
  helm template "$RELEASE" ./ > "$OPENTWINS_CHART_DIR/.tmp/opentwins-rendered.yaml"
  if grep -q "${ALIYUN_REGISTRY}/opentwins/curlimages-curl:7.73.0" "$OPENTWINS_CHART_DIR/.tmp/opentwins-rendered.yaml"; then
    ok "模板验证通过"
  else
    die "模板验证失败 — image 配置异常"
  fi

  info "正在部署 (最长等待 15 分钟)..."
  if ! helm upgrade --install "$RELEASE" ./ \
    --namespace "$NAMESPACE" \
    --create-namespace \
    -f values.yaml \
    --wait \
    --timeout 15m \
    --dependency-update \
    --debug > "$OPENTWINS_CHART_DIR/.tmp/helm-install.log" 2>&1; then
    err "Helm 部署失败！"
    kubectl get pods -n "$NAMESPACE" 2>/dev/null || true
    echo ""
    kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null \
      | awk '$3 != "Running" && $3 != "Completed" {print $1}' \
      | while read -r pod; do
          echo "--- $pod ---"
          kubectl logs -n "$NAMESPACE" "$pod" --tail=30 2>/dev/null || true
        done
    echo ""
    tail -50 "$OPENTWINS_CHART_DIR/.tmp/helm-install.log"
    exit 1
  fi
  ok "Helm 部署完成"

  # ── A5: 等待 pods 就绪 ────────────────────────────────────────────────────
  step "A5: 等待所有 pods 就绪"

  READY_PODS=$(kubectl get pods \
    -l "app.kubernetes.io/instance=$RELEASE" \
    --field-selector=status.phase!=Succeeded \
    -n "$NAMESPACE" -o name 2>/dev/null)

  [ -n "$READY_PODS" ] && echo "$READY_PODS" | xargs kubectl wait --for=condition=ready -n "$NAMESPACE" --timeout=300s 2>/dev/null \
    && ok "所有 pods 就绪" \
    || {
      info "部分 pod 尚未就绪，当前状态："
      kubectl get pods -n "$NAMESPACE"
      info "等待 telegraf 稳定..."
      for i in $(seq 1 12); do
        sleep 5
        TELE_STATUS=$(kubectl get pod -n "$NAMESPACE" -l "app.kubernetes.io/name=telegraf" --no-headers 2>/dev/null | awk '{print $3}' | head -1)
        [ "$TELE_STATUS" = "Running" ] && break
      done
      ACTUAL_NOT_READY=$(kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null \
        | awk '{split($2,a,"/"); if(a[1]!=a[2]) print $1, $3}' | grep -v Completed || true)
      if [ -z "$ACTUAL_NOT_READY" ]; then
        ok "所有 pods 就绪"
      else
        err "以下 pods 未就绪:"; echo "$ACTUAL_NOT_READY"
        kubectl get pods -n "$NAMESPACE"
      fi
    }

  # ── A6: Post-install job ─────────────────────────────────────────────────
  step "A6: 检查 post-install job"

  sleep 10
  JOB_NAME="${RELEASE}-post-install-ditto-default"
  if kubectl get job -n "$NAMESPACE" "$JOB_NAME" 2>/dev/null; then
    ok "Post-install job 已创建"
    info "等待 job 完成..."
    kubectl wait --for=condition=complete "job/$JOB_NAME" -n "$NAMESPACE" --timeout=180s \
      || kubectl wait --for=condition=failed "job/$JOB_NAME" -n "$NAMESPACE" --timeout=10s \
      || true
    kubectl logs -n "$NAMESPACE" "job/$JOB_NAME" || info "无法获取日志"
  else
    die "Post-install job 未创建！"
  fi

  # ── A7: 验证 Ditto policies ──────────────────────────────────────────────
  step "A7: 验证 Ditto policies"

  sleep 5
  DITTO_GW="${RELEASE}-ditto-gateway"
  DITTO_NGINX="${RELEASE}-ditto-nginx"

  POLICY_CHECK=$(kubectl exec -n "$NAMESPACE" "deployment/$DITTO_GW" -- \
    curl -s -u ditto:ditto \
    "http://$DITTO_NGINX:8080/api/2/policies/opentwins:basic_policy" 2>/dev/null \
    | grep -c '"policyId"' || echo "0")

  if [ "$POLICY_CHECK" -gt 0 ]; then
    ok "Policy 'opentwins:basic_policy' 已存在"
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

  # 更新 OPENTWINS_HOST_IP（minikube 部署后可能有变化）
  OPENTWINS_HOST_IP="$(minikube ip)"
  ok "OpenTwins 基础设施部署完成 (IP: $OPENTWINS_HOST_IP)"

fi  # DEPLOY_INFRA

# ═════════════════════════════════════════════════════════════════════════════
# 阶段 B: WineFermentTwin Demo 部署
# ═════════════════════════════════════════════════════════════════════════════

if [[ "$DEPLOY_DEMO" == true ]]; then

  step "B1: 检查 OpenTwins 基础设施连通性"

  DITTO_USER="${DITTO_USERNAME:-ditto}"
  DITTO_PASS="${DITTO_PASSWORD:-ditto}"

  _fail=0
  if curl -fsS --max-time 5 -u "${DITTO_USER}:${DITTO_PASS}" "http://${OPENTWINS_HOST_IP}:30525/api/2/things" >/dev/null 2>&1; then
    ok "Ditto API 连通"
  else
    err "Ditto API 不可达 (${OPENTWINS_HOST_IP}:30525)"; _fail=1
  fi
  if timeout 4 bash -c "</dev/tcp/${OPENTWINS_HOST_IP}/30511" 2>/dev/null; then
    ok "Mosquitto MQTT 连通"
  else
    err "Mosquitto MQTT 不可达 (${OPENTWINS_HOST_IP}:30511)"; _fail=1
  fi
  if [[ "$_fail" -eq 1 ]]; then
    die "OpenTwins 基础设施未就绪，请先运行 ./deploy_all.sh 或 ./deploy_all.sh --infra-only"
  fi

  # ── B2: Python 环境 & 依赖 ────────────────────────────────────────────────
  step "B2: 准备 Python 环境 & 依赖"

  cd "$WINE_DEMO_DIR"
  mkdir -p logs

  PYTHON_BIN="python3"
  if python3 -m venv .venv >/dev/null 2>&1; then
    source .venv/bin/activate
    PYTHON_BIN="python"
    python -m pip install --upgrade pip
    pip install -r wine-init/requirements.txt -r wine-simulator/requirements.txt -r winetwin-service/requirements.txt
    ok "venv 依赖安装完成"
  else
    python3 -m pip install --user -r wine-init/requirements.txt -r wine-simulator/requirements.txt -r winetwin-service/requirements.txt
    ok "pip --user 依赖安装完成"
  fi

  # ── B3: 初始化 Wine Twin 类型 & 实例 ──────────────────────────────────────
  step "B3: 初始化 Wine Twin 类型 & 实例"

  export DITTO_BASE_URL="http://${OPENTWINS_HOST_IP}:30525"
  export EXTENDED_API_URL="http://${OPENTWINS_HOST_IP}:30526"

  "$PYTHON_BIN" wine-init/init_wine_types.py \
    --ditto-url "$DITTO_BASE_URL" \
    --extended-api "$EXTENDED_API_URL" \
    --username "$DITTO_USER" --password "$DITTO_PASS"
  ok "Wine Twin 类型初始化完成"

  "$PYTHON_BIN" wine-init/create_wine_twins.py \
    --schema configs/wine_twin_schema.json \
    --ditto-url "$DITTO_BASE_URL" \
    --username "$DITTO_USER" --password "$DITTO_PASS"
  ok "Wine Twin 实例创建完成"

  "$PYTHON_BIN" wine-init/verify_wine_twins.py \
    --ditto-url "$DITTO_BASE_URL" \
    --username "$DITTO_USER" --password "$DITTO_PASS"
  ok "Wine Twin 实例验证完成"

  # ── B4: 停止旧进程 & 启动服务 ─────────────────────────────────────────────
  step "B4: 启动 WineTwin 服务"

  bash scripts/stop_demo.sh >/dev/null 2>&1 || true

  export MQTT_HOST="${OPENTWINS_HOST_IP}"
  export MQTT_PORT="30511"
  export INFLUX_URL="http://${OPENTWINS_HOST_IP}:30716"
  export WINE_SERVICE_URL="http://${HOST_IP}:8010"
  export WINE_SERVICE_HOST="0.0.0.0"
  export WINE_SERVICE_PORT="8010"
  export CORS_ALLOW_ORIGINS="*"

  # 提取 InfluxDB token
  if [[ -z "${INFLUX_TOKEN:-}" && -f "${OPENTWINS_CHART_DIR}/values.yaml" ]]; then
    INFLUX_TOKEN="$(awk '/adminUser:/{in_admin=1} in_admin && /^[[:space:]]+token:/{gsub(/^[[:space:]]+token:[[:space:]]*"/,""); gsub(/"[[:space:]]*$/,""); print; exit}' "${OPENTWINS_CHART_DIR}/values.yaml")"
  fi
  export INFLUX_TOKEN="${INFLUX_TOKEN:-}"

  # 1) WineTwin Service (FastAPI/uvicorn)
  (cd winetwin-service && \
    DITTO_BASE_URL="$DITTO_BASE_URL" \
    INFLUX_URL="$INFLUX_URL" INFLUX_TOKEN="$INFLUX_TOKEN" \
    CORS_ALLOW_ORIGINS="$CORS_ALLOW_ORIGINS" \
    setsid -f "$PYTHON_BIN" -m uvicorn app.main:app --host 0.0.0.0 --port 8010 \
    > "$WINE_DEMO_DIR/logs/winetwin-service.log" 2>&1 < /dev/null)
  info "WineTwin Service 启动中 (port 8010)..."

  # 2) Wine Frontend (Vite/React)
  (cd wine-frontend && npm install && \
    VITE_API_BASE_URL="$WINE_SERVICE_URL" \
    setsid -f npm run dev -- --host 0.0.0.0 --port 5173 \
    > "$WINE_DEMO_DIR/logs/wine-frontend.log" 2>&1 < /dev/null)
  info "Wine Frontend 启动中 (port 5173)..."

  # 3) Wine Simulator (虚拟传感器数据发送)
  MQTT_HOST="$MQTT_HOST" MQTT_PORT="$MQTT_PORT" \
    setsid -f "$PYTHON_BIN" wine-simulator/wine_fermentation_simulator.py \
    --config configs/wine_simulation.yaml \
    > logs/wine-simulator.log 2>&1 < /dev/null
  info "Wine Simulator 启动中 (MQTT → ${MQTT_HOST}:${MQTT_PORT})..."

  sleep 3

  # ── B5: 验证服务 ──────────────────────────────────────────────────────────
  step "B5: 验证服务"

  if curl -fsS --max-time 5 "http://${HOST_IP}:8010/docs" >/dev/null 2>&1; then
    ok "WineTwin Service API 可访问"
  else
    err "WineTwin Service API 不可达 (http://${HOST_IP}:8010)"
  fi

  if curl -fsS --max-time 5 "http://${HOST_IP}:5173" >/dev/null 2>&1; then
    ok "Wine Frontend 可访问"
  else
    err "Wine Frontend 不可达 (http://${HOST_IP}:5173)"
  fi

fi  # DEPLOY_DEMO

# ═════════════════════════════════════════════════════════════════════════════
# 完成摘要
# ═════════════════════════════════════════════════════════════════════════════

echo ""
printf "${GREEN}==========================================\n"
printf "  部署完成！\n"
printf "==========================================${NC}\n"
echo ""
echo "▸ OpenTwins 基础设施 (minikube):"
echo "  Grafana:        http://${OPENTWINS_HOST_IP}:30718  (admin / Test123456!)"
echo "  Ditto API:      http://${OPENTWINS_HOST_IP}:30525  (ditto / ditto)"
echo "  Extended API:   http://${OPENTWINS_HOST_IP}:30526"
echo "  InfluxDB:       http://${OPENTWINS_HOST_IP}:30716"
echo "  Mosquitto MQTT: ${OPENTWINS_HOST_IP}:30511"
echo ""
echo "▸ WineFermentTwin Demo:"
echo "  Frontend:       http://${HOST_IP}:5173"
echo "  WineTwin API:   http://${HOST_IP}:8010/docs"
echo "  Simulator 日志: $WINE_DEMO_DIR/logs/wine-simulator.log"
echo ""
echo "▸ OpenTwins 原始示例 (如需):"
echo "  cd OpenTwins && python3 get_data_simulate.py"
echo ""
echo "▸ 停止 Demo:"
echo "  ./stop_all.sh           # 停止 WineTwin Demo 进程"
echo "  ./stop_all.sh --infra   # 同时卸载 OpenTwins 基础设施"
