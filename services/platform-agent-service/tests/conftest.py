"""pytest 启动时注入 contracts 运行时钩子（与 app.config 导入路径对齐）。"""

from __future__ import annotations


def pytest_configure() -> None:
    from app.contracts_runtime import wire_contracts_runtime

    wire_contracts_runtime()
