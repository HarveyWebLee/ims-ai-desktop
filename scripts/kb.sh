#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/services/platform-agent-service"
exec uv run python scripts/ingest_to_qdrant.py "$@"
