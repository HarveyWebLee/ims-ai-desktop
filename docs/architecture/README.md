# 架构文档索引

编码唯一依据。从 [00-overview.md](./00-overview.md) 开始阅读。

本仓为 **ims-ai-desktop**（Electron + Agent + MCP）。UI：`apps/desktop`；服务：`services/`。验收：[`../desktop-m1-acceptance.md`](../desktop-m1-acceptance.md)。

| 文档                                                       | 主题                      |
| ---------------------------------------------------------- | ------------------------- |
| [00-overview.md](./00-overview.md)                         | 目标、原则、验收对应      |
| [01-system-context.md](./01-system-context.md)             | 组件、端口、目录          |
| [02-mcp-platform-server.md](./02-mcp-platform-server.md)   | Platform MCP              |
| [03-agent-runtime.md](./03-agent-runtime.md)               | LangGraph / SSE / HITL    |
| [04-agent-mcp-gateway.md](./04-agent-mcp-gateway.md)       | Agent `/mcp`              |
| [05-qdrant-rag.md](./05-qdrant-rag.md)                     | Qdrant 知识库             |
| [06-contracts.md](./06-contracts.md)                       | packages 契约             |
| [08-dev-guide.md](./08-dev-guide.md)                       | 本地开发 / 质量门禁 / IDE |
| [09-platform-db-readonly.md](./09-platform-db-readonly.md) | 达梦只读 / 实体同步       |

迭代设想（非编码基准）：[`../roadmap/README.md`](../roadmap/README.md)
