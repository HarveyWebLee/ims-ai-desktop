"""
Playbook 自动评测 CLI（W0）。

用法::

    uv run python scripts/eval_playbook.py
    uv run python scripts/eval_playbook.py --cases eval/playbook_cases.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SERVICE_ROOT = Path(__file__).resolve().parent.parent
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))

from app.services.playbook.eval_runner import DEFAULT_CASES_PATH, run_eval  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Playbook 自动评测（固定用例）")
    parser.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASES_PATH,
        help=f"用例 JSON（默认 {DEFAULT_CASES_PATH.name}）",
    )
    args = parser.parse_args(argv)
    path: Path = args.cases
    if not path.is_file():
        print(f"[FAIL] 用例文件不存在: {path}", file=sys.stderr)
        return 2

    results = run_eval(path)
    failed = [r for r in results if not r.ok]
    for r in results:
        mark = "PASS" if r.ok else "FAIL"
        print(f"[{mark}] {r.case_id}")
        for err in r.errors:
            print(f"       - {err}")

    print(f"\n合计 {len(results)}，失败 {len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
