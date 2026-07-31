#!/usr/bin/env bash
# 一键联调：Platform MCP → Agent → Electron Desktop（进程相互隔离）
#
# 行为：
# - 三个服务由 scripts/dev_supervisor.py 监督并行运行
# - 任一服务热更新 / 崩溃 / 异常退出不会拖垮其他服务（自动重启）
# - 仅 Ctrl+C 时统一停止全部（Windows：须 2 秒内连按两次，防热重载误杀）
# - Windows 子进程用 CREATE_NO_WINDOW（禁止 DETACHED_PROCESS，避免狂弹 CMD）
#
# 后台启动（不占当前终端 / Cursor tab，且不弹 CMD）：
#   bash scripts/all.sh --bg
#   停止：python scripts/all_stop.py
#
# 可选环境变量：
#   AGENT_RELOAD=0  关闭 Agent 热重载
#   MCP_RELOAD=0    关闭 MCP 热重载
#   ELECTRON_MIRROR 覆盖 Electron 下载镜像
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export AGENT_RELOAD="${AGENT_RELOAD:-1}"
export MCP_RELOAD="${MCP_RELOAD:-1}"
export ELECTRON_MIRROR="${ELECTRON_MIRROR:-https://npmmirror.com/mirrors/electron/}"
# Windows 控制台默认 GBK；强制 UTF-8 避免监督器/子进程中文乱码
export PYTHONUTF8="${PYTHONUTF8:-1}"
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"

resolve_python() {
  if command -v python >/dev/null 2>&1; then
    echo "python"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return
  fi
  if command -v py >/dev/null 2>&1; then
    echo "py"
    return
  fi
  echo ""
}

PY="$(resolve_python)"
if [ -z "$PY" ]; then
  echo "错误：需要 python / python3 / py 以运行联调监督器" >&2
  exit 1
fi

run_py() {
  if [ "$PY" = "py" ]; then
    py -3 "$@"
  else
    "$PY" "$@"
  fi
}

# --bg / --detach：脱离终端后台跑，避免占用 Cursor 终端 tab
if [ "${1:-}" = "--bg" ] || [ "${1:-}" = "--detach" ] || [ "${ALL_BG:-0}" = "1" ]; then
  run_py "$ROOT/scripts/all_bg.py"
  exit $?
fi

echo "==> 一键联调（MCP :8010 → Agent :8008 → Desktop）"
echo "    进程隔离监督：热更新/异常互不影响；Ctrl+C 停止全部"
echo "    若不想占用本终端：bash scripts/all.sh --bg"

if [ "$PY" = "py" ]; then
  exec py -3 "$ROOT/scripts/dev_supervisor.py"
fi
exec "$PY" "$ROOT/scripts/dev_supervisor.py"
