# ims-ai-desktop — AI 智能化桌面端

本目录为 **综合信息平台 AI 智能化桌面端** 的统一维护根（Electron + Agent + MCP）。

> **架构基准（编码唯一依据）**：[`docs/architecture/00-overview.md`](docs/architecture/00-overview.md)  
> 产品说明：[`README.md`](README.md)  
> 手工验收（M1）：[`docs/desktop-m1-acceptance.md`](docs/desktop-m1-acceptance.md)

**约束**：工具只经 Platform MCP；对话 UI 走 SSE；HITL 仅 LangGraph `interrupt` / `Command(resume)`（无图外 pending）；ReAct 仅 `create_agent`。

**M1 范围**：聊天 + Plan 步骤条 + 基础 HITL；不含 BPMN 编排画布。无宿主时 `client_action`（如 navigate）跳过并降级。

---

## 目录结构

```
ims-ai-desktop/
├── AGENTS.md
├── docs/architecture/
├── packages/
│   ├── agent-core/                    # catalog 唯一数据源
│   ├── shared-types/
│   └── desktop-api/
├── services/
│   ├── platform-mcp-server/           # :8010
│   └── platform-agent-service/        # :8008
├── apps/
│   └── desktop/                       # Electron
├── prj-docs/
└── scripts/
```

---

## 子工程职责

| 工程                               | 技术栈                              | 端口     | 职责                         |
| ---------------------------------- | ----------------------------------- | -------- | ---------------------------- |
| `packages/`                        | TypeScript                          | —        | catalog / 协议 / desktop-api |
| `services/platform-mcp-server/`    | Python + MCP                        | **8010** | 平台工具执行面               |
| `services/platform-agent-service/` | FastAPI + StateGraph + create_agent | **8008** | SSE、父图、RAG、Gateway      |
| `apps/desktop/`                    | Electron + React                    | 渲染进程 | 登录、对话、HITL、Plan       |

**约束**：

- Agent / MCP Python 代码不得放入 `apps/desktop/`
- 图内工具只来自 `MultiServerMCPClient.get_tools()` + 本地 `retrieve_knowledge`
- M1 不引入 BPMN 编排 UI
- 包管理：根目录 **pnpm**

---

## 本地联调

见 [`docs/architecture/08-dev-guide.md`](docs/architecture/08-dev-guide.md)。

```bash
bash scripts/up.sh
bash scripts/all.sh
# 分端：scripts/mcp.sh | agent.sh | desktop.sh
# 知识库：bash scripts/kb.sh --dir e:/WORK/CODE/ims-ai-desktop/prj-docs
```

关键环境变量：

```bash
PLATFORM_MCP_URL=http://127.0.0.1:8010/mcp
PLATFORM_API_BASE=http://192.168.x.x:18001/api/app
AGENT_SERVICE_URL=http://127.0.0.1:8008
QDRANT_URL=http://127.0.0.1:16333
REDIS_URL=redis://127.0.0.1:13386/0
DASHSCOPE_API_KEY=...
DEEPSEEK_API_KEY=...
```

环境：Node `>=20` + pnpm `9.15`；Agent / MCP 为 **Python 3.14.4**。

---

## 代码质量

```bash
pnpm format   # 文档 + 桌面 + Agent fix + MCP fix
pnpm check    # 文档 + 桌面 + Agent all + MCP all
```

提交：`.husky/pre-commit` 先 `format` 再 `check`。IDE：`.vscode/`（扩展 / settings / tasks）。分服务入口：`uv run check`、`uv run mcp-check`。详见 [`08-dev-guide.md`](docs/architecture/08-dev-guide.md) §6–7。

---

## 能力分期

| 阶段          | 目标                        | 状态   |
| ------------- | --------------------------- | ------ |
| 架构文档      | `docs/architecture/*`       | ✅     |
| Platform MCP  | `:8010`                     | ✅     |
| Agent Runtime | 父图 + SSE + RAG `:8008`    | ✅     |
| Agent Gateway | `/mcp`                      | ✅     |
| Desktop M1    | Electron 聊天 + Plan + HITL | ✅     |
| BPMN UI       | 编排画布                    | 未纳入 |

**禁止**：图外 `pending_*` HITL、手写 ReAct 外循环与 `create_agent` 双轨。

迭代设想：[`docs/roadmap/README.md`](docs/roadmap/README.md)。

---

## 关联功能完整性

见 [`.cursor/rules/change-integrity.mdc`](.cursor/rules/change-integrity.mdc)、[`.cursor/rules/ai-dev-quality-gates.mdc`](.cursor/rules/ai-dev-quality-gates.mdc)。

典型关联面：桌面 `sendMessage` / `resume` / `reject` / `abort`；后端 `astream_events` + `Command(resume)`；契约 `packages/` 与 SSE。

---

## 开发强制规范

1. LangChain / LangGraph：动手前用 MCP `docs-langchain` 核对 API（[`.cursor/rules/langchain-langgraph-docs-first.mdc`](.cursor/rules/langchain-langgraph-docs-first.mdc)）
2. 架构基准：`docs/architecture/`（`00` / `02` / `03` / `06`）
3. i18n：`aiAssistant.*`（`apps/desktop/src/locales/`）
4. JSON：`{ code, data, message }`，`code === 0` 成功
5. 工具：只经 Platform MCP；catalog 唯一说明书
6. 对称路径：改一条须同步 chat / resume / reject / 新会话
7. 平台达梦只读：仅 `SELECT`；业务写走平台 API（[`09-platform-db-readonly.md`](docs/architecture/09-platform-db-readonly.md)）

详细：[`.cursor/rules/ai-agent-dev.mdc`](.cursor/rules/ai-agent-dev.mdc)。

---

## Cursor 辅助

| 类型   | 路径                                                                 |
| ------ | -------------------------------------------------------------------- |
| Rules  | `.cursor/rules/`                                                     |
| Skills | `.cursor/skills/`                                                    |
| Hooks  | `.cursor/hooks.json` + `.cursor/hooks/`                              |
| MCP    | `.cursor/mcp.json`（[`.cursor/MCP_USAGE.md`](.cursor/MCP_USAGE.md)） |

---

## Git 提交

Angular 规范，**中文 subject**。示例：`feat(桌面端): 补齐 HITL 续跑对称路径`
