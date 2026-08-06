"""
platform-contracts 本地代码质量入口：格式化 / Lint / 类型检查 / 测试。

用法（需先 ``uv sync --extra dev``）::

    uv run check format
    uv run check lint
    uv run check typecheck
    uv run check test
    uv run check fix          # format + lint --fix
    uv run check gate         # 提交门禁：format --check + lint + typecheck（不含 pytest）
    uv run check all          # 完整自检：gate + test
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

# 与 pyproject.toml [tool.ruff] / [tool.pyright] 的 include 保持一致
TARGETS = ("contracts", "tests")
# 显式 --project，避免仓根 pyrightconfig.json（IDE 用）污染本服务 CLI 检查
_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: Sequence[str]) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd)


def _py_module(module: str, *args: str) -> list[str]:
    """用当前解释器 -m 调用工具，避免 Windows 下 Scripts 未入 PATH。"""
    return [sys.executable, "-m", module, *args]


def cmd_format(*, check: bool = False) -> int:
    args = _py_module("ruff", "format", *TARGETS)
    if check:
        args.append("--check")
    return _run(args)


def cmd_lint(*, fix: bool = False) -> int:
    args = _py_module("ruff", "check", *TARGETS)
    if fix:
        args.append("--fix")
    return _run(args)


def cmd_typecheck() -> int:
    return _run(_py_module("basedpyright", "--project", str(_PROJECT_ROOT)))


def cmd_test(pytest_args: Sequence[str]) -> int:
    return _run(_py_module("pytest", *pytest_args))


def cmd_fix() -> int:
    """写回：格式化 + 自动修复可修 lint。"""
    code = cmd_format(check=False)
    if code != 0:
        return code
    return cmd_lint(fix=True)


def cmd_gate() -> int:
    """提交门禁：静态检查，不跑 pytest。"""
    steps = (
        ("format --check", lambda: cmd_format(check=True)),
        ("lint", lambda: cmd_lint(fix=False)),
        ("typecheck", cmd_typecheck),
    )
    for name, step in steps:
        print(f"\n==> {name}", flush=True)
        code = step()
        if code != 0:
            print(f"\n[check] 失败于: {name} (exit={code})", flush=True)
            return code
    print("\n[check] gate 通过（未跑 test）", flush=True)
    return 0


def cmd_all(pytest_args: Sequence[str]) -> int:
    """完整自检：gate + pytest；手动使用，不进 pre-commit。"""
    code = cmd_gate()
    if code != 0:
        return code
    print("\n==> test", flush=True)
    code = cmd_test(pytest_args)
    if code != 0:
        print(f"\n[check] 失败于: test (exit={code})", flush=True)
        return code
    print("\n[check] 全部通过", flush=True)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check",
        description="platform-contracts 本地代码质量管理（format / lint / typecheck / test）",
    )
    parser.add_argument(
        "command",
        choices=("format", "lint", "typecheck", "test", "fix", "gate", "all"),
        help="要执行的子命令",
    )
    parser.add_argument(
        "pytest_args",
        nargs="*",
        help="仅 test/all 时透传给 pytest",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "format":
        return cmd_format(check=False)
    if args.command == "lint":
        return cmd_lint(fix=False)
    if args.command == "typecheck":
        return cmd_typecheck()
    if args.command == "test":
        return cmd_test(args.pytest_args)
    if args.command == "fix":
        return cmd_fix()
    if args.command == "gate":
        return cmd_gate()
    return cmd_all(args.pytest_args)


if __name__ == "__main__":
    sys.exit(main())
