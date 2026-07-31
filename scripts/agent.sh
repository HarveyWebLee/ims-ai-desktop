#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if ! curl -sf "http://127.0.0.1:8010/health" >/dev/null 2>&1; then
  echo "[agent.sh] 警告: Platform MCP :8010 未就绪，请先 bash scripts/mcp.sh" >&2
fi
cd "$ROOT/services/platform-agent-service"
exec uv run agent
