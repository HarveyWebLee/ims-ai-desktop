# 06 — 契约（packages + Python contracts）

## 1. 唯一数据源

| 包 / 工程                                         | 内容                                                                                           |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `@ims/agent-core`                                 | `tool-catalog.ts`、`model-catalog.ts`、路由/设备动作 catalog                                   |
| `@ims/shared-types`                               | `PlatformToolDefinition`、SSE 事件类型、HITL、Plan、ClientAction、ToolResult                   |
| `services/platform-contracts`（包名 `contracts`） | Agent / MCP **共享** Python 运行时：HITL、preflight、catalog 读取、平台客户端、告警/设备纯函数 |

禁止在 Python / 前端硬编码工具列表或与 catalog 冲突的 schema。

### 1.1 三包边界（Python）

| 包                                      | 职责                                                   | 依赖约束                                                                                               |
| --------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| `contracts`                             | 共享契约与纯逻辑（无 LangChain / FastMCP / LangGraph） | Agent + MCP 均可依赖；**禁止** `import app` / `import platform_mcp`；**禁止**硬编码兄弟工程路径        |
| `platform-mcp-server`（`platform_mcp`） | MCP 传输 + `@tool` **执行面**（`runtime/tools`）       | 依赖 `contracts`；启动时 `bind_settings` + `bind_shared_data_dir`；不反向被 Agent import               |
| `platform-agent-service`（`app`）       | 父图 / SSE / RAG / Gateway                             | 依赖 `contracts`；启动时 `wire_contracts_runtime`；**禁止** `import platform_mcp`；工具只经 MCP Client |

宿主能力（配置单例、共享 data 目录、会话历史、编排调试探针）由 Agent/MCP 经 `contracts.runtime_bind` 注入，不得在 `contracts` 内回指宿主包或写死其他服务工程路径。

## 2. ToolResult

权威类型：`packages/shared-types` 的 `ToolResult`（与 `contracts.result.tool_result` 对齐）。

```ts
interface ToolResult {
  ok: boolean;
  summary: string;
  data?: unknown;
  client_action?: ClientAction | null;
  /** 多条前端动作（分批导出等）；与 client_action 二选一，序列化优先本字段 */
  client_actions?: ClientAction[];
  user_cancelled?: boolean;
}
```

MCP Server 与 Agent 解析统一此结构。

| 字段             | 说明                                                                                              |
| ---------------- | ------------------------------------------------------------------------------------------------- |
| `client_action`  | 单条 Client Tool 动作                                                                             |
| `client_actions` | 多条动作；Agent chat/resume 流与历史回放会**展开为多条** SSE `client_action`（无独立 SSE 事件名） |
| `user_cancelled` | 用户拒绝/取消；编排勿自动重试                                                                     |

改字段须同步：`shared-types` → MCP `tool_result` → Agent `_client_actions_from_*` → 桌面 `parseToolResult` / `ClientToolExecutor`。

## 3. SSE

前端 `AgentController` / `sseParser` 只认本契约事件名与 payload。改事件须同步：

1. `packages/shared-types`
2. Agent stream adapter / envelope
3. 前端 parser / Store

`interrupt` 事件 **仅** 由图 `astream_events` 的 `stream.interrupts`（或等价 checkpoint interrupt）映射产生。

## 4. Catalog → MCP

`export_catalog.py` 输出：

- Agent：`app/tools/catalog.json`（preflight / prompt）
- Platform MCP：`platform_mcp/data/catalog.json`（+ navigation / device_action）

工具 **实现** 在 `platform_mcp.runtime.tools`；共享逻辑在 `contracts`；catalog 只描述「是什么、参数、风险」。

## 4.1 HITL（单一路径）

| 层                   | 职责                                                            |
| -------------------- | --------------------------------------------------------------- |
| Agent 父图节点       | `plan_confirm` / 设备缺槽 / preflight → `interrupt(payload)`    |
| Agent MCP 工具包装器 | 收到 MCP `hitl_required` → `interrupt(payload)` → resume 后重调 |
| Platform MCP         | 只返回 `{ hitl_required, payload }`；**不**调用 `interrupt()`   |
| 前端 `/resume`       | body 原样作为 `Command(resume=...)`；无图外 pending 分支        |

**禁止** `pending_plan` / `pending_tool_hitl` 作为 HITL 暂存。

自定义表单 payload（`type` / `tool` / `fields` / `message` 等）可保留产品形状。

## 4.2 MCP HTTP 头（Agent → Platform MCP）

| Header                  | 说明                                                        |
| ----------------------- | ----------------------------------------------------------- |
| `Authorization`         | 平台 JWT                                                    |
| `X-Thread-Id`           | 会话线程                                                    |
| `X-Hitl-Confirm-Bypass` | `1`/`true`：图内已确认后重调时跳过工具内 `ask_user_confirm` |

## 5. i18n

用户可见文案：`apps/desktop/src/locales/ai_assistant/`，命名空间 `aiAssistant.*`（zh-CN / en-US 同步）。
