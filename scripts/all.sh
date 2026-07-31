#!/usr/bin/env bash
# 依次启动 Platform MCP → Agent → Electron Desktop
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AGENT_RELOAD="${AGENT_RELOAD:-1}"
MCP_RELOAD="${MCP_RELOAD:-1}"
PIDS=()

is_windows() {
  case "$(uname -s 2>/dev/null || true)" in
    MINGW*|MSYS*|CYGWIN*) return 0 ;;
    *) return 1 ;;
  esac
}

kill_tree() {
  local pid=$1
  if is_windows && command -v taskkill >/dev/null 2>&1; then
    taskkill //F //T //PID "$pid" >/dev/null 2>&1 || true
  else
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
  fi
}

cleanup() {
  local code=$?
  echo ""
  echo "==> 停止 MCP / Agent ..."
  for pid in "${PIDS[@]:-}"; do
    kill_tree "$pid"
  done
  exit "$code"
}
trap cleanup EXIT INT TERM

start_bg() {
  local cwd=$1
  shift
  if is_windows; then
    local py=""
    if command -v python >/dev/null 2>&1; then
      py=python
    elif command -v py >/dev/null 2>&1; then
      py=py
    else
      echo "错误：Windows 下需要 python/py 以隔离后台进程" >&2
      exit 1
    fi
    "$py" "$ROOT/scripts/start_isolated.py" --cwd "$cwd" -- "$@" &
  else
    (cd "$cwd" && exec "$@") &
  fi
  PIDS+=($!)
}

wait_port() {
  local port=$1
  local name=$2
  local i=0
  while true; do
    if command -v curl >/dev/null 2>&1; then
      if curl -sf --connect-timeout 1 "http://127.0.0.1:${port}/health" >/dev/null 2>&1         || curl -sf --connect-timeout 1 "http://127.0.0.1:${port}/mcp/health" >/dev/null 2>&1         || curl -sf --connect-timeout 1 "http://127.0.0.1:${port}/" >/dev/null 2>&1         || curl -sf --connect-timeout 1 "http://127.0.0.1:${port}/mcp" >/dev/null 2>&1; then
        break
      fi
    fi
    if (echo >/dev/tcp/127.0.0.1/"$port") 2>/dev/null; then
      break
    fi
    i=$((i + 1))
    if [ "$i" -gt 90 ]; then
      echo "错误：等待 ${name} (:${port}) 超时" >&2
      exit 1
    fi
    sleep 0.5
  done
  echo "  ✓ ${name} 已就绪 :${port}"
}

echo "==> 1/3 Platform MCP  (:8010)"
export MCP_RELOAD
start_bg "$ROOT/services/platform-mcp-server" uv run python -m platform_mcp
wait_port 8010 "MCP"

echo "==> 2/3 Agent         (:8008)"
export AGENT_RELOAD
start_bg "$ROOT/services/platform-agent-service" uv run agent
wait_port 8008 "Agent"

echo "==> 3/3 Desktop       (Electron)"
echo "    Ctrl+C 将一并停止 MCP / Agent"
cd "$ROOT"
# Electron 二进制下载镜像（可被外部同名环境变量覆盖）
export ELECTRON_MIRROR="${ELECTRON_MIRROR:-https://npmmirror.com/mirrors/electron/}"
pnpm --filter @ims/desktop dev
