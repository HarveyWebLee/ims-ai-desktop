# 06 — 契约（packages）

## 1. 唯一数据源

| 包                  | 内容                                                                         |
| ------------------- | ---------------------------------------------------------------------------- |
| `@ims/agent-core`   | `tool-catalog.ts`、`model-catalog.ts`、路由/设备动作 catalog                 |
| `@ims/shared-types` | `PlatformToolDefinition`、SSE 事件类型、HITL、Plan、ClientAction、ToolResult |

禁止在 Python / 前端硬编码工具列表或与 catalog 冲突的 schema。

## 2. ToolResult

权威类型：`packages/shared-types` 的 `ToolResult`（与 `platform_mcp.runtime.result.tool_result` 对齐）。

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

工具 **实现** 在 `platform_mcp.runtime`；catalog 只描述「是什么、参数、风险」。

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
