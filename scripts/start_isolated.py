#!/usr/bin/env python3
"""
在独立进程组中启动子进程（供调试或旧入口复用）。

联调请优先使用 ``scripts/all.sh`` → ``scripts/dev_supervisor.py``：
监督器已内置进程隔离、日志前缀与崩溃自动重启。

Windows 上 uvicorn WatchFiles 热重载可能向同一控制台广播 CTRL_C，
CREATE_NEW_PROCESS_GROUP 可隔离该广播。
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
    popen_cmd: str | list[str] = command
    shell = False
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
        popen_cmd = subprocess.list2cmdline(command)
        shell = True

    process = subprocess.Popen(
        popen_cmd,
        cwd=args.cwd,
        shell=shell,
        creationflags=creationflags,
        start_new_session=(sys.platform != "win32"),
    )
    return int(process.wait())


if __name__ == "__main__":
    raise SystemExit(main())
