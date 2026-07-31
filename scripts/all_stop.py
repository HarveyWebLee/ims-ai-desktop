#!/usr/bin/env python3
"""停止联调监督器，并清理本仓相关残留进程 / 端口（含狂弹的 CMD）。"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PID_FILE = ROOT / "scripts" / ".all-dev.pid"
ROOT_WIN = str(ROOT).replace("/", "\\")


def _kill_tree(pid: int) -> None:
    if pid <= 0:
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    import os
    import signal

    try:
        os.killpg(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass


def _free_ports(*ports: int) -> None:
    if sys.platform != "win32":
        return
    completed = subprocess.run(
        ["netstat", "-ano"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    for port in ports:
        pattern = re.compile(
            rf"^\s*TCP\s+\S+:{port}\s+\S+\s+LISTENING\s+(\d+)\s*$",
            re.IGNORECASE | re.MULTILINE,
        )
        for match in pattern.finditer(completed.stdout or ""):
            _kill_tree(int(match.group(1)))


def _kill_project_leftovers() -> int:
    """结束命令行含本仓路径的 python/uv/agent/cmd（阻止自动重启继续弹窗）。"""
    if sys.platform != "win32":
        return 0
    marker = ROOT_WIN.replace("'", "''")
    script = (
        "$killed = 0; "
        "Get-CimInstance Win32_Process | Where-Object { "
        "  $c = $_.CommandLine; "
        "  if (-not $c) { return $false }; "
        f"  if ($c -notlike '*{marker}*') {{ return $false }}; "
        "  $n = $_.Name; "
        "  $n -in @('python.exe','pythonw.exe','uv.exe','agent.exe','cmd.exe','node.exe') "
        "  -or ($n -eq 'electron.exe') "
        "} | ForEach-Object { "
        "  Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; "
        "  $killed++ "
        "}; "
        "Write-Output $killed"
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    try:
        return int((completed.stdout or "0").strip().splitlines()[-1])
    except (ValueError, IndexError):
        return 0


def main() -> int:
    pid = 0
    if PID_FILE.is_file():
        try:
            pid = int(PID_FILE.read_text(encoding="utf-8").strip())
        except ValueError:
            pid = 0

    if pid > 0:
        print(f"停止联调监督器 pid={pid} ...")
        _kill_tree(pid)

    n = _kill_project_leftovers()
    if n:
        print(f"已清理本仓相关残留进程约 {n} 个")

    _free_ports(8008, 8010)
    if PID_FILE.is_file():
        PID_FILE.unlink(missing_ok=True)
    print("已停止（端口 8008/8010 已尝试释放；不应再弹 CMD）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
