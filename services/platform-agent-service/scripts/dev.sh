#!/usr/bin/env bash
# 本地开发启动（Git Bash / WSL / macOS / Linux）
# 等价于：uv run agent
set -euo pipefail
cd "$(dirname "$0")/.."
exec uv run agent
