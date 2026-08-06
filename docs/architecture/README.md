# 架构文档索引

编码唯一依据。从 [00-overview.md](./00-overview.md) 开始阅读。

本仓为 **ims-ai-desktop**（Electron + Agent + MCP）。UI：`apps/desktop`；服务：`services/`（含 `platform-contracts` 共享 Python 包 `contracts`）。验收：[`../desktop-m1-acceptance.md`](../desktop-m1-acceptance.md)。

| 文档                                                       | 主题                             |
| ---------------------------------------------------------- | -------------------------------- |
| [00-overview.md](./00-overview.md)                         | 目标、原则、验收对应             |
| [01-system-context.md](./01-system-context.md)             | 组件、端口、目录                 |
| [02-mcp-platform-server.md](./02-mcp-platform-server.md)   | Platform MCP 执行面              |
| [03-agent-runtime.md](./03-agent-runtime.md)               | LangGraph / SSE / HITL           |
| [04-agent-mcp-gateway.md](./04-agent-mcp-gateway.md)       | Agent `/mcp`                     |
| [05-qdrant-rag.md](./05-qdrant-rag.md)                     | Qdrant 知识库                    |
| [06-contracts.md](./06-contracts.md)                       | TS packages + Python `contracts` |
| [07-conversation-flow.md](./07-conversation-flow.md)       | 用户需求→回复 / 多轮 / HITL 时序 |
| [08-dev-guide.md](./08-dev-guide.md)                       | 本地开发 / 质量门禁 / IDE        |
| [09-platform-db-readonly.md](./09-platform-db-readonly.md) | 达梦只读 / 实体同步              |
| [10-voice-asr.md](./10-voice-asr.md)                       | 语音转写 / 按段纠错 / 标注       |
| [11-voiceprint.md](./11-voiceprint.md)                     | 生产级声纹识别（1:1 / 1:N）      |

迭代设想（非编码基准）：[`../roadmap/README.md`](../roadmap/README.md)
