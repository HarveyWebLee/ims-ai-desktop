# ims-ai-desktop

综合信息平台 **AI 智能化桌面端**：Electron + Agent Runtime + Platform MCP。

## 目录

- `apps/desktop`：Electron 桌面聊天端（聊天 + Plan 步骤条 + HITL）
- `services/platform-agent-service`：Agent Runtime（:8008）
- `services/platform-mcp-server`：Platform MCP（:8010）
- `packages/*`：共享协议与 catalog（`agent-core` / `shared-types` / `desktop-api`）
- `docs` / `prj-docs` / `scripts`

## 首期能力（M1）

- 桌面端内嵌登录（平台 `/api/app/auth/login`）
- SSE 对话、会话历史、中止、基础 HITL
- Plan 步骤条展示
- 无宿主页面时，`navigate` 等 `client_action` 跳过并降级提示

## 开发环境

1. 复制并配置环境变量：
   - `services/platform-agent-service/.env`
   - `services/platform-mcp-server/.env`
   - `apps/desktop/.env`（可从 `.env.example` 复制）
2. 安装依赖：

```bash
pnpm install
```

3. 启动基础设施：

```bash
bash scripts/up.sh
```

4. 一键联调：

```bash
bash scripts/all.sh
```

或分端启动：

```bash
bash scripts/mcp.sh
bash scripts/agent.sh
bash scripts/desktop.sh
```

## 常用命令

```bash
pnpm --filter @ims/desktop dev
pnpm --filter @ims/desktop build
bash scripts/kb.sh --dir e:/WORK/CODE/ims-ai-desktop/prj-docs
```

## 代码质量与提交门禁

```bash
# 统一格式化（文档 + 前端 + 两个 Python 服务）
pnpm format

# 统一检查（Prettier check + 桌面 ESLint/tsc + Agent/MCP quality all）
pnpm check
```

| 分项  | 命令                                                                     |
| ----- | ------------------------------------------------------------------------ |
| 文档  | `pnpm format:docs` / `pnpm check:docs`                                   |
| 桌面  | `pnpm --filter @ims/desktop format` / `check`                            |
| Agent | `pnpm format:agent` / `pnpm check:agent`（`python -m app.quality`）      |
| MCP   | `pnpm format:mcp` / `pnpm check:mcp`（`python -m platform_mcp.quality`） |

提交前会自动执行 `.husky/pre-commit`：

1. 先执行 `pnpm format`
2. 若格式化改动了文件，则阻止提交（提示先 `git add`）
3. 再执行 `pnpm check`，全部通过才允许提交

首次启用（或新 clone 后）执行 `pnpm install`（`prepare` 安装 Husky）。完整说明见 [`docs/architecture/08-dev-guide.md`](docs/architecture/08-dev-guide.md) §6–7。

## IDE / Cursor

根目录 [`.vscode/`](.vscode/)：

- 推荐扩展：Cursor Pyright、Python、Ruff、Prettier、ESLint（勿用 Pylance）
- 保存时：Python → Ruff；TS/TSX/JSON → Prettier
- 任务：`mcp:*`、`agent:fix` / `agent:all`、`desktop:check`

Python：**3.14.4**（Agent / MCP）。

## 说明

- 平台业务库（达梦）只读，业务写入仅通过平台 API。
- 登录 token 仅本地存储，不提交到仓库。
- 维护入口：[`AGENTS.md`](AGENTS.md)；架构：[`docs/architecture/`](docs/architecture/00-overview.md)；验收：[`docs/desktop-m1-acceptance.md`](docs/desktop-m1-acceptance.md)。
- Cursor：`.cursor/rules`、`.cursor/skills`、`.cursor/hooks.json`、`.cursor/mcp.json`（说明见 `.cursor/MCP_USAGE.md`）。
