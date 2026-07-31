# 01 — 系统上下文与部署

## 1. 组件图

```text
┌─────────────────┐     SSE      ┌──────────────────────────┐
│ Electron Desktop│─────────────▶│ platform-agent-service   │
│ apps/desktop    │◀─────────────│  :8008  /api/agent/*     │
│ AiAssistant     │   events     │  :8008  /mcp (Gateway)   │
└─────────────────┘              │  LangGraph + MCP Client  │
                                 │  Qdrant RAG 层           │
                                 └───────────┬──────────────┘
                                             │ MCP (HTTP)
                                             ▼
                                 ┌──────────────────────────┐
                                 │ platform-mcp-server      │
                                 │  :8010  /mcp             │
                                 │  告警/设备/导出/导航…    │
                                 └───────────┬──────────────┘
                                             │ HTTP + JWT
                                             ▼
                                 ┌──────────────────────────┐
                                 │ 平台业务 API             │
                                 │  PLATFORM_API_BASE       │
                                 └───────────┬──────────────┘
                                             │ （平台服务读写）
                                             ▼
                                 ┌──────────────────────────┐
                                 │ 平台业务库（达梦）         │
                                 │ 智能化侧：只读 SELECT     │
                                 └──────────────────────────┘
```

数据面：Postgres(checkpointer) :16543 | Qdrant :16333 | Redis :13386  
平台业务库：达梦（智能化进程仅允许查询，见 [09-platform-db-readonly.md](./09-platform-db-readonly.md)）

## 2. 进程与端口

| 进程         | 目录                               | 端口       | 职责                                                    |
| ------------ | ---------------------------------- | ---------- | ------------------------------------------------------- |
| 桌面端       | `apps/desktop/`                    | Electron   | 登录、SSE、HITL、Plan 步骤条                            |
| Agent 服务   | `services/platform-agent-service/` | **8008**   | SSE、LangGraph、MCP Client、Gateway、RAG                |
| 共享契约     | `services/platform-contracts/`     | —          | 包名 `contracts`（HITL/preflight/catalog；无 MCP 执行） |
| Platform MCP | `services/platform-mcp-server/`    | **8010**   | 平台工具 MCP Server（`runtime/tools`）                  |
| Postgres     | docker compose                     | 16543→5432 | Checkpointer / 会话                                     |
| Qdrant       | docker compose                     | 16333→6333 | 向量检索                                                |
| Redis        | docker compose                     | 13386→6379 | 缓存                                                    |

## 3. 目录结构

```text
ims-ai-desktop/
├── docs/architecture/
├── packages/
│   ├── agent-core/
│   ├── shared-types/
│   └── desktop-api/
├── services/
│   ├── platform-contracts/      # 目录；Python 包名 contracts
│   ├── platform-mcp-server/     # Python 3.14.4，uv / mcp-check
│   └── platform-agent-service/  # Python 3.14.4，uv / check
├── deploy/
│   └── docker-compose.yml       # Postgres / Qdrant / Redis
├── apps/
│   └── desktop/                 # Electron，pnpm @ims/desktop
├── .vscode/                     # 扩展推荐、settings、tasks
├── .husky/                      # pre-commit → pnpm format + check
├── prj-docs/
└── scripts/
```

## 4. 网络与鉴权

| 链路                         | 鉴权                                           |
| ---------------------------- | ---------------------------------------------- |
| Desktop → Agent `:8008`      | 用户 JWT                                       |
| Agent → Platform MCP `:8010` | 转发同一 JWT                                   |
| Platform MCP → 平台 API      | 同一 JWT                                       |
| Cursor → Agent `/mcp`        | API Key 或 JWT（见 `04-agent-mcp-gateway.md`） |

## 5. 环境变量（摘要）

见 [08-dev-guide.md](./08-dev-guide.md)。关键项：

- `PLATFORM_API_BASE` — 平台业务 API
- `PLATFORM_MCP_URL` — 默认 `http://127.0.0.1:8010/mcp`
- `AGENT_SERVICE_URL` — 桌面端开发代理，默认 `http://127.0.0.1:8008`
- `QDRANT_URL` — 默认 `http://127.0.0.1:16333`
- `DASHSCOPE_API_KEY` / `DEEPSEEK_API_KEY`
