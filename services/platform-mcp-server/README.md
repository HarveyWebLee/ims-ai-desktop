# Platform MCP Server

架构：[`docs/architecture/02-mcp-platform-server.md`](../../docs/architecture/02-mcp-platform-server.md)

要求：**Python 3.14.4**（与 Agent 对齐）。

**边界**：本进程仅 `platform_mcp.runtime.tools` 执行面；HITL / preflight / catalog / 平台客户端等共享逻辑在邻仓 [`../platform-contracts`](../platform-contracts)（import `contracts`）。

## 启动

```bash
# editable 安装 ../platform-contracts
uv sync --extra dev
uv run mcp
# 等价：uv run platform-mcp
# 等价：uv run python -m platform_mcp
# → http://127.0.0.1:8010/mcp
```

联调也可从仓库根：`bash scripts/mcp.sh`。

工具单测：`uv run pytest tests`（告警/设备/导出等 handler 测试在本仓 `tests/`）。

## 代码质量

配置在 `pyproject.toml`（Ruff、basedpyright）。本服务入口：

```bash
uv sync --extra dev
uv run mcp-check fix        # 写回：format + lint --fix
uv run mcp-check all        # 门禁：format --check + lint + typecheck
```

等价模块调用（与 monorepo 根 `pnpm check:mcp` / VS Code 任务一致）：

```bash
uv run --extra dev python -m platform_mcp.quality all
```

**Monorepo 提交门禁**：根目录 Husky → `pnpm format` / `pnpm check`（含 `check:mcp`）。详见 [`docs/architecture/08-dev-guide.md`](../../docs/architecture/08-dev-guide.md) §6–7。

编辑器任务：`mcp:format` / `mcp:lint` / `mcp:typecheck` / `mcp:fix` / `mcp:all`（根 `.vscode/tasks.json`）。

## 环境变量

见 `.env.example`（`PORT=8010`、`PLATFORM_API_BASE`）。
