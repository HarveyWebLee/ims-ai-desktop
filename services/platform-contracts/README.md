# platform-contracts

Agent / Platform MCP **共享** Python 运行时契约（包名 **`contracts`**）。

- 目录：`services/platform-contracts/`
- import：`from contracts import ...`（或 `from contracts.hitl import ...`）
- **无** LangChain / FastMCP / LangGraph
- **禁止** `import app` / `import platform_mcp`；不得硬编码兄弟工程路径；宿主能力经 `contracts.runtime_bind` 注入
- 工具 `@tool` 执行面仍在 [`../platform-mcp-server`](../platform-mcp-server)

架构说明：[`docs/architecture/06-contracts.md`](../../docs/architecture/06-contracts.md) §1.1。

```bash
uv sync --extra dev

# 写回：格式化 + lint --fix
uv run check fix
# 或：uv run python -m contracts.quality fix

# 只读门禁：format --check + lint + typecheck + test
uv run check all
```

根目录：`pnpm format:contracts` / `pnpm check:contracts`（已纳入 `pnpm format` / `pnpm check`）。
