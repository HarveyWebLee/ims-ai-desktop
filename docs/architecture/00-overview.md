# 00 — 架构总览（开发基准）

> **本文档集是本仓编码唯一依据。**

## 1. 目标

综合信息平台 AI 智能化桌面端采用：

1. **双层 MCP**：平台业务工具只实现在 Platform MCP Server；Agent 仅通过 MCP Client 发现与调用工具。
2. **Agent MCP Gateway**：Agent 对外暴露 `/mcp`，供 Cursor 等 MCP Client 调用。
3. **SSE 对话 UI**：`apps/desktop` AiAssistant 走 `/api/agent/chat`、`/resume`；MCP **不**替代聊天流协议。
4. **Qdrant**：知识库 RAG 默认注入每轮上下文；并提供 `retrieve_knowledge` 工具。
5. **官方 LangGraph 模型**：父 StateGraph + `create_agent` 节点；HITL 仅 `interrupt` / `Command(resume)` / checkpointer；异步 `astream_events(v3)`。

## 2. 非目标

- 用 MCP 替换桌面端 SSE 聊天
- Agent 内业务 `@tool` 与 MCP 双轨
- 图外 `pending_plan` / `pending_tool_hitl` 第二 HITL 状态机
- 手写 ReAct StateGraph 与 `create_agent` 双轨
- Platform MCP 依赖 `langgraph`
- M1 交付 BPMN 编排画布 UI

## 3. 原则

| 原则     | 说明                                                         |
| -------- | ------------------------------------------------------------ |
| 契约单一 | SSE / HITL 以 `06-contracts.md` 为准                         |
| 验收对齐 | [`../desktop-m1-acceptance.md`](../desktop-m1-acceptance.md) |
| 达梦只读 | 智能化侧仅 SELECT，见 `09`                                   |

## 4. 与验收的关系

| 能力域                 | 落点                                                          |
| ---------------------- | ------------------------------------------------------------- |
| 健康检查 / 会话 / 历史 | Agent SSE API + AsyncPostgres                                 |
| 告警查询 / 导出 / 批量 | Platform MCP → 平台 API                                       |
| Client Tool            | Platform MCP `client_action(s)` → SSE；桌面端可跳过降级       |
| HITL                   | 父图 / 工具包装器 `interrupt` + `/resume` → `Command`         |
| Plan                   | 父图节点 + 桌面步骤条（默认 AI-first 下门控旁路，见 `03`）    |
| 纯对话短路             | 父图 `chat_direct`（仅 `AGENT_INTENT_AI_FIRST=false` 时生效） |
| 知识检索               | Qdrant + `retrieve_knowledge`                                 |

### 默认意图路由（AI-first）

环境变量 **`AGENT_INTENT_AI_FIRST` 默认 `true`**：`classify` **恒路由 `react`**（`create_agent` + MCP 工具），旁路 `chat_direct` / `device_gate` / `plan_confirm`。完整父图拓扑仅在设为 `false` 时启用。HITL 仍走工具包装器 `hitl_required` → `interrupt`。详见 [`03-agent-runtime.md`](./03-agent-runtime.md) §2。

## 5. 文档索引

| 编号 | 文件                                                       | 主题                             |
| ---- | ---------------------------------------------------------- | -------------------------------- |
| 01   | [01-system-context.md](./01-system-context.md)             | 组件、端口、部署                 |
| 02   | [02-mcp-platform-server.md](./02-mcp-platform-server.md)   | Platform MCP Server              |
| 03   | [03-agent-runtime.md](./03-agent-runtime.md)               | 父图 / SSE / HITL / Plan         |
| 04   | [04-agent-mcp-gateway.md](./04-agent-mcp-gateway.md)       | 对外 Agent MCP                   |
| 05   | [05-qdrant-rag.md](./05-qdrant-rag.md)                     | Qdrant RAG                       |
| 06   | [06-contracts.md](./06-contracts.md)                       | packages 契约                    |
| 07   | [07-conversation-flow.md](./07-conversation-flow.md)       | 用户需求→回复 / 多轮 / HITL 时序 |
| 08   | [08-dev-guide.md](./08-dev-guide.md)                       | 本地开发 / 质量门禁 / IDE        |
| 09   | [09-platform-db-readonly.md](./09-platform-db-readonly.md) | 平台达梦只读                     |
| 10   | [10-voice-asr.md](./10-voice-asr.md)                       | 语音转写 / 按段纠错 / 标注       |
| 11   | [11-voiceprint.md](./11-voiceprint.md)                     | 生产级声纹识别（1:1 / 1:N）      |
| —    | [../roadmap/README.md](../roadmap/README.md)               | 迭代设想（非编码唯一依据）       |

## 6. 技术选型（固定）

| 层                | 选型                                                                                                          |
| ----------------- | ------------------------------------------------------------------------------------------------------------- |
| Platform MCP      | Python `mcp` + Streamable HTTP（FastMCP）；**无 langgraph**                                                   |
| Agent Client      | `langchain-mcp-adapters` → `MultiServerMCPClient`                                                             |
| Agent 图          | 父 `StateGraph` + 节点内 `create_agent`                                                                       |
| HITL              | `interrupt()` + `Command(resume=...)` + checkpointer                                                          |
| 流                | `astream_events(version="v3")`                                                                                |
| 对话 API          | FastAPI SSE，端口 **8008**                                                                                    |
| Platform MCP 进程 | 端口 **8010**，路径 `/mcp`                                                                                    |
| Checkpointer      | `AsyncPostgresSaver`                                                                                          |
| 向量库            | Qdrant，宿主机 REST `http://127.0.0.1:16333`                                                                  |
| Embedding         | DashScope，维度 **1024**                                                                                      |
| 契约源            | TS：`packages/agent-core`、`packages/shared-types`；Python：`services/platform-contracts`（包名 `contracts`） |
| 桌面端            | `apps/desktop`（Electron）                                                                                    |
| 平台业务库        | 达梦；智能化侧 **仅 SELECT**（见 [`09`](./09-platform-db-readonly.md)）                                       |
