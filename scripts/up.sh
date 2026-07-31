#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Postgres + Qdrant + Redis"
docker compose -f "$ROOT/deploy/docker-compose.yml" up -d

cat <<'EOF'
依赖已启动（Postgres :16543 / Qdrant :16333 / Redis :13386）。

一键联调：
  bash scripts/all.sh

分端启动：
  bash scripts/mcp.sh       # :8010
  bash scripts/agent.sh     # :8008
  bash scripts/desktop.sh   # Electron

知识库入库示例：
  bash scripts/kb.sh --dir e:/WORK/CODE/ims-ai-desktop/prj-docs
EOF
