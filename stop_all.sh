#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# OpenTwins + WineFermentTwin 统一停止脚本
# ═══════════════════════════════════════════════════════════════════════════════
# 用法:
#   ./stop_all.sh              # 仅停止 WineTwin Demo 进程（不影响基础设施）
#   ./stop_all.sh --infra      # 停止 Demo + 卸载 OpenTwins 基础设施 (helm uninstall)
#   ./stop_all.sh --infra-full # 停止 Demo + 卸载基础设施 + 停止 minikube
# ═══════════════════════════════════════════════════════════════════════════════
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WINE_DEMO_DIR="$PROJECT_ROOT/wine-ferment-twin"
RELEASE="opentwins"
NAMESPACE="opentwins"

STOP_INFRA=false
STOP_MINIKUBE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --infra)      STOP_INFRA=true;    shift ;;
    --infra-full) STOP_INFRA=true; STOP_MINIKUBE=true; shift ;;
    -h|--help)    head -8 "$0" | tail -6; exit 0 ;;
    *)            shift ;;
  esac
done

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
ok()   { printf "${GREEN}✓ %s${NC}\n" "$*"; }
info() { printf "${BLUE}→ %s${NC}\n" "$*"; }
step() { printf "\n${YELLOW}══ %s ══${NC}\n" "$*"; }

# ── 停止 WineTwin Demo ──────────────────────────────────────────────────────
step "停止 WineFermentTwin Demo"

cd "$WINE_DEMO_DIR"

# 通过 PID 文件停止
for f in logs/winetwin-service.pid logs/wine-frontend.pid logs/wine-simulator.pid; do
  if [[ -f "$f" ]]; then
    pid="$(cat "$f")"
    kill "$pid" 2>/dev/null || true
    rm -f "$f"
  fi
done

# 通过进程名兜底
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "wine_fermentation_simulator.py" 2>/dev/null || true
pkill -f "vite.*5173" 2>/dev/null || true

ok "WineFermentTwin Demo 已停止"

# ── 停止 OpenTwins 原始示例的 get_data_simulate.py（如果正在运行）────
pkill -f "get_data_simulate.py" 2>/dev/null && ok "OpenTwins get_data_simulate.py 已停止" || true

# ── 卸载基础设施 ────────────────────────────────────────────────────────────
if [[ "$STOP_INFRA" == true ]]; then
  step "卸载 OpenTwins 基础设施"

  export no_proxy="192.168.49.2,localhost,127.0.0.1,10.96.0.0/12,10.244.0.0/16,.svc,.cluster.local,minikube"
  export NO_PROXY="$no_proxy"

  helm uninstall "$RELEASE" -n "$NAMESPACE" 2>/dev/null && ok "Helm release 已卸载" || info "未找到 Helm release"
  kubectl delete namespace "$NAMESPACE" --wait=true --timeout=120s 2>/dev/null && ok "命名空间已删除" || info "命名空间已不存在"

  # 清理卡住的 Terminating 命名空间
  if kubectl get namespace "$NAMESPACE" 2>/dev/null | grep -q Terminating; then
    info "命名空间卡在 Terminating，强制清除..."
    kubectl get namespace "$NAMESPACE" -o json | \
      python3 -c "import sys,json; d=json.load(sys.stdin); d['spec']['finalizers']=[]; print(json.dumps(d))" | \
      kubectl replace --raw "/api/v1/namespaces/$NAMESPACE/finalize" -f -
    ok "Finalizers 已清除"
  fi
fi

# ── 停止 minikube ───────────────────────────────────────────────────────────
if [[ "$STOP_MINIKUBE" == true ]]; then
  step "停止 minikube"
  minikube stop 2>/dev/null && ok "minikube 已停止" || info "minikube 停止失败"
fi

echo ""
printf "${GREEN}所有服务已停止${NC}\n"
