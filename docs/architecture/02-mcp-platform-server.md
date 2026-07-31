# 02 — Platform MCP Server

## 1. 职责

`platform-mcp-server` 是平台业务能力的 **唯一执行面**：

- **执行面**：`platform_mcp.runtime.tools`（告警/设备/导出/导航等 `@tool` handler）
- **共享逻辑**：`services/platform-contracts`（包名 `contracts`）—— HITL 载荷、preflight、catalog 读取、平台 HTTP 客户端、告警/设备纯函数等
- 以 MCP Tools 对外暴露；调用平台 HTTP API（JWT 透传）
- **不**跑 LLM、**不**调用 LangGraph `interrupt()`、**不管** SSE / checkpointer
- Agent **禁止** `import platform_mcp`；共享代码只依赖 `contracts`；图内绑工具只经 MCP Client（+ 本机 `retrieve_knowledge`）

**禁止**本进程依赖 `langgraph`。运行时歧义通过 JSON `hitl_required` 上抛，由 **Agent 进程** 转为 `interrupt()`。

## 2. 传输与入口

- Transport：**Streamable HTTP**
- URL：`http://127.0.0.1:8010/mcp`
- 依赖：官方 `mcp` Python SDK（可用 FastMCP 注册工具）

## 3. 工具清单

与 `packages/agent-core/tool-catalog.ts` 对齐（导出 JSON 供运行时校验）：

### Server Tools（后端执行）

| 名称                     | 说明                      |
| ------------------------ | ------------------------- |
| `query_alarms`           | 查询告警列表              |
| `get_alarm_detail`       | 告警详情                  |
| `download_file`          | 导出 Excel（多 resource） |
| `batch_confirm_alarms`   | 批量确认                  |
| `batch_process_alarms`   | 批量处理                  |
| `query_devices`          | 查询设备                  |
| `get_device_detail`      | 设备详情                  |
| `query_device_variables` | 设备变量                  |
| `send_device_cmd`        | 下发设备指令              |

### Client Tools（返回动作，浏览器执行）

| 名称                 | 说明            |
| -------------------- | --------------- |
| `navigate_to`        | 路由跳转        |
| `pause`              | 暂停等待用户    |
| `open_alarm_detail`  | 打开告警详情 UI |
| `open_device_detail` | 打开设备详情 UI |

### RAG

| 名称                 | 说明                              |
| -------------------- | --------------------------------- |
| `retrieve_knowledge` | 默认在 **Agent 侧** 注册（见 05） |

## 4. 返回约定

统一 JSON 字符串（或 MCP text content 内嵌 JSON）：

```json
{
  "ok": true,
  "summary": "给人看的一句话摘要",
  "data": {},
  "client_action": null,
  "client_actions": null,
  "user_cancelled": false
}
```

权威形状：`@ims/shared-types` 的 `ToolResult`（见 [`06-contracts.md`](./06-contracts.md)）。`client_action` 与 `client_actions` 二选一；多文件导出等场景用 `client_actions`。

需人工补参/确认时（运行时歧义）：

```json
{
  "hitl_required": true,
  "payload": {
    "type": "ask_params",
    "tool": "get_device_detail",
    "message": "...",
    "fields": []
  }
}
```

Agent Client 检测到 `hitl_required` 后在**图内**调用 `interrupt(payload)`，resume 后带合并参数重调本 Server。

## 5. 元数据与 HITL 边界

- `risk_level`、`hitl_fields`、参数 schema 以 **catalog** 为唯一源
- MCP tool `description` 由 catalog 生成
- **图级**缺参 / plan_confirm：在 Agent 父图节点 `interrupt`，不在本 Server
- **工具内** `ask_user_*`：只发出 `hitl_required`（或抛 `McpHitlSignal` 由 server 层序列化），**永不**调用 `langgraph.types.interrupt`

## 6. 鉴权

每个 tool 调用从 MCP HTTP 请求头读取：

- `Authorization: Bearer <jwt>` → `current_auth_token`
- 可选 `X-Thread-Id` → `current_thread_id`
- 可选 `X-Hitl-Confirm-Bypass: 1` → 跳过工具内 `ask_user_confirm`（Agent 图内已确认后的重调）

写操作未带 Token 一律返回 `ok: false`。

## 7. 健康检查

- `GET http://127.0.0.1:8010/health` → `{ status, service, mcp, port, catalog, resources, prompts }`

## 8. Resources / Prompts

| URI / 名称              | 说明             |
| ----------------------- | ---------------- |
| `catalog://tools`       | 工具契约 JSON    |
| `catalog://write-tools` | 写操作工具名单   |
| Prompt `platform_ops`   | 运维场景使用指引 |

## 9. Catalog 同步

```bash
cd platform-agent-service
uv run python scripts/export_catalog.py
```

启动时校验 catalog 工具名 ↔ 已注册 MCP tools。
