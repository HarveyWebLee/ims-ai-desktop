#!/usr/bin/env python3
"""
后台启动联调（MCP / Agent / Desktop），不占用当前终端会话。

用法：
  python scripts/all_bg.py
  bash scripts/all.sh --bg

日志：scripts/.all-dev.log
PID： scripts/.all-dev.pid
停止：python scripts/all_stop.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
LOG_FILE = SCRIPTS / ".all-dev.log"
PID_FILE = SCRIPTS / ".all-dev.pid"
SUPERVISOR = SCRIPTS / "dev_supervisor.py"

CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_NO_WINDOW = 0x08000000
# 禁止 DETACHED_PROCESS：控制台程序会 AllocConsole，导致 CMD 窗口反复弹出


def _python() -> list[str]:
    if sys.platform == "win32" and Path(sys.executable).name.lower() == "py.exe":
        return [sys.executable, "-3"]
    return [sys.executable]


def main() -> int:
    if not SUPERVISOR.is_file():
        print(f"错误：找不到 {SUPERVISOR}", file=sys.stderr)
        return 1

    # 若已有记录且进程仍在，直接提示
    if PID_FILE.is_file():
        try:
            old_pid = int(PID_FILE.read_text(encoding="utf-8").strip())
        except ValueError:
            old_pid = 0
        if old_pid > 0:
            alive = False
            if sys.platform == "win32":
                probe = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {old_pid}"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
                alive = str(old_pid) in (probe.stdout or "")
            else:
                try:
                    os.kill(old_pid, 0)
                    alive = True
                except OSError:
                    alive = False
            if alive:
                print(f"联调已在运行 (pid={old_pid})。停止：python scripts/all_stop.py")
                print(f"日志：{LOG_FILE}")
                return 0

    env = os.environ.copy()
    env.setdefault("AGENT_RELOAD", "1")
    env.setdefault("MCP_RELOAD", "1")
    env.setdefault("ELECTRON_MIRROR", "https://npmmirror.com/mirrors/electron/")
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUNBUFFERED", "1")

    log_fp = open(LOG_FILE, "w", encoding="utf-8", errors="replace")
    cmd = [*_python(), str(SUPERVISOR)]
    kwargs: dict = {
        "cwd": str(ROOT),
        "env": env,
        "stdin": subprocess.DEVNULL,
        "stdout": log_fp,
        "stderr": subprocess.STDOUT,
        "close_fds": True,
    }
    if sys.platform == "win32":
        # 无窗口后台跑；不要用 DETACHED_PROCESS（会狂弹 CMD）
        kwargs["creationflags"] = CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
    else:
        kwargs["start_new_session"] = True

    proc = subprocess.Popen(cmd, **kwargs)
    log_fp.close()
    PID_FILE.write_text(str(proc.pid), encoding="utf-8")
    print(f"已后台启动联调 (pid={proc.pid})")
    print("  MCP :8010 → Agent :8008 → Desktop")
    print(f"  日志：{LOG_FILE}")
    print("  停止：python scripts/all_stop.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
