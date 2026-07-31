# platform-agent-service

综合信息平台 **AI Agent 后端服务**，基于 **Python 3.14.4 + FastAPI + LangGraph**。

## 快速启动

```bash
# 安装依赖（推荐 uv；含开发工具：ruff / basedpyright / pytest）
uv sync --extra dev
# 或 pip install -e ".[dev]"

# 配置环境变量
cp .env.example .env

# 从 monorepo packages/ 同步 catalog JSON
python scripts/export_catalog.py

# 启动（默认端口见 .env 的 PORT，建议 8008）
uv run agent
```

## 代码质量（本地）

配置集中在 `pyproject.toml`（Ruff 格式化/Lint、basedpyright、pytest）。本服务入口：

```bash
uv sync --extra dev

uv run check format      # Ruff 格式化（写回）
uv run check lint        # Ruff Lint（只读）
uv run check typecheck   # basedpyright（basic，与 IDE 对齐）
uv run check test        # pytest；可透传：uv run check test -k hitl -q
uv run check fix         # format + lint --fix
uv run check all         # 门禁：format --check + lint + typecheck + test
```

等价模块调用（与 monorepo 根 `pnpm check:agent` / VS Code 任务一致）：

```bash
uv run --extra dev python -m app.quality all
```

若 `uv run check` 因正在运行的 `agent` 进程锁住脚本安装失败，可先停掉进程，再执行 `uv sync --extra dev`；临时也可用：

```bash
.venv/Scripts/python -m app.quality lint
```

**Monorepo 提交门禁**：根目录已接 Husky（`.husky/pre-commit`）→ `pnpm format` 后 `pnpm check`（含本服务 `check:agent`）。详见 [`docs/architecture/08-dev-guide.md`](../../docs/architecture/08-dev-guide.md) §6–7。

编辑器：安装仓库推荐扩展（Ruff + Cursor Pyright，见根 `.vscode/extensions.json`）后，Python 保存时自动格式化；「运行任务」可用 `agent:fix` / `agent:all`。

## Postgres 持久化（Checkpointer）

LangGraph 线程状态与会话列表可持久化到 Postgres：

```bash
# 1. 启动依赖（Postgres + Qdrant + Redis）
# 在仓库根目录：
bash scripts/up.sh
# 或：docker compose -f deploy/docker-compose.yml up -d

# 2. .env 配置连接串
# POSTGRES_DSN=postgresql://agent:agent@127.0.0.1:16543/platform_agent

# 3. 安装依赖并启动 Agent
uv sync
uv run agent
```

未配置 `POSTGRES_DSN` 时自动回退 **InMemorySaver**（重启后会话丢失）。配置后图状态使用 **AsyncPostgresSaver**。

`GET /health` 返回 `persistence: postgres|memory` 可确认模式。

须在 `.env` 中配置 `DEEPSEEK_API_KEY` 或 `DASHSCOPE_API_KEY`；未配置时对话 / 续跑会直接返回明确错误，不再提供 Mock 回复。

## Qdrant 向量库（语义检索 / RAG）

Compose 已包含 Qdrant，宿主机 REST 端口 **16333**（Dashboard：<http://127.0.0.1:16333/dashboard>）。

```bash
# .env
QDRANT_URL=http://127.0.0.1:16333
DASHSCOPE_API_KEY=...   # Embedding 共用

# 将文档入库
uv run kb --dir ../../prj-docs --search "告警确认"
```

完整说明：[`docs/architecture/05-qdrant-rag.md`](../../docs/architecture/05-qdrant-rag.md)。

`GET /health` 的 `qdrant` 字段可确认连通性。

## MCP 双层（v2）

1. 启动 Platform MCP：`cd ../platform-mcp-server && uv run mcp`（`:8010/mcp`）
2. 本服务：`uv run agent`，配置 `PLATFORM_MCP_URL=http://127.0.0.1:8010/mcp`
3. Agent Gateway：`GET /mcp/health`、`POST /mcp/tools/list`、`POST /mcp/tools/call`

架构基准：[`docs/architecture/00-overview.md`](../../docs/architecture/00-overview.md)。

## 跨轮次 / HITL 问题排查日志

当「取消导出后下一轮仍显示导出 Plan」等问题时，可开启结构化 `[AgentTrace]` 日志：

```bash
# platform-agent-service/.env
AGENT_DEBUG_TRACE=true
```

重启 Agent 后复现问题，终端或日志文件中过滤：

```bash
grep AgentTrace
```

关键事件：

| 事件                                            | 含义                                                    |
| ----------------------------------------------- | ------------------------------------------------------- |
| `flow.api.chat` / `flow.api.resume`             | API 入口：消息、model、路径                             |
| `flow.context.assembled`                        | 组装后的 `llm_user_message`（LLM 实际看到的用户侧输入） |
| `flow.route.decision`                           | mock / chat_direct / llm 路由                           |
| `flow.plan.route_eval`                          | 规则层 Plan 模式 react / explicit_plan                  |
| `flow.ai.llm_plan.request/response`             | LLM 结构化生成多步 Plan                                 |
| `flow.ai.llm_plan_params.request/response`      | LLM 抽取 Plan 工具参数                                  |
| `flow.plan.resolved`                            | 最终 Plan 来源 llm / rule                               |
| `flow.checkpoint.before_chat/before_resume`     | **checkpoint 最近消息摘要（含 tool_calls）**            |
| `flow.ai.react.stream_start`                    | ReAct 图开始：HumanMessage 或 Command                   |
| `flow.ai.llm_tool_call/llm_tool_result`         | 图内 LLM 决策的工具与结果                               |
| `flow.tool.preflight` / `flow.tool.invoke_done` | Platform MCP 工具校验与执行结果（非图外旁路）           |
| `flow.ai.hitl_interrupt`                        | 图内 interrupt 载荷                                     |
| `flow.sse.emit` / `flow.sse.text_delta`         | 下发 SSE 摘要                                           |
| `chat.orchestration_clear`                      | 新消息清编排暂存                                        |
| `checkpoint.abandon_*`                          | 清除 stale 图内 interrupt                               |
| `resume.reject` / `resume.path_*`               | HITL 续跑分支                                           |

复现后请复制**整段** `[AgentTrace]` 日志（含 `flow.checkpoint.*`）以便分析 AI 决策链。

## 目录

- `app/` — FastAPI 应用、LangGraph Agent、工具、提示词
- `scripts/export_catalog.py` — 从 `../../packages/` 导出 catalog JSON；从 `swaggerApi.json` 导出 API 索引
- `app/data/swaggerApi.json` — 平台全量 OpenAPI（YApi 导出），Agent 工具开发参考
- `app/data/platform_api_index.json` — 轻量 API 索引（由 export 脚本生成）
- `tests/` — 单元测试

## 共享包

TypeScript 契约包位于 monorepo **`packages/`**（相对本服务为 `../../packages/`）：

| 包                  | 路径                           |
| ------------------- | ------------------------------ |
| `@ims/agent-core`   | `../../packages/agent-core/`   |
| `@ims/shared-types` | `../../packages/shared-types/` |
| `@ims/desktop-api`  | `../../packages/desktop-api/`  |

Python **不直接运行 TS**；修改 catalog 或 swagger 后须执行 `python scripts/export_catalog.py`。

## 平台 OpenAPI 与 Agent 工具开发

`app/data/swaggerApi.json` 为平台接口的 OpenAPI 3.0 导出（约 1500+ path）。**不应**把全部接口直接暴露给 LLM，而应用于：

| 用途                | 说明                                                                                                   |
| ------------------- | ------------------------------------------------------------------------------------------------------ |
| **新 @tool 脚手架** | 查 path、summary、request 字段，避免手写错参                                                           |
| **契约交叉校验**    | `export_api_index.py` 会校验现有工具（如 `query_alarms` → `/alarm/getAlarmList`）是否在 swagger 中存在 |
| **Prompt 域摘要**   | `platform_api_catalog.format_tag_summary_for_prompt('alarmManagementApi')` 按 tag 注入 API 参考        |
| **Preflight 校验**  | `validate_request_fields(path, payload)` 对照必填项（Agent 父图 / MCP 包装调用前）                     |
| **API 检索**        | `search_apis('exportAlarm')` 供研发或调试                                                              |

```bash
# 从 swaggerApi.json 生成轻量索引（已并入 export_catalog.py）
python scripts/export_api_index.py
# 输出：app/data/platform_api_index.json（~1.3MB）
#       app/data/platform_api_tags.json
```

Python 读取：`app/services/platform_api_catalog.py`。

**推荐做法**：继续以 `packages/agent-core/tool-catalog.ts` 为 **Agent 可见工具** 的唯一白名单；swagger 作为 **实现层参考**，按业务域逐步封装为高阶 @tool（如现有 `query_alarms`），而非 1526 个裸 API 全部注册给模型。

## API

| 接口                                | 说明                |
| ----------------------------------- | ------------------- |
| `GET /api/agent/models`             | 模型列表            |
| `GET /api/agent/sessions`           | 会话列表            |
| `GET /api/agent/threads/{id}/state` | 线程历史            |
| `POST /api/agent/chat`              | SSE 对话            |
| `POST /api/agent/resume`            | HITL 恢复           |
| `POST /api/agent/transcribe`        | 语音转写（Phase 2） |

JSON 响应统一 `{ code, data, message }`，`code === 0` 为成功。

## 文档

- 本服务文档索引：[`docs/README.md`](docs/README.md)
- **代码学习阅读路径**：[`docs/code-reading-guide.md`](docs/code-reading-guide.md)
- Qdrant 部署：[`docs/qdrant-deployment.md`](docs/qdrant-deployment.md)
- Monorepo 说明：`../../AGENTS.md`
- 架构基准：`../../docs/architecture/00-overview.md`
- Agent 规范：`../../.cursor/rules/ai-agent-dev.mdc`
