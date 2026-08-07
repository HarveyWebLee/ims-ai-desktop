"""pytest 启动时注入 contracts 运行时钩子（与 platform_mcp.config 导入路径对齐）。"""

from __future__ import annotations


def pytest_configure() -> None:
    # 副作用：bind_shared_data_dir(platform_mcp/data) + bind_settings
    import platform_mcp.config  # noqa: F401
    from contracts.device_action_catalog import load_device_action_catalog

    # 防止收集阶段此前已空载 catalog 导致 lru_cache 脏读
    load_device_action_catalog.cache_clear()
