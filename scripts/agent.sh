#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if ! curl -sf "http://127.0.0.1:8010/health" >/dev/null 2>&1; then
  echo "[agent.sh] 警告: Platform MCP :8010 未就绪，请先 bash scripts/mcp.sh" >&2
fi
cd "$ROOT/services/platform-agent-service"
# 不用 `uv run agent`：刷新 Scripts/agent.exe 时若有残留进程会报 os error 32
export PYTHONUTF8="${PYTHONUTF8:-1}"
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"
uv sync --inexact
exec uv run --no-sync python -m app.dev
