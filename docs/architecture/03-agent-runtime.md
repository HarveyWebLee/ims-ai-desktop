# 03 — Agent Runtime

## 1. 职责

`platform-agent-service` 负责：

- FastAPI：`/api/agent/chat`、`/resume`、会话、模型、BPMN、健康检查
- **父 StateGraph**：classify / plan_confirm / device / plan / BPMN / react（唯一运行时入口）
- **ReAct / 纯对话**：官方 `create_agent`（作为父图节点，非第二套编排引擎）
- **MCP Client**：`MultiServerMCPClient.get_tools()` + 本地 `retrieve_knowledge`
- Qdrant RAG 注入（见 05）
- Agent MCP Gateway（见 04）

HTTP 层只做鉴权、构造初始 state / `Command(resume=...)`、把 `astream_events(v3)` 映射为 SSE。**禁止**图外 `pending_plan` / `pending_tool_hitl` 第二状态机。

## 2. 父图拓扑

```text
START → classify
  ├─ chat_direct   → create_agent(tools=[]) → END
  ├─ device_gate   → interrupt(ask_params) → react 或 END
  ├─ plan_confirm  → interrupt(plan_confirm) → plan_execute | bpmn_execute → END
  └─ react         → create_agent(tools=MCP+RAG) → END
```

### 默认：`AGENT_INTENT_AI_FIRST=true`（生产 / `.env.example` 默认）

| 开关               | `classify` 行为                                                         |
| ------------------ | ----------------------------------------------------------------------- |
| **`true`（默认）** | **恒路由 `react`**；旁路 `chat_direct` / `device_gate` / `plan_confirm` |
| `false`            | 启用上图完整门控（寒暄短路、设备缺槽、多步 Plan 确认）                  |

默认 AI-first 下，缺参/确认类 HITL **主要**依赖 MCP 返回 `hitl_required` → 工具包装器 `interrupt`（而非父图 plan/device 门控节点）。健康检查 `feature_flags.agent_intent_ai_first` 可观测当前值。

- `get_agent_topology()` / Trace 必须反映**真实**编译图（`graph.get_graph()`），禁止静态假拓扑。
- 删除手写 ReAct `StateGraph` 双轨与 `AGENT_USE_STATE_GRAPH` 开关。

## 3. 工具绑定

```text
启动
  → MultiServerMCPClient({ platform: { transport: http, url: PLATFORM_MCP_URL } })
  → tools = await client.get_tools()
  → Auth / HITL wrapper（图内 interrupt）
  → (+ retrieve_knowledge)
  → 绑定到 create_agent / 父图 plan·bpmn 节点调用同一套包装工具
```

**禁止**：直绑业务 `@tool` 实现；Platform MCP 不可达时不回退本机工具。

## 4. 流式与持久化

| 项           | 选型                                              |
| ------------ | ------------------------------------------------- |
| 流           | `await graph.astream_events(..., version="v3")`   |
| Checkpointer | `AsyncPostgresSaver`（无 DSN 时 `InMemorySaver`） |
| 节点 IO      | 统一 `ainvoke`                                    |

删除同步 `stream_events` + 工作线程桥。

## 5. SSE 事件契约

事件名（`06-contracts.md` 为权威）：

| 事件                              | 用途                               |
| --------------------------------- | ---------------------------------- |
| `message`                         | 助手增量文本                       |
| `tool_start` / `tool_end`         | 工具起止                           |
| `client_action`                   | 浏览器执行                         |
| `interrupt`                       | HITL（仅来自 `stream.interrupts`） |
| `plan` / `plan_update` / `replan` | 计划                               |
| `trace`                           | 执行轨迹                           |
| `done` / `error`                  | 结束                               |

JSON 非流接口统一 `{ code, data, message }`，`code === 0` 成功。

## 6. HITL（唯一机制）

官方模型：[`interrupt()` + `Command(resume=...)` + checkpointer](https://docs.langchain.com/oss/python/langgraph/interrupts)。

| 场景                                 | 做法                                                                                   |
| ------------------------------------ | -------------------------------------------------------------------------------------- |
| plan_confirm / 设备缺槽 / preflight  | 父图节点内 `interrupt(payload)`                                                        |
| MCP 运行时歧义（多名匹配、导出确认） | MCP 返回 `hitl_required` → Agent 工具包装器内 `interrupt(payload)` → resume 后重调 MCP |
| 前端续跑                             | `POST /api/agent/resume` → **一律** `Command(resume=body)`                             |

**禁止**：

- `session_store.pending_plan` / `pending_tool_hitl`
- `HitlInterruptRequired` 作为编排主路径
- `HumanInTheLoopMiddleware`（与自定义表单双协议）

对称路径：approve / reject / abort / 新消息（若仍 interrupted → `Command(resume=reject)` 清图）须状态闭合。

自定义表单 payload 形状保留（`ask_params` / `confirm` / `plan_confirm`），经 `interrupt(payload)` 下发。

## 7. Plan / BPMN

- Plan 确认与逐步执行：父图节点（可 interrupt）
- BPMN：父图节点/子图；工具 HITL 同走包装器 `interrupt`
- BPMN HTTP API 仍挂 `/api/agent/bpmn/*` 与 threads state

## 8. 会话

- `thread_id` + AsyncPostgres checkpointer
- 新会话 = 新 `thread_id`；删除会话清理持久化

## 9. Client Action 桥接

```text
MCP ToolResult.client_action 或 .client_actions
  → Agent 展开为一条或多条 SSE client_action
  → 前端 ClientToolExecutor 执行
  → 无 /tool-result 回调
```

契约见 [`06-contracts.md`](./06-contracts.md) §2；类型源：`@ims/shared-types` 的 `ToolResult`。
