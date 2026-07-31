"""知识库 CLI：``uv run kb --dir ...`` / ``uv run kb --search ...``。"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def main() -> None:
    script = Path(__file__).resolve().parents[2] / "scripts" / "ingest_to_qdrant.py"
    spec = importlib.util.spec_from_file_location("ingest_to_qdrant", script)
    if spec is None or spec.loader is None:
        print(f"无法加载脚本: {script}", file=sys.stderr)
        raise SystemExit(1)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    raise SystemExit(mod.main())


if __name__ == "__main__":
    main()
