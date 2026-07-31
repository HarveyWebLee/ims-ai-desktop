# 08 — 本地开发指南

## 1. 环境要求

| 项     | 要求                                        |
| ------ | ------------------------------------------- |
| Node   | `>=20`（根 `package.json` `engines`）       |
| 包管理 | **pnpm** `9.15.0`（`packageManager` 字段）  |
| Python | **3.14.4**（Agent / MCP `requires-python`） |
| uv     | Agent、MCP 依赖安装与脚本入口               |
| Docker | 可选；Postgres / Qdrant / Redis             |

## 2. 一键依赖

```bash
bash scripts/up.sh
# 或：
docker compose -f deploy/docker-compose.yml up -d
```

| 服务     | 宿主机端口 | 说明                                                      |
| -------- | ---------- | --------------------------------------------------------- |
| Postgres | **16543**  | `postgresql://agent:agent@127.0.0.1:16543/platform_agent` |
| Qdrant   | **16333**  | REST / Dashboard；gRPC 另映射 **16334**                   |
| Redis    | **13386**  | `redis://127.0.0.1:13386/0`                               |

Compose 定义：[`deploy/docker-compose.yml`](../../deploy/docker-compose.yml)。

## 3. 启动

一键（MCP → Agent → Desktop）：

```bash
bash scripts/all.sh
```

或分终端：

| 服务         | 命令                      | 端口 / 形态 |
| ------------ | ------------------------- | ----------- |
| Platform MCP | `bash scripts/mcp.sh`     | **8010**    |
| Agent        | `bash scripts/agent.sh`   | **8008**    |
| 桌面端       | `bash scripts/desktop.sh` | Electron    |

首次安装：

```bash
pnpm install
cd services/platform-mcp-server && uv sync --extra dev
cd ../platform-agent-service && uv sync --extra dev
```

环境变量（从示例复制后按环境修改，**勿提交 `.env`**）：

| 路径                                   | 示例文件       |
| -------------------------------------- | -------------- |
| `services/platform-agent-service/.env` | `.env.example` |
| `services/platform-mcp-server/.env`    | `.env.example` |
| `apps/desktop/.env`                    | `.env.example` |

`pnpm install` 会通过 `prepare` 安装 Husky 钩子。

## 4. 知识库

```bash
cd services/platform-agent-service
uv run kb --dir ../../prj-docs
uv run kb --search "告警确认"
uv run kb --count
```

或根目录：`bash scripts/kb.sh --dir e:/WORK/CODE/ims-ai-desktop/prj-docs`

详见 [`05-qdrant-rag.md`](./05-qdrant-rag.md)。

## 5. 环境变量（摘要）

完整键以各服务 `.env.example` 为准；此处仅列联调常用项。

### services/platform-mcp-server/.env

```bash
PORT=8010
PLATFORM_API_BASE=http://127.0.0.1:18001/api/app
```

### services/platform-agent-service/.env

```bash
PORT=8008
PLATFORM_MCP_URL=http://127.0.0.1:8010/mcp
AGENT_MCP_REQUIRED=true
PLATFORM_API_BASE=http://127.0.0.1:18001/api/app
QDRANT_URL=http://127.0.0.1:16333
QDRANT_COLLECTION=platform_knowledge
DASHSCOPE_API_KEY=...
DEEPSEEK_API_KEY=...
POSTGRES_DSN=postgresql://agent:agent@127.0.0.1:16543/platform_agent
REDIS_URL=redis://127.0.0.1:13386/0
AGENT_INTENT_AI_FIRST=true
```

> **`AGENT_INTENT_AI_FIRST`（默认 true）**：`classify` 恒走 `react`，旁路 `chat_direct` / `device_gate` / `plan_confirm`。需完整父图门控时设为 `false`。详见 [`03-agent-runtime.md`](./03-agent-runtime.md) §2。

平台达梦（只读）与实体同步变量见 [`09-platform-db-readonly.md`](./09-platform-db-readonly.md)。

### apps/desktop/.env

```bash
AGENT_SERVICE_URL=http://127.0.0.1:8008
PLATFORM_API_BASE=http://192.168.x.x:18001/api/app
ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/
```

Agent Gateway：`http://127.0.0.1:8008/mcp`

## 6. 代码质量与提交门禁

根目录统一入口（与 [`.husky/pre-commit`](../../.husky/pre-commit) 一致）：

```bash
# 格式化：文档 Prettier + 桌面 Prettier + Agent fix + MCP fix
pnpm format

# 检查：文档 Prettier check + 桌面 check + Agent all + MCP all
pnpm check
```

| 脚本                                          | 实际命令概要                                          |
| --------------------------------------------- | ----------------------------------------------------- |
| `pnpm format:docs` / `check:docs`             | Prettier 对 `**/*.{md,mdc,json,yml,yaml}`             |
| `pnpm --filter @ims/desktop format` / `check` | 桌面 Prettier + ESLint + `tsc --noEmit`               |
| `pnpm format:agent` / `check:agent`           | `uv run … python -m app.quality fix` / `all`          |
| `pnpm format:mcp` / `check:mcp`               | `uv run … python -m platform_mcp.quality fix` / `all` |

提交前钩子顺序：

1. `pnpm format`
2. 若有未暂存的格式化改动 → 阻止提交（需 `git add` 后重试）
3. `pnpm check` 全部通过才允许提交

### 分服务入口（等价）

| 服务   | 写回修复                                     | 全量门禁                                       |
| ------ | -------------------------------------------- | ---------------------------------------------- |
| Agent  | `uv run check fix`                           | `uv run check all`                             |
|        | 或 `uv run python -m app.quality …`          | （含 format --check、lint、typecheck、pytest） |
| MCP    | `uv run mcp-check fix`                       | `uv run mcp-check all`                         |
|        | 或 `uv run python -m platform_mcp.quality …` | （format --check、lint、typecheck）            |
| 桌面端 | `pnpm --filter @ims/desktop format`          | `pnpm --filter @ims/desktop check`             |

Agent 子命令：`format` / `lint` / `typecheck` / `test` / `fix` / `all`（`pyproject.toml` → `check = app.quality:main`）。

catalog 导出：

```bash
cd services/platform-agent-service && python scripts/export_catalog.py
```

手工验收：[`../desktop-m1-acceptance.md`](../desktop-m1-acceptance.md)。LangGraph / MCP API：用 MCP `docs-langchain` 核对。

## 7. IDE / Cursor 配置

仓库已提供 [`.vscode/`](../../.vscode/)（Cursor 共用）：

| 文件              | 作用                                                                                                                                       |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `extensions.json` | 推荐：Cursor Pyright、Python、Ruff、Prettier、ESLint；**不推荐** Pylance                                                                   |
| `settings.json`   | Python Language Server = None；`cursorpyright` basic + `extraPaths` 指向两服务；Ruff / Prettier 保存格式化；ESLint 工作目录 `apps/desktop` |
| `tasks.json`      | 运行任务：`mcp:*`、`agent:fix` / `agent:all`、`desktop:check`（默认测试任务）                                                              |

Agent / MCP 的 Ruff、basedpyright 规则以**各自** `pyproject.toml` 为准；IDE 的 `cursorpyright` 与命令行 `basedpyright` 均使用 **basic** 模式对齐。

若 `uv run check` / `mcp-check` 因正在运行的 `uv run agent` / `mcp` 锁住环境，可先停进程，或临时用 `.venv` 内 `python -m app.quality` / `python -m platform_mcp.quality`。
