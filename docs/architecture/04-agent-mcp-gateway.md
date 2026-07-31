# 04 — Agent MCP Gateway（B 面）

## 1. 目标

让 Cursor / 其他 MCP Client 通过 **Agent 进程** 使用平台能力与高层对话能力，而不直接暴露全部写操作（可配置）。

| 面         | 路径                        | 协议                                           |
| ---------- | --------------------------- | ---------------------------------------------- |
| **真 MCP** | `http://127.0.0.1:8008/mcp` | FastMCP **Streamable HTTP**（Cursor 配置此项） |
| REST 兼容  | `/api/agent/gateway/*`      | JSON（脚本 / 联调）                            |

### REST 路由

| 方法 | 路径                            | 说明                                             |
| ---- | ------------------------------- | ------------------------------------------------ |
| GET  | `/api/agent/gateway/health`     | Gateway 健康 + Platform MCP 探测                 |
| POST | `/api/agent/gateway/tools/list` | 列出上游 MCP 工具                                |
| POST | `/api/agent/gateway/tools/call` | 调用 Gateway 工具（body: `{ name, arguments }`） |

挂载在 `/mcp` 的 FastMCP 另提供 `GET /mcp/health`（custom_route）。

## 2. 暴露工具子集（默认）

| 工具                  | 说明                                                            |
| --------------------- | --------------------------------------------------------------- |
| `agent_chat`          | 发起一轮对话并聚合文本；参数：`message`、`thread_id?`、`model?` |
| `agent_resume`        | HITL 续跑；参数：`thread_id`、`payload`、`model?`               |
| `list_platform_tools` | 列出 Platform MCP（及额外 MCP）工具名与描述                     |
| `call_platform_tool`  | 代理调用只读白名单内工具                                        |

写操作（`send_device_cmd`、`batch_*`、`download_file`）默认 **不** 经 Gateway 直接暴露；须走 `agent_chat` 由 Agent 图 + HITL 约束。

MCP Resource：`gateway://capabilities`（白名单与工具说明）。

## 3. 鉴权与审计

- Header `Authorization: Bearer <jwt>` 或 `X-Agent-Mcp-Key: <key>`（与 `AGENT_MCP_GATEWAY_KEY` 匹配）
- **Fail-closed**：未携带有效 Bearer / 密钥时一律拒绝；`AGENT_MCP_GATEWAY_KEY` 为空时**不再**匿名放行，仅接受 Bearer JWT
- `/api/agent/gateway/health` 与 `/mcp/health` 暴露 `auth_required`、`gateway_key_configured`（健康检查本身不鉴权）
- Gateway `agent_chat` / `agent_resume` 走同一套 SSE 编排（审计由 stream 写入）
- `list_platform_tools` / `call_platform_tool` 额外写 `mcp_gateway_*` 审计事件

写工具 Agent 侧授权：catalog `required_permissions` 在 JWT 未声明 `permissions`/`scopes`/`authorities`/`perms` 时默认拒绝（`AGENT_TOOL_PERMISSION_FAIL_CLOSED=true`）。平台 JWT 尚无权限声明时，本地可临时关开关，生产须保持开启并对齐 JWT claims。

## 4. Cursor 配置示例

```json
{
  "mcpServers": {
    "ims-agent": {
      "url": "http://127.0.0.1:8008/mcp",
      "headers": {
        "Authorization": "Bearer <token>"
      }
    }
  }
}
```

## 5. 与双层关系

```text
Cursor → Agent MCP Gateway (/mcp Streamable HTTP)
            ├─ agent_chat → LangGraph → Platform MCP
            └─ call_platform_tool → Platform MCP（白名单）
```

Gateway **不**绕过 Platform MCP：`list_platform_tools` / `call_platform_tool` 均经 `MultiServerMCPClient`（`retrieve_knowledge` 仍为本机 RAG 工具）。

## 6. 相关环境变量

| 变量                                | 说明                                                                            |
| ----------------------------------- | ------------------------------------------------------------------------------- |
| `AGENT_MCP_GATEWAY_KEY`             | Gateway 共享密钥；可与 Bearer 二选一。空=不接受密钥头，仍须 Bearer              |
| `AGENT_TOOL_PERMISSION_FAIL_CLOSED` | `true`（默认）：JWT 未声明 permissions 时拒绝含 `required_permissions` 的写工具 |
| `AGENT_MCP_REQUIRED`                | `true` 时 Platform MCP 不可达则拒绝启动/绑工具                                  |
| `AGENT_MCP_WARMUP_ON_START`         | 启动预热 `list_tools`                                                           |
| `AGENT_MCP_EXTRA_SERVERS_JSON`      | 追加外部 MCP，形如 `{"ext":{"transport":"streamable_http","url":"..."}}`        |
