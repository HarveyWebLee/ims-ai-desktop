# 代码学习阅读指南

> **目标**：用最短路径理解 `platform-agent-service` 的生产主链，并能独立定位 chat / resume / HITL / Plan / MCP 相关改动点。  
> **原则**：先读架构文档，再按「请求从哪进、图怎么走、事件怎么出」对着源码走；不要从工具目录或零散 service 随机翻。

---

## 0. 读前准备

### 0.1 必读架构（先于源码）

| 顺序 | 文档                                                                                   | 读什么                           |
| ---- | -------------------------------------------------------------------------------------- | -------------------------------- |
| 1    | [`docs/architecture/00-overview.md`](../../docs/architecture/00-overview.md)           | 双层 MCP、零兼容、技术选型       |
| 2    | [`docs/architecture/03-agent-runtime.md`](../../docs/architecture/03-agent-runtime.md) | 父图拓扑、HITL、SSE、Plan        |
| 3    | [`docs/architecture/06-contracts.md`](../../docs/architecture/06-contracts.md)         | SSE / ToolResult / packages 契约 |

可选：[`02-mcp-platform-server.md`](../../docs/architecture/02-mcp-platform-server.md)、[`05-qdrant-rag.md`](../../docs/architecture/05-qdrant-rag.md)、[`08-dev-guide.md`](../../docs/architecture/08-dev-guide.md)。

### 0.2 脑中固定模型

```text
前端 AiAssistant
  → POST /api/agent/chat | /resume   （SSE）
  → app/api/*                        （HTTP / 鉴权 / 格式化 SSE）
  → app/application/conversation/*   （用例：组装上下文、清 stale、构造 input）
  → app/graph/parent_graph_stream.py （astream_events v3）
  → app/graph/parent_graph.py        （唯一运行时父 StateGraph）
       ├─ chat_direct / react        → create_agent（agent_factory）
       ├─ plan_confirm / device_gate → interrupt() → Command(resume)
       └─ plan_execute / bpmn_execute→ application/execution/*
  → 工具仅经 MCP Client（app/mcp/client.py）+ 本地 retrieve_knowledge
  → SSE 事件经 agent_stream_adapter / stream_envelope 回前端
```

**牢记三条红线**（代码里已删，读旧笔记时勿找）：

- 无图外 `pending_plan` / `pending_tool_hitl`
- 无手写 ReAct 与 `create_agent` 双轨
- 业务工具不在 Agent 进程内用 `@tool` 直绑平台 API

### 0.3 本地能跑再读更有效

```bash
# monorepo 根或本服务目录，按 docs/architecture/08-dev-guide.md
uv sync --extra dev
cp .env.example .env   # 配 DEEPSEEK_API_KEY 或 DASHSCOPE_API_KEY、PLATFORM_MCP_URL
uv run agent           # 默认 :8008（以 .env PORT 为准）
curl -s localhost:8008/health
```

排查时开 `AGENT_DEBUG_TRACE=true`，过滤 `[AgentTrace]`（见服务根 [`README.md`](../README.md) 表格）。

---

## 1. 目录地图（按层读，不要按字母序）

| 层       | 路径                                              | 职责                                          | 建议精力 |
| -------- | ------------------------------------------------- | --------------------------------------------- | -------- |
| 入口     | `app/main.py`                                     | FastAPI 路由、lifespan、/health、挂载 Gateway | ★☆☆      |
| API      | `app/api/`                                        | chat/resume/sessions/bpmn 等 HTTP 面          | ★★☆      |
| 用例     | `app/application/conversation/`                   | `stream_chat` / `stream_resume`               | ★★★      |
| 执行     | `app/application/execution/`                      | Plan / BPMN / ReAct 步进执行                  | ★★☆      |
| 图       | `app/graph/`                                      | 父图、流适配、HITL、checkpoint                | ★★★      |
| MCP      | `app/mcp/`                                        | Client、工具包装、Gateway B 面                | ★★★      |
| 领域服务 | `app/services/`                                   | Plan 门控、意图、Prompt、会话元数据           | ★★☆      |
| 持久化   | `app/persistence/`、`infrastructure/persistence/` | checkpointer、会话                            | ★★☆      |
| RAG      | `app/rag/`、`infrastructure/vector/`              | 检索与向量                                    | ★☆☆      |
| 提示词   | `app/prompts/`                                    | 系统 / 意图 / Plan 等 md                      | ★★☆      |
| 配置     | `app/config.py`                                   | 环境变量与开关                                | ★★☆      |
| 测试     | `tests/`                                          | 行为锚点，改功能时对照                        | ★★☆      |

**较少优先读**（除非任务点名）：`app/tools/` 历史目录、`app/cli/`、`app/quality.py`、大体积 `app/data/*.json`。

---

## 2. 分阶段阅读路径

### 阶段 A — 一条「你好」走完（约 1～2 小时）

目标：看清 **新消息 → 纯对话 → SSE 文本**，对应验收 AC-20。

| 步  | 文件                                              | 关注点                                                                               |
| --- | ------------------------------------------------- | ------------------------------------------------------------------------------------ |
| 1   | `app/main.py`                                     | `@app.post("/api/agent/chat")` 如何转到 `api.chat`                                   |
| 2   | `app/api/chat.py`                                 | `ChatRequest`、校验、`StreamingResponse`、`_format_sse`                              |
| 3   | `app/application/conversation/chat.py`            | `stream_chat` → `stream_chat_core`：清编排、abandon stale interrupt、`initial_state` |
| 4   | `app/graph/context.py`                            | `assemble_context`：用户消息如何变成 `llm_user_message`                              |
| 5   | `app/graph/router.py` + `services/chat_intent.py` | 何时判为 `CHAT`（chat_direct）                                                       |
| 6   | `app/graph/parent_graph.py`                       | `classify_node` → `chat_direct`；`build_parent_graph`                                |
| 7   | `app/graph/agent_factory.py`                      | `create_agent(tools=[])` 纯对话 Agent                                                |
| 8   | `app/graph/parent_graph_stream.py`                | `astream_events(version="v3")`                                                       |
| 9   | `app/graph/agent_stream_adapter.py`               | LangGraph 事件 → `(event_name, payload)`                                             |
| 10  | `app/graph/stream_envelope.py`                    | Plan/Trace 包装（本路径可略读）                                                      |

自检问题：

- 同 `thread_id` 再发一条新消息时，为何要 `abandon_stale_checkpoint_interrupt`？
- SSE 的 `message` 与 HTTP JSON `{code,data,message}` 分别用在哪？

### 阶段 B — HITL 对称路径（约 2～3 小时）

目标：理解 **interrupt → 前端表单 → resume → Command**，对应 AC-06/07/21/22。

| 步  | 文件                                                          | 关注点                                                  |
| --- | ------------------------------------------------------------- | ------------------------------------------------------- |
| 1   | `app/graph/hitl_interrupt.py`                                 | 唯一封装：`interrupt(payload)`                          |
| 2   | `parent_graph.py` 的 `plan_confirm_node` / `device_gate_node` | resume 后如何分支 approve / reject                      |
| 3   | `app/mcp/client.py`                                           | 工具包装器：MCP 返回 `hitl_required` → 图内 `interrupt` |
| 4   | `app/api/resume.py`                                           | 请求体如何进用例层                                      |
| 5   | `app/application/conversation/resume.py`                      | **一律** `Command(resume=...)`；拒绝与 bypass           |
| 6   | `app/graph/checkpoint_utils.py`                               | pending interrupt 探测、dangling tool_calls 修复        |

自检问题：

- 用户「取消」后，下一轮 chat 为何不应再弹出旧 interrupt？
- 为何禁止在 `session_store` 再造一套 `pending_*`？

对称路径清单（改 HITL 时必须 mentally walkthrough）：

```text
approve  → stream_resume(Command)
reject   → stream_resume(Command 带 reject)
abort    → 前端中止流；后端状态闭合
新消息   → stream_chat（清编排 + abandon stale）
同 thread 下一轮 → checkpoint 消息追加，无残留 HITL UI
```

### 阶段 C — Plan / BPMN 执行（约 2～4 小时）

目标：多步确认与执行节点，对应 AC-08～11、BPMN AC-24+。

| 步  | 文件                                                               | 关注点                        |
| --- | ------------------------------------------------------------------ | ----------------------------- |
| 1   | `services/plan_confirm.py`、`plan_route.py`、`llm_task_planner.py` | 何时进 `plan_confirm`         |
| 2   | `parent_graph.py` → `plan_execute_node` / `bpmn_execute_node`      | 节点如何调执行层              |
| 3   | `application/execution/plan_runner.py`、`bpmn_plan_runner.py`      | 步进、工具调用、custom stream |
| 4   | `application/execution/node_handlers/`                             | BPMN 节点类型处理             |
| 5   | `api/bpmn.py` + `services/bpmn_orchestration.py`                   | HTTP 画布 ↔ Plan / 快照       |

自检：Plan 批准后走 `plan_execute` 还是 `bpmn_execute` 由哪些 state 字段决定？

### 阶段 D — MCP、RAG、Gateway（按需）

| 主题           | 文件                                                  | 说明                                             |
| -------------- | ----------------------------------------------------- | ------------------------------------------------ |
| 工具发现与缓存 | `mcp/client.py`、`mcp/connections.py`                 | `MultiServerMCPClient`；不可达不回退本机业务工具 |
| 本地 RAG 工具  | `mcp/local_tools.py`、`rag/`                          | `retrieve_knowledge`                             |
| Agent B 面     | `mcp/gateway.py`、`main.py` lifespan                  | `/mcp` 供 Cursor 等调用                          |
| Catalog        | `scripts/export_catalog.py`、`../packages/agent-core` | 工具说明书唯一源；改完须 export                  |

---

## 3. 生产主链速查（改 bug 时用）

### 3.1 新消息 chat

```text
api/chat.py
  → conversation/chat.py::stream_chat[_core]
  → clear_thread_orchestration + abandon_stale_interrupt + repair_dangling_tool_calls
  → stream_parent_graph(input=ParentState)
  → parent_graph.classify → chat_direct | device_gate | plan_confirm | react
  → SSE …
```

### 3.2 HITL resume

```text
api/resume.py
  → conversation/resume.py::stream_resume[_core]
  → Command(resume=normalized_body)
  → stream_parent_graph(input=Command)
  → 从 interrupt 点继续（节点重跑，interrupt 之前须幂等）
```

### 3.3 关键符号（建议全文搜索）

| 符号                                   | 含义                |
| -------------------------------------- | ------------------- |
| `stream_chat` / `stream_resume`        | 对话用例入口        |
| `stream_parent_graph`                  | 父图流式执行        |
| `build_parent_graph` / `classify_node` | 父图构建与路由      |
| `interrupt_or_raise`                   | 图内 HITL           |
| `Command(resume=`                      | 续跑唯一写法        |
| `get_mcp_tools` / `warmup_mcp_tools`   | 工具绑定            |
| `wrap_stream_with_plan_trace`          | Plan/Trace SSE 包装 |
| `assemble_context`                     | 用户输入组装        |

---

## 4. 模块职责一览（深入时对照）

### 4.1 `app/graph/`

| 文件                      | 一句话                               |
| ------------------------- | ------------------------------------ |
| `parent_graph.py`         | 父 StateGraph 拓扑与各节点           |
| `parent_graph_stream.py`  | `astream_events` + CustomTransformer |
| `agent_factory.py`        | 按 model_id 缓存 create_agent / 父图 |
| `agent_stream_adapter.py` | 官方流事件 → 内部 SSE 元组           |
| `stream_envelope.py`      | Plan/Trace/client_action 等 envelope |
| `hitl_interrupt.py`       | `interrupt()` 薄封装                 |
| `checkpoint_utils.py`     | interrupt / 消息修复 / 摘要          |
| `context.py`              | `AgentContext` 组装                  |
| `router.py`               | TaskRoute 分类                       |

### 4.2 `app/application/`

| 路径                     | 一句话             |
| ------------------------ | ------------------ |
| `conversation/chat.py`   | 新消息用例         |
| `conversation/resume.py` | HITL 续跑用例      |
| `execution/*`            | Plan/BPMN/工具步进 |
| `tool_execution.py`      | 工具执行编排辅助   |

### 4.3 `app/services/`（高频）

| 文件                                         | 何时读                                             |
| -------------------------------------------- | -------------------------------------------------- |
| `session_store.py`                           | 线程元数据（如 BPMN 快照）；**不是** HITL 主状态机 |
| `plan_confirm.py` / `plan_route.py`          | Plan 门控                                          |
| `device_control_gate.py`                     | 设备控制缺参门控                                   |
| `prompt_assembly.py`                         | 系统提示与近期消息                                 |
| `chat_intent.py`                             | 纯对话意图                                         |
| `llm_task_planner.py` / `llm_plan_params.py` | LLM 生成 Plan / 抽参                               |
| `trace_collector.py` / `trace_graph.py`      | Trace 拓扑                                         |

---

## 5. 用测试当说明书

改行为前，先在 `tests/` 用关键词搜对称场景，例如：

```bash
cd platform-agent-service
rg -n "stream_resume|plan_confirm|interrupt|chat_direct" tests/
uv run check test -k hitl -q
```

测试命名通常直接对应验收意图；优先读断言与 fixture，再回头改生产代码。

---

## 6. 常见「找错地方」对照

| 想改的行为          | 正确落点                                                               | 勿先改                         |
| ------------------- | ---------------------------------------------------------------------- | ------------------------------ |
| SSE 事件名/字段     | `agent_stream_adapter` + `packages/shared-types` + 前端 parser         | 只改 `api/chat.py` 字符串      |
| HITL 表单字段       | interrupt payload 构造处（父图节点 / MCP wrapper）+ 契约               | 新建 session_store pending     |
| 工具能否被模型看到  | `packages/agent-core` → `export_catalog` → Platform MCP → `mcp/client` | 在 Agent 里新写 `@tool` 调平台 |
| 纯对话误调工具      | `router` / `chat_intent` / classify                                    | 在 react 节点里特判吞工具      |
| 取消后仍显示旧 Plan | chat 清编排 + abandon interrupt + 前端 pendingInterrupt                | 只改 resume 成功分支           |
| 续跑丢上下文        | checkpointer + `thread_id` + `Command(resume)`                         | 自行拼 messages 重跑子图       |

---

## 7. 建议的一周自学节奏

| 天  | 内容                                  | 产出                    |
| --- | ------------------------------------- | ----------------------- |
| D1  | 阶段 A + 跑通 /health 与一句「你好」  | 能画 chat 序列图        |
| D2  | 阶段 B + 开 AgentTrace 打一次缺参导出 | 能解释 interrupt/resume |
| D3  | 阶段 C 选 Plan 或 BPMN 一条线         | 能指出 execute 节点入口 |
| D4  | MCP client 包装 + catalog export      | 能说清工具从哪来        |
| D5  | 读一条相关测试并按 AC 手工点一轮      | 能改前写出影响面清单    |

改功能时强制对照：[`ai-dev-quality-gates.mdc`](../../.cursor/rules/ai-dev-quality-gates.mdc) 的「改前影响面 / 改后门禁」。

---

## 8. 文档与源码冲突时

1. **架构意图**：以 `docs/architecture/*` 为准
2. **运行时行为**：以当前 `app/graph/parent_graph.py` + 测试为准
3. **契约字段**：以 `packages/` + `06-contracts.md` 为准

发现文档过时：优先提 MR 改文档或在本指南相关段落注明日期与真实路径，避免「第二套真相」。
