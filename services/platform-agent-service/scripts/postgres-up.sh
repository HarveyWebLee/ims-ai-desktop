#!/usr/bin/env bash
# 启动 Agent 依赖：Postgres + Qdrant
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose up -d
echo "Postgres: postgresql://agent:agent@127.0.0.1:16543/platform_agent"
echo "Qdrant:   http://127.0.0.1:16333  (Dashboard: /dashboard)"
docker compose ps
