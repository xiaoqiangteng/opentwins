#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# WineFermentTwin Demo 日志查看脚本
# ═══════════════════════════════════════════════════════════════════════════════
# 用法:
#   ./watch_demo.sh                  # 实时追踪所有日志 (tail -f)
#   ./watch_demo.sh --snapshot       # 输出最近 N 行日志快照，不追踪
#   ./watch_demo.sh --simulator      # 仅查看 Wine Simulator 日志
#   ./watch_demo.sh --service        # 仅查看 WineTwin Service 日志
#   ./watch_demo.sh --modelica       # 仅查看 OpenModelica Simulation Service 日志
#   ./watch_demo.sh --frontend       # 仅查看 Wine Frontend 日志
#   ./watch_demo.sh --status         # 仅显示各服务运行状态摘要
#   ./watch_demo.sh --lines 50       # 快照模式显示最近 50 行 (默认 30)
# ═══════════════════════════════════════════════════════════════════════════════
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WINE_DEMO_DIR="$PROJECT_ROOT/wine-ferment-twin"
LOG_DIR="$WINE_DEMO_DIR/logs"

# ── 颜色 ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'
CYAN='\033[0;36m'; MAGENTA='\033[0;35m'; NC='\033[0m'; BOLD='\033[1m'

# ── 默认参数 ────────────────────────────────────────────────────────────────
MODE="follow"            # follow | snapshot | status
FILTER="all"             # all | simulator | service | frontend | modelica
LINES=30

while [[ $# -gt 0 ]]; do
  case "$1" in
    --snapshot)   MODE="snapshot";   shift ;;
    --status)     MODE="status";     shift ;;
    --simulator)  FILTER="simulator"; shift ;;
    --service)    FILTER="service";   shift ;;
    --modelica)   FILTER="modelica";  shift ;;
    --frontend)   FILTER="frontend";  shift ;;
    --lines)      LINES="$2";         shift 2 ;;
    -h|--help)    head -9 "$0" | tail -7; exit 0 ;;
    *)            echo "未知参数: $1"; exit 1 ;;
  esac
done

# ── 日志文件映射 ────────────────────────────────────────────────────────────
declare -A LOG_FILES=(
  [simulator]="$LOG_DIR/wine-simulator.log"
  [service]="$LOG_DIR/winetwin-service.log"
  [modelica]="docker:modelica-simulation-service"
  [frontend]="$LOG_DIR/wine-frontend.log"
)

declare -A LOG_LABELS=(
  [simulator]="🍷 Wine Simulator  (虚拟传感器数据)"
  [service]="⚙️  WineTwin Service (FastAPI)"
  [modelica]="🧮 Modelica Service (OpenModelica)"
  [frontend]="🖥️  Wine Frontend   (Vite/React)"
)

declare -A LOG_COLORS=(
  [simulator]="$CYAN"
  [service]="$GREEN"
  [modelica]="$BLUE"
  [frontend]="$MAGENTA"
)

declare -A PROC_PATTERNS=(
  [simulator]="wine_fermentation_simulator.py"
  [service]="uvicorn app.main:app"
  [modelica]="modelica-simulation-service"
  [frontend]="vite.*5173"
)

# ── 服务状态检测 ────────────────────────────────────────────────────────────
check_status() {
  printf "\n${BOLD}── WineFermentTwin Demo 服务状态 ──${NC}\n\n"

  for key in simulator service modelica frontend; do
    local log="${LOG_FILES[$key]}"
    local label="${LOG_LABELS[$key]}"
    local color="${LOG_COLORS[$key]}"
    local pattern="${PROC_PATTERNS[$key]}"

    # 检查进程 / Docker container
    if [[ "$key" == "modelica" ]] && docker ps --format '{{.Names}}' | grep -qx "$pattern"; then
      local pid=$(docker inspect -f '{{.State.Pid}}' "$pattern" 2>/dev/null || echo "container")
      printf "  ${GREEN}● 运行中${NC}  %s  (PID: %s)\n" "$label" "$pid"
    elif [[ "$key" != "modelica" ]] && pgrep -f "$pattern" >/dev/null 2>&1; then
      local pid=$(pgrep -f "$pattern" | head -1)
      printf "  ${GREEN}● 运行中${NC}  %s  (PID: %s)\n" "$label" "$pid"
    else
      printf "  ${RED}○ 已停止${NC}  %s\n" "$label"
    fi

    # 日志文件信息
    if [[ "$log" == docker:* ]]; then
      local container="${log#docker:}"
      local status=$(docker inspect -f '{{.State.Status}}' "$container" 2>/dev/null || echo "不存在")
      printf "           日志: docker logs %s (状态: %s)\n" "$container" "$status"
    elif [[ -f "$log" ]]; then
      local size=$(du -h "$log" | awk '{print $1}')
      local mtime=$(stat -c '%y' "$log" 2>/dev/null | cut -d'.' -f1 || echo "未知")
      printf "           日志: %s (%s, 最后更新: %s)\n" "$log" "$size" "$mtime"
    else
      printf "           日志: ${YELLOW}文件不存在${NC}\n"
    fi
  done

  # 基础设施连通性快速检查
  printf "\n${BOLD}── 基础设施连通性 ──${NC}\n\n"

  local infra_ok=true
  if command -v minikube >/dev/null 2>&1; then
    local mk_ip=$(minikube ip 2>/dev/null || echo "")
    if [[ -n "$mk_ip" ]]; then
      # Ditto
      if curl -fsS --max-time 2 -u "ditto:ditto" "http://${mk_ip}:30525/api/2/things" >/dev/null 2>&1; then
        printf "  ${GREEN}● Ditto${NC}       http://%s:30525\n" "$mk_ip"
      else
        printf "  ${RED}○ Ditto${NC}       http://%s:30525  不可达\n" "$mk_ip"; infra_ok=false
      fi
      # Mosquitto
      if timeout 2 bash -c "</dev/tcp/${mk_ip}/30511" 2>/dev/null; then
        printf "  ${GREEN}● Mosquitto${NC}  %s:30511\n" "$mk_ip"
      else
        printf "  ${RED}○ Mosquitto${NC}  %s:30511  不可达\n" "$mk_ip"; infra_ok=false
      fi
      # Grafana
      if curl -fsS --max-time 2 "http://${mk_ip}:30718/login" >/dev/null 2>&1; then
        printf "  ${GREEN}● Grafana${NC}    http://%s:30718\n" "$mk_ip"
      else
        printf "  ${YELLOW}○ Grafana${NC}    http://%s:30718  不可达\n" "$mk_ip"
      fi
    else
      printf "  ${YELLOW}无法获取 minikube IP${NC}\n"; infra_ok=false
    fi
  else
    printf "  ${YELLOW}minikube 未安装或不在 PATH 中${NC}\n"; infra_ok=false
  fi

  # WineTwin Service 健康检查
  printf "\n${BOLD}── WineTwin Service API ──${NC}\n\n"
  if curl -fsS --max-time 2 "http://localhost:8010/docs" >/dev/null 2>&1; then
    printf "  ${GREEN}● API 可访问${NC}  http://localhost:8010/docs\n"
  else
    printf "  ${RED}○ API 不可达${NC}  http://localhost:8010/docs\n"
  fi
  if curl -fsS --max-time 2 "http://localhost:5173" >/dev/null 2>&1; then
    printf "  ${GREEN}● Frontend 可访问${NC}  http://localhost:5173\n"
  else
    printf "  ${RED}○ Frontend 不可达${NC}  http://localhost:5173\n"
  fi
  if curl -fsS --max-time 3 "http://localhost:8020/health" >/dev/null 2>&1; then
    printf "  ${GREEN}● Modelica API 可访问${NC}  http://localhost:8020/docs\n"
  else
    printf "  ${RED}○ Modelica API 不可达${NC}  http://localhost:8020/docs\n"
  fi

  echo ""
}

# ── 日志输出 ────────────────────────────────────────────────────────────────
show_logs() {
  local mode="$1"  # follow | snapshot

  # 确定要显示哪些日志
  local keys=()
  if [[ "$FILTER" == "all" ]]; then
    keys=(simulator service modelica frontend)
  else
    keys=("$FILTER")
  fi

  # 检查是否有日志文件存在
  local found_any=false
  for key in "${keys[@]}"; do
    if [[ "${LOG_FILES[$key]}" == docker:* ]]; then
      docker inspect "${LOG_FILES[$key]#docker:}" >/dev/null 2>&1 && found_any=true
    elif [[ -f "${LOG_FILES[$key]}" ]]; then
      found_any=true
    fi
  done

  if [[ "$found_any" == false ]]; then
    printf "${RED}未找到任何日志文件，Demo 可能未启动${NC}\n"
    printf "运行 ./deploy_all.sh --demo-only 启动 Demo\n"
    exit 1
  fi

  if [[ "$mode" == "status" ]]; then
    check_status
    return
  fi

  # ── 快照模式 ─────────────────────────────────────────────────────────────
  if [[ "$mode" == "snapshot" ]]; then
    for key in "${keys[@]}"; do
      local log="${LOG_FILES[$key]}"
      local label="${LOG_LABELS[$key]}"
      local color="${LOG_COLORS[$key]}"

      if [[ "$log" == docker:* ]]; then
        local container="${log#docker:}"
        printf "${color}── %s ──%s${NC}\n" "$label" "$(printf ' %.0s' $(seq 1 $((60 - ${#label})) 2>/dev/null || true))"
        docker logs --tail "$LINES" "$container" 2>&1 || true
        echo ""
        continue
      fi

      if [[ ! -f "$log" ]]; then
        printf "${YELLOW}── %s ── 日志文件不存在 ──${NC}\n\n" "$label"
        continue
      fi

      printf "${color}── %s ──%s${NC}\n" "$label" "$(printf ' %.0s' $(seq 1 $((60 - ${#label}))))"
      tail -n "$LINES" "$log"
      echo ""
    done
    return
  fi

  # ── 实时追踪模式 ─────────────────────────────────────────────────────────
  # 如果只追踪一个日志，直接 tail -f
  if [[ ${#keys[@]} -eq 1 ]]; then
    local key="${keys[0]}"
    local log="${LOG_FILES[$key]}"
    if [[ "$log" == docker:* ]]; then
      local container="${log#docker:}"
      printf "${LOG_COLORS[$key]}── 实时追踪: ${LOG_LABELS[$key]} ──${NC}\n"
      exec docker logs -f --tail "$LINES" "$container"
    elif [[ -f "$log" ]]; then
      printf "${LOG_COLORS[$key]}── 实时追踪: ${LOG_LABELS[$key]} ──${NC}\n"
      exec tail -n "$LINES" -f "$log"
    else
      printf "${RED}日志文件不存在: $log${NC}\n"; exit 1
    fi
  fi

  # 多个日志：使用带前缀的 tail -f（需要 tail --pid 配合，或直接多进程）
  # 这里用简单方案：启动后台 tail 进程，带颜色前缀
  cleanup() {
    jobs -p | xargs kill 2>/dev/null || true
  }
  trap cleanup EXIT INT TERM

  for key in "${keys[@]}"; do
    local log="${LOG_FILES[$key]}"
    local label="${LOG_LABELS[$key]}"
    local color="${LOG_COLORS[$key]}"
    local tag="$key"

    if [[ "$log" == docker:* ]]; then
      local container="${log#docker:}"
      docker logs -f --tail "$LINES" "$container" 2>&1 \
        | sed -u "s/^/${color}[${tag}]${NC} /" &
      continue
    fi

    if [[ ! -f "$log" ]]; then
      printf "${YELLOW}── %s ── 日志文件不存在，跳过 ──${NC}\n" "$label"
      continue
    fi

    # 用 sed 给每行加上彩色标签前缀
    tail -n "$LINES" -f "$log" 2>/dev/null \
      | sed -u "s/^/${color}[${tag}]${NC} /" &
  done

  printf "${BOLD}── 实时追踪所有日志 (Ctrl+C 退出) ──${NC}\n\n"
  wait
}

# ── 主逻辑 ──────────────────────────────────────────────────────────────────
if [[ "$MODE" == "status" ]]; then
  check_status
else
  show_logs "$MODE"
fi
