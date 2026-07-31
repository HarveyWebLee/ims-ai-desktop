"""uv run mcp 入口（热重载见 MCP_RELOAD / platform_mcp.main）。"""

from __future__ import annotations


def main() -> None:
    from platform_mcp.main import run

    run()


if __name__ == "__main__":
    main()
