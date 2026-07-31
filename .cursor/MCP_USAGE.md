# ims-ai-desktop MCP 使用约定

## 目标

用 MCP 支撑「需求理解 → 架构设计 → 实现落地」，减少凭记忆开发导致的返工。

配置文件：[`.cursor/mcp.json`](./mcp.json)

## 推荐优先级

1. **`docs-langchain`**
   - 用途：LangChain / LangGraph API 签名、能力边界、迁移说明
   - 场景：`create_agent`、`astream_events`、checkpoint、interrupt / resume、StateGraph、MCP adapters
2. **`context7`**
   - 用途：第三方库文档（FastAPI、Electron、antd、psycopg、pytest、ruff 等）
3. **`filesystem`**
   - 用途：按仓库根路径快速读取结构、配置与文档（已绑定本仓根目录）
4. **`github`**
   - 用途：PR / issue / 变更上下文（需本机配置 `GITHUB_PERSONAL_ACCESS_TOKEN`）

## 强制规则

- 涉及 LangGraph / LangChain API 时：**先查 `docs-langchain` 再编码**
- 无法确认 API 参数时，不得凭经验直接实现
- 需求不完整时：先读 `docs/architecture/` + MCP 文档收敛假设，再落代码
- 平台业务库相关：遵守达梦只读（见 `docs/architecture/09-platform-db-readonly.md`）

## 与本仓路径对照

| 主题 | 优先阅读 |
| ---- | -------- |
| 总览 / 端口 | `docs/architecture/00-overview.md`、`01-system-context.md` |
| MCP 工具 | `docs/architecture/02-mcp-platform-server.md` |
| 父图 / HITL / SSE | `docs/architecture/03-agent-runtime.md` |
| 契约 | `docs/architecture/06-contracts.md` |
| 联调 | `docs/architecture/08-dev-guide.md`、`README.md` |
| 桌面验收 | `docs/desktop-m1-acceptance.md` |

## 开发流程建议

1. 需求分析：输入 / 输出 / 状态 / 失败分支
2. MCP 查证：官方文档确认接口与限制
3. 方案设计：复用父图 / Platform MCP / 桌面 SSE 主链
4. 编码：对称路径与契约同步
5. 回归：根目录 `pnpm check`（或 Agent `uv run check all`）+ 桌面 M1 手测
