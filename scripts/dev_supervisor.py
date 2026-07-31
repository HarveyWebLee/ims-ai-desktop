#!/usr/bin/env python3
"""
联调进程监督器：同时拉起 Platform MCP / Agent / Desktop。

设计目标：
- 任一服务热重载、崩溃或异常退出，不牵连其余服务
- 崩溃后自动重启（指数退避）
- 仅用户 Ctrl+C / SIGTERM 时统一停止
- Windows 下用 CREATE_NEW_PROCESS_GROUP 隔离控制台 CTRL_C 广播
- 子进程强制 UTF-8，避免中文日志乱码
- Agent 用 ``python -m app.dev`` + ``--no-sync``，避免 uv 改写占用中的 agent.exe
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_RESTART_INITIAL_SEC = 1.0
_RESTART_MAX_SEC = 30.0
_RESTART_RESET_AFTER_SEC = 60.0

_PRINT_LOCK = threading.Lock()


def _log(msg: str, *, file=None) -> None:
    """串行写终端，避免多服务日志行交错。"""
    with _PRINT_LOCK:
        print(msg, file=file, flush=True)


def _configure_stdio_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def _which(cmd: str) -> str:
    path = shutil.which(cmd)
    if not path:
        print(f"错误：找不到命令 `{cmd}`，请确认已安装并在 PATH 中", file=sys.stderr)
        raise SystemExit(1)
    return path


def _child_env() -> dict[str, str]:
    """强制子进程 UTF-8 + 无缓冲，避免 Windows 默认 GBK 导致乱码/行交错。"""
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    return env


def _pids_listening_on(port: int) -> list[int]:
    """解析 netstat，找出监听指定端口的 PID。"""
    try:
        completed = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError:
        return []
    pids: set[int] = set()
    # TCP    0.0.0.0:8008    0.0.0.0:0    LISTENING    1234
    pattern = re.compile(
        rf"^\s*TCP\s+\S+:{port}\s+\S+\s+LISTENING\s+(\d+)\s*$",
        re.IGNORECASE | re.MULTILINE,
    )
    for match in pattern.finditer(completed.stdout or ""):
        pid = int(match.group(1))
        if pid > 0:
            pids.add(pid)
    return sorted(pids)


def _kill_pid_tree(pid: int) -> None:
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
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return


def _free_port(port: int, *, label: str) -> None:
    pids = _pids_listening_on(port)
    if not pids:
        return
    _log(f"  · 释放 :{port} 占用（{label}）: PID {', '.join(map(str, pids))}")
    for pid in pids:
        _kill_pid_tree(pid)
    # 等端口真正让出
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if not _pids_listening_on(port):
            return
        time.sleep(0.2)


def _kill_stale_venv_entrypoints() -> None:
    """结束仍占用 .venv Scripts/agent.exe 的残留进程（uv 同步会因此失败）。"""
    if sys.platform != "win32":
        return
    marker = str(ROOT / "services" / "platform-agent-service").replace("/", "\\")
    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    "Get-CimInstance Win32_Process | "
                    "Where-Object { $_.Name -eq 'agent.exe' -and $_.CommandLine -like "
                    f"'*{marker}*' }} | "
                    "ForEach-Object { $_.ProcessId }"
                ),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError:
        return
    pids: list[int] = []
    for line in (completed.stdout or "").splitlines():
        line = line.strip()
        if line.isdigit():
            pids.append(int(line))
    if not pids:
        return
    _log(f"  · 清理残留 agent.exe: PID {', '.join(map(str, pids))}")
    for pid in pids:
        _kill_pid_tree(pid)


def _port_ready(port: int) -> bool:
    for path in ("/health", "/mcp/health", "/", "/mcp"):
        url = f"http://127.0.0.1:{port}{path}"
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if 200 <= getattr(resp, "status", 200) < 500:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            continue
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def _wait_port(port: int, name: str, *, timeout_sec: float = 45.0) -> bool:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if _port_ready(port):
            _log(f"  ✓ {name} 已就绪 :{port}")
            return True
        time.sleep(0.5)
    _log(f"⚠ 等待 {name} (:{port}) 超时", file=sys.stderr)
    return False


def _needs_shell(command: list[str]) -> bool:
    """仅 .cmd/.bat 需要 shell；uv.exe 等直接 exec，便于挂上隔离 flags。"""
    exe = command[0].lower()
    return exe.endswith((".cmd", ".bat"))


def _windows_creationflags() -> int:
    """
    Windows 子进程启动 flags（禁止 DETACHED_PROCESS）：

    - DETACHED_PROCESS 会让控制台程序自行 AllocConsole，表现为不停弹出 CMD 窗口，
      且崩溃自动重启时会「没完没了」弹窗。
    - CREATE_NO_WINDOW：无控制台窗口；stdout 已接到 PIPE，日志仍可汇聚。
    - CREATE_NEW_PROCESS_GROUP：降低与监督器控制台信号的耦合；
      热重载误发 SIGINT 仍由监督器「双击确认」兜底。
    """
    create_new_process_group = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
    create_no_window = 0x08000000  # CREATE_NO_WINDOW
    return int(create_new_process_group) | create_no_window


def _popen_isolated(command: list[str], cwd: Path) -> subprocess.Popen[str]:
    """在独立进程组中启动；Windows 下无新控制台窗口。"""
    common: dict = {
        "cwd": str(cwd),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "stdin": subprocess.DEVNULL,
        "bufsize": 1,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "env": _child_env(),
    }
    if sys.platform == "win32":
        flags = _windows_creationflags()
        if _needs_shell(command):
            # 显式 cmd /c + CREATE_NO_WINDOW，避免 shell=True 默认弹出可见控制台
            cmdline = subprocess.list2cmdline(command)
            return subprocess.Popen(
                ["cmd.exe", "/d", "/c", cmdline],
                shell=False,
                creationflags=flags,
                **common,
            )
        return subprocess.Popen(
            command,
            shell=False,
            creationflags=flags,
            **common,
        )
    return subprocess.Popen(
        command,
        start_new_session=True,
        **common,
    )


def _kill_tree(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=3)


@dataclass
class Service:
    name: str
    cwd: Path
    command: list[str]
    ready_port: int | None = None
    process: subprocess.Popen[str] | None = None
    restart_delay: float = _RESTART_INITIAL_SEC
    started_at: float = 0.0
    stopping: bool = False
    restarting: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)

    def prepare(self) -> None:
        """启动前清理端口与会锁住 uv 入口的残留进程。"""
        if self.ready_port is not None:
            _free_port(self.ready_port, label=self.name)
        if self.name == "agent":
            _kill_stale_venv_entrypoints()

    def start(self) -> None:
        with self.lock:
            if self.stopping:
                return
            self.prepare()
            _log(f"==> 启动 [{self.name}] {' '.join(self.command)}")
            self.process = _popen_isolated(self.command, self.cwd)
            self.started_at = time.monotonic()
            threading.Thread(
                target=self._pump_logs,
                name=f"pump-{self.name}",
                daemon=True,
            ).start()

    def _pump_logs(self) -> None:
        proc = self.process
        if proc is None or proc.stdout is None:
            return
        for line in proc.stdout:
            # 子进程已强制 UTF-8；再兜底去掉可能的孤立替换符行尾
            _log(f"[{self.name}] {line.rstrip()}")

    def alive(self) -> bool:
        proc = self.process
        return proc is not None and proc.poll() is None

    def stop(self) -> None:
        with self.lock:
            self.stopping = True
            proc = self.process
        if proc is not None:
            _log(f"==> 停止 [{self.name}] (pid={proc.pid})")
            _kill_tree(proc)
        if self.ready_port is not None:
            _free_port(self.ready_port, label=f"{self.name}-stop")

    def claim_restart(self) -> bool:
        with self.lock:
            if self.stopping or self.restarting:
                return False
            proc = self.process
            if proc is None or proc.poll() is None:
                return False
            self.restarting = True
            return True

    def maybe_restart(self) -> None:
        with self.lock:
            proc = self.process
            code = None if proc is None else proc.returncode
            lived = time.monotonic() - self.started_at
            delay = self.restart_delay
            if lived >= _RESTART_RESET_AFTER_SEC:
                delay = _RESTART_INITIAL_SEC
            _log(
                f"⚠ [{self.name}] 已退出 (code={code})，{delay:.0f}s 后自动重启"
                f"（不影响其他服务）"
            )
            self.restart_delay = min(max(delay, _RESTART_INITIAL_SEC) * 2, _RESTART_MAX_SEC)

        time.sleep(delay)
        try:
            with self.lock:
                if self.stopping:
                    return
            self.start()
            if self.ready_port is not None:
                if _wait_port(self.ready_port, self.name, timeout_sec=45.0):
                    with self.lock:
                        self.restart_delay = _RESTART_INITIAL_SEC
                else:
                    _log(
                        f"⚠ [{self.name}] 重启后端口未就绪，将继续重试",
                        file=sys.stderr,
                    )
        finally:
            with self.lock:
                self.restarting = False


class Supervisor:
    # Windows：热重载广播的 CTRL_C 与用户真按 Ctrl+C 无法区分；
    # 2 秒内连续两次 SIGINT 才停，单次仅提示（防误杀）。
    _WIN_SIGINT_CONFIRM_SEC = 2.0

    def __init__(self, services: list[Service]) -> None:
        self.services = services
        self._stop_event = threading.Event()
        self._last_sigint_at = 0.0

    def run(self) -> int:
        signal.signal(signal.SIGINT, self._on_signal)
        signal.signal(signal.SIGTERM, self._on_signal)
        if hasattr(signal, "SIGBREAK"):
            # Ctrl+Break：视为明确停止（不受「双击确认」约束）
            signal.signal(signal.SIGBREAK, self._on_signal_force)  # type: ignore[attr-defined]

        for index, svc in enumerate(self.services, start=1):
            if self._stop_event.is_set():
                break
            total = len(self.services)
            title = {
                "mcp": "Platform MCP  (:8010)",
                "agent": "Agent         (:8008)",
                "desktop": "Desktop       (Electron)",
            }.get(svc.name, svc.name)
            _log(f"==> {index}/{total} {title}")
            svc.start()
            if svc.ready_port is not None and not self._stop_event.is_set():
                if not _wait_port(svc.ready_port, svc.name):
                    _log(
                        f"⚠ [{svc.name}] 首次启动未在时限内就绪，监督器将继续运行并自动重试"
                    )

        _log("")
        _log("联调已启动。任一服务热更新/崩溃不会终止其他服务。")
        if sys.platform == "win32":
            _log(
                "停止方式：2 秒内连按两次 Ctrl+C（热重载可能误发一次中断，故需确认）；"
                "或 Ctrl+Break。"
            )
        else:
            _log("按 Ctrl+C 停止全部。")
        _log("")

        try:
            while not self._stop_event.is_set():
                for svc in self.services:
                    if self._stop_event.is_set():
                        break
                    if svc.claim_restart():
                        threading.Thread(
                            target=svc.maybe_restart,
                            name=f"restart-{svc.name}",
                            daemon=True,
                        ).start()
                self._stop_event.wait(1.0)
        finally:
            self._shutdown_all()
        return 0

    def _request_stop(self, reason: str) -> None:
        if self._stop_event.is_set():
            return
        _log(f"\n==> {reason}")
        self._stop_event.set()

    def _on_signal_force(self, signum: int, _frame: object) -> None:
        self._request_stop(f"收到信号 {signum}，正在停止全部服务 ...")

    def _on_signal(self, signum: int, _frame: object) -> None:
        if self._stop_event.is_set():
            return
        # Windows SIGINT：过滤 uvicorn 热重载对控制台的 CTRL_C 广播
        if sys.platform == "win32" and signum == signal.SIGINT:
            now = time.monotonic()
            if now - self._last_sigint_at > self._WIN_SIGINT_CONFIRM_SEC:
                self._last_sigint_at = now
                _log(
                    "提示: 收到中断信号（常见于 MCP/Agent 热重载广播，并非你按了 Ctrl+C）。"
                    f"{self._WIN_SIGINT_CONFIRM_SEC:.0f} 秒内再按一次 Ctrl+C 才会停止全部。"
                )
                return
        self._request_stop(f"收到信号 {signum}，正在停止全部服务 ...")

    def _shutdown_all(self) -> None:
        for svc in reversed(self.services):
            svc.stop()


def _ensure_uv_sync(uv: str, cwd: Path) -> None:
    """
    ``uv run --no-sync`` 不会安装/更新本地 path 依赖。
    联调前先 ``uv sync --inexact``，确保 ``contracts`` 可导入，且不卸载已装的 dev 额外包。
    """
    _log(f"  · 同步依赖: {cwd.name}")
    completed = subprocess.run(
        [uv, "sync", "--inexact"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env=_child_env(),
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        _log(f"错误：{cwd.name} uv sync 失败\n{detail}", file=sys.stderr)
        raise SystemExit(1)
    # 快速校验共享契约包
    probe = subprocess.run(
        [uv, "run", "--no-sync", "python", "-c", "import contracts"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env=_child_env(),
    )
    if probe.returncode != 0:
        err = (probe.stderr or probe.stdout or "").strip()
        _log(f"错误：{cwd.name} 无法 import contracts\n{err}", file=sys.stderr)
        raise SystemExit(1)


def main() -> int:
    _configure_stdio_utf8()
    os.environ.setdefault("AGENT_RELOAD", "1")
    os.environ.setdefault("MCP_RELOAD", "1")
    os.environ.setdefault(
        "ELECTRON_MIRROR",
        "https://npmmirror.com/mirrors/electron/",
    )
    # 监督器自身也用 UTF-8
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    uv = _which("uv")
    pnpm = _which("pnpm")

    _log(
        f"热重载: MCP_RELOAD={os.environ.get('MCP_RELOAD')}  "
        f"AGENT_RELOAD={os.environ.get('AGENT_RELOAD')}"
    )

    mcp_cwd = ROOT / "services" / "platform-mcp-server"
    agent_cwd = ROOT / "services" / "platform-agent-service"
    # 必须先 sync：否则 --no-sync 启动会 ModuleNotFoundError: contracts
    _ensure_uv_sync(uv, mcp_cwd)
    _ensure_uv_sync(uv, agent_cwd)

    services = [
        Service(
            name="mcp",
            cwd=mcp_cwd,
            # --no-sync：避免每次热启改写 Scripts；contracts 已在上方 sync
            command=[uv, "run", "--no-sync", "python", "-m", "platform_mcp"],
            ready_port=8010,
        ),
        Service(
            name="agent",
            cwd=agent_cwd,
            # 不用 `uv run agent`（会刷新 Scripts/agent.exe，易触发 os error 32）
            command=[uv, "run", "--no-sync", "python", "-m", "app.dev"],
            ready_port=8008,
        ),
        Service(
            name="desktop",
            cwd=ROOT,
            command=[pnpm, "--filter", "@ims/desktop", "dev"],
            ready_port=None,
        ),
    ]
    return Supervisor(services).run()


if __name__ == "__main__":
    raise SystemExit(main())
