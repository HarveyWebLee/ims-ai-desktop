#!/usr/bin/env python3
"""
在独立进程组中启动子进程，供 scripts/all.sh 后台拉起 MCP / Agent。

Windows 上 uvicorn WatchFiles 热重载可能向同一控制台广播 CTRL_C，
导致 all.sh / App 一并退出。CREATE_NEW_PROCESS_GROUP 可隔离该广播。
"""

from __future__ import annotations

import argparse
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="独立进程组启动命令")
    parser.add_argument("--cwd", required=True, help="工作目录")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="要执行的命令（前可带 --）")
    args = parser.parse_args()

    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("错误：缺少要执行的命令", file=sys.stderr)
        return 2

    creationflags = 0
    if sys.platform == "win32":
        # 禁用该进程组对控制台 CTRL+C 的接收，避免热重载拖垮联调脚本
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

    process = subprocess.Popen(
        command,
        cwd=args.cwd,
        creationflags=creationflags,
    )
    return int(process.wait())


if __name__ == "__main__":
    raise SystemExit(main())
