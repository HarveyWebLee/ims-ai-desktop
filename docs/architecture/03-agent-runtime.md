# 03 — Agent Runtime

> **端到端时序（用户需求 → 回复 / 多轮 / HITL）**：见 [`07-conversation-flow.md`](./07-conversation-flow.md)。

## 1. 职责

`platform-agent-service` 负责：

- FastAPI：`/api/agent/chat`、`/resume`、会话、模型、BPMN、健康检查
- **父 StateGraph**：classify / plan_confirm / device / plan / BPMN / react（唯一运行时入口）
- **ReAct / 纯对话**：官方 `create_agent`（作为父图节点，非第二套编排引擎）
- **MCP Client**：`MultiServerMCPClient.get_tools()` + 本地 `retrieve_knowledge`
- Qdrant RAG 注入（见 05）
- **运行时 Playbook**（`app/playbooks/*.md`）：按意图注入 `llm_user_message`，对齐 Cursor Skills 的按需规程；见下文 §3.2
- Agent MCP Gateway（见 04）

HTTP 层只做鉴权、构造初始 state / `Command(resume=...)`、把 `astream_events(v3)` 映射为 SSE。**禁止**图外 `pending_plan` / `pending_tool_hitl` 第二状态机。

## 2. 父图拓扑

```text
START → classify
  ├─ chat_direct   → create_agent(tools=[]) → END
  ├─ device_gate   → interrupt(ask_params) → 节点内调 MCP → END
  ├─ plan_confirm  → interrupt(plan_confirm) → plan_execute | bpmn_execute → END
  └─ react         → create_agent(tools=MCP+retrieve_knowledge) → END
```

> `device_gate` 批准后**不**再进入 `react`：在本节点执行设备工具并结束（见 `device_gate_node`）。

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
  → Auth / HITL / run_mode wrapper（图内 interrupt；readonly 拒写）
  → (+ retrieve_knowledge)
  → 按 run_mode + 意图 domains 裁剪子集
  → 绑定到 create_agent（按 model_id + 工具指纹缓存）/ 父图 plan·bpmn 节点调用同一套包装工具
```

**会话运行模式**（请求字段 `run_mode`，默认 `confirm`；ContextVar `current_run_mode`；MCP 经 `X-Run-Mode`）：

| 模式         | 绑定                                                                                                  | 调用时                                    |
| ------------ | ----------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| `readonly`   | 仅非写工具（无 `required_permissions` 且 risk≠medium/high）                                           | 写工具若被调用 → ToolResult 拒绝          |
| `confirm`    | 关键词推断 catalog `domains`；命中则 core∪matched；**未命中绑 safe_default（core∪非写），不回退全量** | 写操作必经 `ask_user_confirm` → interrupt |
| `autonomous` | 同 confirm 子集策略                                                                                   | 跳过 confirm HITL；缺参仍 `ask_params`    |

**显式 Plan**（请求字段 `plan_first`，桌面开关「先计划」；ContextVar `current_plan_first`）：

- 默认 AI-first 下 classify 恒 `react`；`plan_first=true` 时覆盖旁路，走既有 `prepare_plan_confirm_gate_async`
- 多步命中后 `interrupt(plan_confirm)`，用户确认（Build）后才 `plan_execute` / 写工具
- `plan_first` 下只读多步也需确认（覆盖 `write_only` 跳过）

**工具子集**：catalog 条目含 `domains`（alarm/device/export/nav/…）；`retrieve_knowledge` 与 nav 低风险工具恒保留。写工具仅在领域命中时进入绑定集。chat 将 tool_names 写入内存 + `agent_thread_tool_subset`（Postgres），resume 复用同一父图；删会话时清理。

### 3.2 运行时 Playbook（P1-1）

| 项              | 说明                                                                                    |
| --------------- | --------------------------------------------------------------------------------------- |
| 目录            | 默认 `app/playbooks/*.md`；可用 `AGENT_PLAYBOOK_DIR` 指向外部目录                       |
| 匹配            | frontmatter `triggers` / `domains` 关键词；`AGENT_PLAYBOOK_MAX_MATCHES` 限制单轮份数    |
| 注入点          | `assemble_context` → 拼入 `llm_user_message`（与被动 RAG 并列）；**不**改 system prompt |
| 为何不进 system | `create_agent` 按 system 指纹缓存；按轮注入避免缓存失效，且符合「长 Skills 按需加载」   |
| 开关            | `AGENT_PLAYBOOK_ENABLED`（默认 true）                                                   |
| resume          | 新消息 chat 注入；resume 沿用 checkpoint 内已含 playbook 的 HumanMessage，无需重匹配    |

内置样例：`alarm-dispose`（告警处置）、`batch-export`（批量导出）、`device-status`（设备状态）。`AGENT_PLAYBOOK_WATCH=true`（默认）时监听目录 `.md` 变更并自动 `reload_playbooks()`；也可重启进程。外部目录可运营热更。

### 3.3 知识检索 Subagent（P1-3）

对齐官方 [Subagents](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents)：子任务包成工具、**仅摘要**回主 agent；**不**采用 handoff 多节点（避免改父图拓扑与 checkpointer 串话）。

| 项       | 说明                                                                                      |
| -------- | ----------------------------------------------------------------------------------------- |
| 入口     | 本地工具 `retrieve_knowledge` → `app/services/subagent/knowledge_research.py`             |
| 隔离     | 无 checkpointer；不写入主 thread 长 hits                                                  |
| 返回     | `summary` + `sources`（标题/路径）+ `hit_count`；**不含**全文 `hits`                      |
| 摘要     | 默认短模型（`AGENT_SUBAGENT_KNOWLEDGE_*`）；失败回退抽取式截断                            |
| 被动 RAG | `format_rag_section` 按 `AGENT_RAG_PASSIVE_SNIPPET_CHARS` 截断注入 HumanMessage           |
| 对称路径 | chat / resume 共用同一本地工具；Gateway `call_platform_tool(retrieve_knowledge)` 同步受益 |

### 3.4 运行时工具 Hooks（P2-1）

对齐 Cursor Lifecycle Hooks：**不**替代 `interrupt` / HITL。挂在授权通过之后、真实 MCP 调用之前/之后。

| 项       | 说明                                                                                     |
| -------- | ---------------------------------------------------------------------------------------- |
| 协议     | `app/domain/tool_hooks.py` → `ToolLifecycleHook.before_tool` / `after_tool`              |
| 默认实现 | `DenyListToolHook`（`AGENT_TOOL_HOOK_DENY_TOOLS`）+ 可选 `AuditToolHook`                 |
| 挂载     | Plan：`ToolExecutionPipeline`；ReAct：`_wrap_mcp_tool(authorize=True)`（避免 Plan 双跑） |
| 拒绝     | 返回统一 ToolResult（`error_code=tool_hook_deny_*`），并写 audit `tool_hook_deny`        |
| 开关     | `AGENT_TOOL_HOOKS_ENABLED`（默认 true）；`AGENT_TOOL_HOOKS_AUDIT_AFTER`（默认 false）    |

**禁止**：直绑业务 `@tool` 实现；Platform MCP 不可达时不回退本机工具。
**禁止**：Agent 生产代码 / 测试 `import platform_mcp`（含 `from platform_mcp...`）；共享 HITL / preflight / catalog / 平台客户端走 `contracts`。

## 3.1 与 contracts 边界

| 包                           | Agent 可否依赖      | 内容                                                                     |
| ---------------------------- | ------------------- | ------------------------------------------------------------------------ |
| `contracts`                  | 是（path editable） | context / hitl / preflight / catalog / platform_client / 告警·设备纯函数 |
| `platform_mcp`（MCP Server） | **否**              | 仅 MCP 进程内 `@tool` 执行面                                             |

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

## 9. Client Action 桥接（P2-2）

```text
MCP ToolResult.client_action 或 .client_actions
  → Agent 展开为一条或多条 SSE client_action
  → 前端 ClientToolExecutor
       ├─ 有 window.imsPlatformHost（或模拟宿主）→ 真实 navigate / openModal
       └─ 无宿主 → 跳过 + 可读降级提示（M1）
  → POST /api/agent/threads/{thread_id}/client-action-result
       → audit `client_action_result`（不阻塞图、不替代 interrupt）
```

| 项       | 说明                                                           |
| -------- | -------------------------------------------------------------- |
| 宿主注入 | 父页设置 `window.imsPlatformHost = { navigate, openModal }`    |
| 本地验收 | `localStorage.setItem('ims_ai_mock_platform_host','1')` 后刷新 |
| 回执契约 | `@ims/shared-types` 的 `ClientActionResult`                    |
| 对称路径 | chat / resume 共用 `useAgentStream.onClientAction`             |

契约见 [`06-contracts.md`](./06-contracts.md) §2；类型源：`@ims/shared-types` 的 `ToolResult` / `ClientActionResult`。
